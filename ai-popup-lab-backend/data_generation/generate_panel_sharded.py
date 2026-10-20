"""
Sharded (parallel-container) version of the weekly panel cycle.

The single-container cycle in `generate_panel_results` is I/O-bound on
sequential LLM calls, so the slow part (biographies + turnout pass + vote
pass) is split across N containers that each handle a slice of the panel.
Three stages, each its own container run (see weekly-job.yml):

  1. PREPARE  (1 container)   prepare_panel_shards()
       - attrition + replacement, written to the active panel blob and
         guarded by the same "attrition" lock as the single-container flow
       - downloads this week's GDELT once and stores it in the gdelt cache
         blob, so the N shards don't each hit GDELT

  2. SHARDS   (N containers in parallel)   run_panel_shard()
       - each shard takes every Nth row of the post-attrition active panel
         (row position % N == its index: exactly even sizes, and the new
         joiners — appended at the end — are spread across all shards),
         generates biographies/media_diet for its new joiners, then runs the
         turnout + vote passes
       - progress goes to the shard's OWN checkpoint blob every
         CHECKPOINT_INTERVAL respondents (panels/checkpoints/{week}/...), so
         parallel shards never write the same blob
       - fully resumable: a rerun loads the shard's checkpoint and only
         does what is still pending (failed respondents are retried;
         finished ones cost nothing)

  3. MERGE    (1 container)   merge_panel_shards()
       - concatenates the shard checkpoints, verifies every panellist is
         present exactly once, applies the same completeness check as the
         single-container flow, writes the historical snapshot + active panel,
         folds scraped article text back into the gdelt cache, and sets the
         "panel" job lock. MRP then runs off the historical snapshot as before.

The active panel is not modified between prepare and merge, so row positions
(and therefore shard assignment) are stable across reruns. panelist_id is used
only as the merge key / integrity check, never to decide the split. Backfill runs keep using the single-container
`generate_panel_results_backfill`; this module only covers the production track.
"""
from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path

import pandas as pd

import azure_storage_utils as storage
from .generate_panel_results import (
    ELECTION_DATA_PATH,
    MAX_MISSING_FRACTION,
    IncompleteWaveError,
    _download_strat_frame,
    _load_country_info,
    iso_week_label,
    isoweek_to_panel_date,
)
from .panel.attrition import apply_attrition_and_replacement, PANEL_SIZE, ATTRITION_RATE
from .panel.biography import populate_panel
from .panel.runner import run_survey, load_wave_news, CHECKPOINT_INTERVAL

logger = logging.getLogger(__name__)

# Same lock type the single-container production flow uses, so the two flows
# agree on whether this week's attrition has already been applied.
ATTRITION_LOCK_TYPE = "attrition"

# populate_panel already retries every LLM call 5x; these are extra full
# passes over rows that still failed, so a short API outage doesn't kill the shard.
BIOGRAPHY_PASSES = 3


def _checkpoint_fn(blob_path: str):
    def _checkpoint(current_panel: pd.DataFrame) -> None:
        storage.upload_dataframe(current_panel, blob_path)
    return _checkpoint


def _read_if_exists(blob_path: str) -> pd.DataFrame | None:
    """Like read_dataframe_or_none, but a *transient read error* raises instead
    of being mistaken for 'blob not there' (which could trigger a cold start or
    throw away checkpointed work)."""
    if not storage.blob_exists(blob_path):
        return None
    return storage.read_dataframe(blob_path)


# ───────────────────────────── 1. PREPARE ──────────────────────────────────

def prepare_panel_shards(country: str, year: int, week: int) -> None:
    info = _load_country_info(country)
    question_id = info.get("question_id")
    if not question_id:
        logger.info("Panel not configured for %s — skipping.", country)
        return

    week_label = iso_week_label(year, week)
    panel_date = isoweek_to_panel_date(year, week)
    label = f"{country} {week_label}"

    if storage.already_ran(country, "panel", week_label):
        logger.info("[%s] Panel already complete — nothing to prepare.", label)
        return

    active_panel_path = storage.get_active_panel_path(country)

    # ── attrition + replacement (once per country/week) ──────────────────
    attrition_pending = not storage.already_ran(country, ATTRITION_LOCK_TYPE, week_label)
    if attrition_pending:
        # Only treat the panel as absent (cold start) if the blob really isn't
        # there; a transient read error must not silently cold-start over it.
        panel_df = _read_if_exists(active_panel_path)
        with tempfile.TemporaryDirectory() as tmp:
            strat_frame_path = _download_strat_frame(country, Path(tmp))
            panel_df = apply_attrition_and_replacement(
                panel_df,
                strat_frame_path,
                panel_date=panel_date,
                panel_size=PANEL_SIZE,
                attrition_rate=ATTRITION_RATE,
            )
    else:
        logger.info("[%s] Attrition already applied this week — skipping.", label)
        panel_df = storage.read_dataframe(active_panel_path)

    # Panellists drawn before panelist_id existed have it blank. Mint a
    # persistent id for them once: the merge stage uses it as the key that
    # proves every panellist came back from exactly one shard.
    if "panelist_id" not in panel_df.columns:
        panel_df["panelist_id"] = pd.NA
    panel_df["panelist_id"] = panel_df["panelist_id"].astype(object)
    blank = panel_df["panelist_id"].isna() | (panel_df["panelist_id"].astype(str).str.strip() == "")
    n_blank = int(blank.sum())
    if n_blank:
        panel_df.loc[blank, "panelist_id"] = [str(uuid.uuid4()) for _ in range(n_blank)]
        logger.info("[%s] Assigned panelist_id to %d panellists that had none.", label, n_blank)
    if panel_df["panelist_id"].duplicated().any():
        raise ValueError(f"[{label}] Duplicate panelist_id in the active panel.")

    if attrition_pending or n_blank:
        storage.upload_dataframe(panel_df, active_panel_path)  # before the lock, as in the single-container flow
    if attrition_pending:
        storage.mark_job_ran(country, ATTRITION_LOCK_TYPE, week_label)
        logger.info("[%s] Attrition applied: %d panellists in the active panel.", label, len(panel_df))

    # ── GDELT, downloaded once for all shards ─────────────────────────────
    gdelt_path = storage.get_gdelt_cache_path(country, week_label)
    if storage.blob_exists(gdelt_path):
        logger.info("[%s] GDELT cache already in blob — skipping download.", label)
    else:
        news_df = load_wave_news(question_id, panel_date)  # raises if nothing found
        storage.upload_dataframe(news_df, gdelt_path)
        logger.info("[%s] GDELT cache uploaded (%d rows).", label, len(news_df))


# ───────────────────────────── 2. SHARD ────────────────────────────────────

def run_panel_shard(country: str, year: int, week: int, shard_index: int, num_shards: int) -> None:
    if num_shards < 1 or not 0 <= shard_index < num_shards:
        raise ValueError(f"Invalid shard {shard_index} of {num_shards}.")

    info = _load_country_info(country)
    question_id = info.get("question_id")
    if not question_id:
        logger.info("Panel not configured for %s — skipping.", country)
        return

    week_label = iso_week_label(year, week)
    panel_date = isoweek_to_panel_date(year, week)
    display_name = info.get("alias", country.title())
    label = f"{country} {week_label} shard {shard_index + 1}/{num_shards}"

    if storage.already_ran(country, "panel", week_label):
        logger.info("[%s] Panel already complete for this week — nothing to do.", label)
        return

    # Without this guard a shard would happily run on LAST week's active panel
    # if the prepare stage had failed.
    if not storage.already_ran(country, ATTRITION_LOCK_TYPE, week_label):
        raise RuntimeError(f"[{label}] Prepare stage hasn't completed for {week_label} (no attrition lock).")

    checkpoint_path = storage.get_panel_shard_checkpoint_path(country, week_label, shard_index, num_shards)
    checkpoint = _checkpoint_fn(checkpoint_path)

    # ── load: resume from this shard's checkpoint, else slice the active panel ──
    panel_df = _read_if_exists(checkpoint_path)
    if panel_df is not None:
        logger.info("[%s] Resuming from checkpoint (%d rows).", label, len(panel_df))
    else:
        active = storage.read_dataframe(storage.get_active_panel_path(country))
        if active["panelist_id"].isna().any():
            raise RuntimeError(f"[{label}] Active panel has blank panelist_id values — prepare stage should have filled them.")
        # Stripe by row position: exactly even, and spreads the new joiners
        # (appended at the end) across every shard.
        panel_df = active.iloc[shard_index::num_shards].reset_index(drop=True)
        logger.info("[%s] Took %d of %d panellists from the active panel.", label, len(panel_df), len(active))
        checkpoint(panel_df)

    if panel_df.empty:
        logger.warning("[%s] Empty shard — nothing to do.", label)
        return

    # ── biographies for this shard's new joiners ──────────────────────────
    for attempt in range(1, BIOGRAPHY_PASSES + 1):
        missing_bio = int(panel_df["biography"].isna().sum())
        if not missing_bio:
            break
        logger.info("[%s] Generating %d biographies (pass %d/%d)...", label, missing_bio, attempt, BIOGRAPHY_PASSES)
        panel_df = populate_panel(
            panel_df,
            display_name,
            delay_seconds=0.01,
            date=panel_date,
            generate_events=True,
            articles_path=ELECTION_DATA_PATH,
            on_checkpoint=checkpoint,
            checkpoint_interval=CHECKPOINT_INTERVAL,
        )
        checkpoint(panel_df)

    missing_bio = int(panel_df["biography"].isna().sum())
    if missing_bio:
        # run_survey would otherwise interview these rows with a literal "nan"
        # biography. Fail the shard; a rerun resumes from the checkpoint.
        raise RuntimeError(f"[{label}] {missing_bio} panellists still have no biography after {BIOGRAPHY_PASSES} passes.")

    # ── survey wave (turnout + vote passes) ───────────────────────────────
    gdelt_path = storage.get_gdelt_cache_path(country, week_label)
    news_df = _read_if_exists(gdelt_path)
    if news_df is None:
        raise FileNotFoundError(f"[{label}] No GDELT cache at {gdelt_path} — prepare stage should have created it.")

    panel_df, news_df = run_survey(
        question_id=question_id,
        panel_df=panel_df,
        panel_date=panel_date,
        news_df=news_df,
        on_checkpoint=checkpoint,
    )
    checkpoint(panel_df)  # final state — this is what merge reads
    logger.info("[%s] Shard checkpoint written to %s", label, checkpoint_path)

    # Article text this shard scraped; merge folds it back into the shared cache.
    if "text" in news_df.columns:
        has_text = news_df["text"].notna() & (news_df["text"].astype(str).str.strip() != "")
        if has_text.any():
            storage.upload_dataframe(
                news_df.loc[has_text, ["DocumentIdentifier", "title", "authors", "text"]],
                storage.get_panel_shard_news_path(country, week_label, shard_index, num_shards),
            )

    vote_col = f"{panel_date}_vote"
    missing_votes = int(panel_df[vote_col].isna().sum())
    if missing_votes:
        logger.warning("[%s] %d/%d respondents have no vote answer yet (merge applies the tolerance).",
                       label, missing_votes, len(panel_df))
    logger.info("[%s] Shard complete.", label)


# ───────────────────────────── 3. MERGE ────────────────────────────────────

def _merge_news_caches(country: str, week_label: str, num_shards: int) -> None:
    """Fold each shard's scraped article text back into the week's gdelt cache.
    Best-effort: the cache is an optimisation, so a failure here must not
    fail the panel."""
    try:
        gdelt_path = storage.get_gdelt_cache_path(country, week_label)
        base = _read_if_exists(gdelt_path)
        if base is None:
            return
        extras = []
        for i in range(num_shards):
            path = storage.get_panel_shard_news_path(country, week_label, i, num_shards)
            part = _read_if_exists(path)
            if part is not None:
                extras.append(part)
        if not extras:
            return

        extra = pd.concat(extras, ignore_index=True).drop_duplicates("DocumentIdentifier").set_index("DocumentIdentifier")
        merged = base.drop_duplicates("DocumentIdentifier").set_index("DocumentIdentifier")
        for col in ("title", "authors", "text"):
            current = merged[col].astype(object) if col in merged.columns else pd.Series(pd.NA, index=merged.index, dtype=object)
            merged[col] = current.combine_first(extra[col].astype(object).reindex(merged.index))
        merged = merged.reset_index()
        merged = merged[list(base.columns) + [c for c in merged.columns if c not in base.columns]]
        storage.upload_dataframe(merged, gdelt_path)
        logger.info("[%s %s] GDELT cache updated with article text from %d shard(s).", country, week_label, len(extras))
    except Exception:
        logger.exception("[%s %s] Could not merge shard news caches — continuing.", country, week_label)


def merge_panel_shards(country: str, year: int, week: int, num_shards: int, force: bool = False) -> None:
    info = _load_country_info(country)
    if not info.get("question_id"):
        logger.info("Panel not configured for %s — skipping.", country)
        return

    week_label = iso_week_label(year, week)
    panel_date = isoweek_to_panel_date(year, week)
    label = f"{country} {week_label}"

    if not force and storage.already_ran(country, "panel", week_label):
        logger.info("[%s] Panel results already exist — skipping merge.", label)
        return

    if not storage.already_ran(country, ATTRITION_LOCK_TYPE, week_label):
        raise RuntimeError(f"[{label}] Prepare stage hasn't completed (no attrition lock) — refusing to merge.")

    # ── load every shard ──────────────────────────────────────────────────
    frames, absent = [], []
    for i in range(num_shards):
        path = storage.get_panel_shard_checkpoint_path(country, week_label, i, num_shards)
        part = _read_if_exists(path)
        if part is None:
            absent.append(i)
        else:
            frames.append(part)
    if absent:
        raise FileNotFoundError(f"[{label}] Missing checkpoints for shard(s) {absent} of {num_shards} — rerun them before merging.")

    merged = pd.concat(frames, ignore_index=True, sort=False)

    # ── integrity: every panellist present exactly once; restore original order ──
    active_path = storage.get_active_panel_path(country)
    expected_ids = storage.read_dataframe(active_path)["panelist_id"]
    if merged["panelist_id"].duplicated().any():
        raise ValueError(f"[{label}] Duplicate panelist_id across shards.")
    if set(merged["panelist_id"]) != set(expected_ids):
        raise ValueError(
            f"[{label}] Merged shards don't match the active panel: "
            f"{len(set(expected_ids) - set(merged['panelist_id']))} missing, "
            f"{len(set(merged['panelist_id']) - set(expected_ids))} unexpected."
        )
    position = pd.Series(range(len(expected_ids)), index=expected_ids.values)
    merged = (
        merged.assign(_order=merged["panelist_id"].map(position))
        .sort_values("_order").drop(columns="_order").reset_index(drop=True)
    )

    # ── completeness (same rule as the single-container flow) ─────────────
    vote_col = f"{panel_date}_vote"
    if vote_col not in merged.columns:
        raise ValueError(f"[{label}] Merged panel has no '{vote_col}' column — shards didn't finish the survey.")
    missing_votes = int(merged[vote_col].isna().sum())
    missing_fraction = missing_votes / max(len(merged), 1)

    if missing_fraction > MAX_MISSING_FRACTION:
        raise IncompleteWaveError(
            f"[{label}] {missing_votes}/{len(merged)} respondents ({missing_fraction:.1%}) have no vote "
            f"answer (limit {MAX_MISSING_FRACTION:.1%}). No snapshot written and week not locked — "
            "rerun the workflow: shards resume from their checkpoints and retry only the failed respondents."
        )
    if missing_votes:
        logger.warning("[%s] %d respondents (%.2f%%) have no vote answer — within tolerance, proceeding.",
                       label, missing_votes, missing_fraction * 100)

    # ── persist ───────────────────────────────────────────────────────────
    historical_path = storage.get_historical_panel_path(country, week_label)
    storage.upload_dataframe(merged, historical_path)
    logger.info("[%s] Results snapshot uploaded to %s", label, historical_path)
    storage.upload_dataframe(merged, active_path)
    logger.info("[%s] Active panel state updated.", label)

    _merge_news_caches(country, week_label, num_shards)

    storage.mark_job_ran(country, "panel", week_label)
    logger.info("Panel generation complete: %s (merged %d shards, %d panellists)", label, num_shards, len(merged))
