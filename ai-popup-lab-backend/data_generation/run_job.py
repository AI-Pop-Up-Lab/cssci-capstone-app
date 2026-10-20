"""
Entry point for the weekly data generation worker container.

Run locally (no Docker):
    export $(cat .env | xargs)
    python -m data_generation.run_job

Env variables:
    COUNTRIES  comma-separated country names, e.g. "usa" or "usa,sweden"
    JOB_TYPE   comma-separated stages (default: panel). One or more of:
                 orchestrate    start/supervise the sharded run's containers inside Azure
                                (what the GitHub workflow launches; see orchestrator.py)
                 panel_prepare  sharded run, stage 1: attrition + one GDELT download
                 panel_shard    sharded run, stage 2: one shard (needs SHARD_INDEX, NUM_SHARDS)
                 panel_merge    sharded run, stage 3: merge shards -> snapshot + active panel
                 mrp            MRP extended frame + longitudinal aggregates
                 panel          legacy single-container panel cycle (no sharding)
                 both           legacy: panel + mrp
    PIPELINE_JOB_TYPE  mrp | panel | both — what `orchestrate` should run (default: both)
    SHARD_INDEX / NUM_SHARDS   used by panel_shard (index 0..NUM_SHARDS-1) and panel_merge
    TARGET_WEEK  optional YYYY-WW override (weekly-job.yml always passes one so every
                 stage of a run agrees on the week)

Countries are processed one after another in a simple loop — the pipeline
runs identically regardless of how many countries are listed, so adding a
second/third country later (e.g. "usa,sweden") needs no code changes here,
only a COUNTRIES value and a configured entry in country_data_info.json.
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

from .generate_panel_results import generate_panel_results, iso_week_label, isoweek_to_panel_date
from .generate_panel_sharded import prepare_panel_shards, run_panel_shard, merge_panel_shards
from .run_scripts import check_r_available, run_extension_script
from .aggregate_longitudinal import update_longitudinal_aggregates, update_longitudinal_national_summary
from .fetch_us_polls import fetch_and_store_us_polls

import azure_storage_utils as storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Comma-separated list of country names, e.g. "usa" or "usa,sweden"
COUNTRIES = [c.strip() for c in os.environ.get("COUNTRIES", "usa").split(",") if c.strip()]

# What to run: one or more comma-separated stages (see module docstring).
JOB_TYPE = os.environ.get("JOB_TYPE", "panel").lower()
JOB_TYPES = {t.strip() for t in JOB_TYPE.split(",") if t.strip()}
if "both" in JOB_TYPES:
    JOB_TYPES |= {"panel", "mrp"}

# Sharded panel run. NUM_SHARDS must be identical across the prepare / shard /
# merge stages of one run (it is baked into the checkpoint blob names).
NUM_SHARDS = int(os.environ.get("NUM_SHARDS", "9"))
PIPELINE_JOB_TYPE = os.environ.get("PIPELINE_JOB_TYPE", "both").strip().lower()
SHARD_INDEX = int(os.environ.get("SHARD_INDEX", "0"))

# If False (the default), skip the memory-heavy simulation-draws phase of
# MRP entirely — quartile/uncertainty tables and CD-level breakdowns won't
# be produced, but extended_frame (the file the rest of the pipeline
# actually consumes right now) is computed earlier and unaffected. Flip to
# true via env var when those other outputs are needed again, without a
# code change.
#
# NOTE: as of the current post_strat_module_us.R, this no longer actually
# skips anything for country == "usa" — that module always runs the full
# draws phase regardless of what's passed here (its only remaining
# draws-related toggle, config$export_cell_draws, just controls whether
# the raw per-cell draw matrix gets written). Left in place — still passed
# through to run_extension_script/the R CLI — in case a country module
# reintroduces a real gate, but expect every USA MRP run to now take as
# long as a "full draws" run used to, whatever this is set to.
COMPUTE_MRP_DRAWS = os.environ.get("COMPUTE_MRP_DRAWS", "false").strip().lower() in ("true", "1", "yes")


# File the R script writes that gets archived (per week) alongside the
# extended frame. Change this one constant if the R output is renamed.
NATIONAL_SUMMARY_R_FILENAME = "mrp_national_summary_95ci.csv"


def _this_week() -> tuple[int, int]:
    """
    Returns the ISO (year, week) to run against. Defaults to the current
    week, but can be overridden with TARGET_WEEK=YYYY-WW (e.g. "2026-35") —
    for retrying a step (most commonly MRP) against a specific past week's
    already-completed production data, without waiting for that week to
    roll back around or misusing the backfill track (which reads/writes a
    separate storage path, not this week's real production panel).
    """
    override = os.environ.get("TARGET_WEEK", "").strip()
    if override:
        try:
            year_str, week_str = override.split("-")
            return int(year_str), int(week_str)
        except ValueError:
            raise ValueError(
                f"Invalid TARGET_WEEK format: '{override}'. Expected YYYY-WW (e.g. 2026-35)."
            )
    today = date.today()
    year, week, _ = today.isocalendar()
    return year, week


def _rename_state_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    The post-stratification R module (post_strat_module.R, currently the US
    variant) expects a `state_abbrv` column with no alias fallback — unlike
    most of its other required columns, it will NOT fall back to `state`.
    Our pipeline uses `state` everywhere else, so rename here rather than
    upstream, since `state` is the established name for every other
    consumer of the frame/panel.
    """
    if "state" in df.columns and "state_abbrv" not in df.columns:
        df = df.rename(columns={"state": "state_abbrv"})
    return df


def _prepare_frame_for_r(frame_df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename `state` -> `state_abbrv`, and disambiguate the frame's two
    population-weight columns for R's `expected_N_raked` alias.

    The frame carries both `expected_N` (= old_N * prob, i.e. UNraked) and
    `N` (= cell total * prob_raked, i.e. the properly RAKED/corrected
    weight — verified against the actual sample data: old_N * prob equals
    expected_N exactly, and cell_total_N * prob_raked equals N exactly).
    R's alias list for `expected_N_raked` checks `expected_N` before `N`,
    which would silently pick the unraked figure. Rename `N` explicitly
    instead of relying on that alias order, and drop `expected_N` so
    there's no ambiguity even if R's alias list changes later. This also
    keeps the frame consistent with panel.attrition, which already samples
    replacement panellists weighted by `N`.
    """
    frame_df = _rename_state_column(frame_df)
    if "expected_N_raked" not in frame_df.columns:
        if "N" in frame_df.columns:
            frame_df = frame_df.rename(columns={"N": "expected_N_raked"})
        if "expected_N" in frame_df.columns:
            frame_df = frame_df.drop(columns=["expected_N"])
    return frame_df


# Raw vote-choice text may be a bare "Did not vote", or a district-race
# answer in the "Name (Party Party)" format `survey.py` generates options
# in (e.g. "Jane Smith (Democratic Party)", "Pat Lee (Libertarian Party)").
# R's model treats every distinct `predicted_vote` value as its own outcome
# category, so left unnormalized this would produce a one-off category per
# candidate name instead of collapsing to the three-party view
# country_data_info.json's `party_colours` expects. "Did not vote" is left
# untouched — aggregate_longitudinal.py specifically filters on that exact
# string to exclude non-voters from party-share calculations.
def _normalize_party(raw_vote) -> str:
    if pd.isna(raw_vote):
        return raw_vote
    text = str(raw_vote).strip()
    if text.lower() == "did not vote":
        return "Did not vote"
    lowered = text.lower()
    if "democrat" in lowered:
        return "Democrat"
    if "republican" in lowered:
        return "Republican"
    return "Other"


def _prepare_survey_for_r(survey_df: pd.DataFrame, panel_date: str) -> pd.DataFrame:
    """
    Rename `state` -> `state_abbrv`, and build a `predicted_vote` (aliased
    to `vote_2026`) column — the panel stores this week's answers as
    `{panel_date}_vote` dynamically (every week's answers accumulate as
    their own column), so copy that week's column over under the name R
    expects, normalized down to Democrat / Republican / Other / Did not vote.
    """
    survey_df = _rename_state_column(survey_df)
    vote_col = f"{panel_date}_vote"
    if vote_col not in survey_df.columns:
        raise ValueError(
            f"Expected this week's vote column '{vote_col}' in the survey results, "
            f"but it wasn't found. Panel/survey must have completed for this week "
            f"before MRP can run."
        )
    survey_df = survey_df.copy()
    survey_df["predicted_vote"] = survey_df[vote_col].apply(_normalize_party)
    return survey_df


def _prepare_extended_frame_for_longitudinal(extended_frame: pd.DataFrame) -> pd.DataFrame:
    """
    aggregate_longitudinal.py (and the frontend charts consuming its output)
    expect columns named `party` (outcome), `prob_raked` (weight), and
    `state` (demographic dimension) — but the US R module's extended-frame
    output names these `vote_2026`, `expected_N`, and `state_abbrv`
    respectively (the latter because the R module itself requires that
    exact name with no alias fallback — see _prepare_frame_for_r). Rename
    on a copy here rather than upstream, so the blob uploaded to
    get_extended_frame_path keeps the R script's native column names for
    any other consumer.
    """
    return extended_frame.rename(columns={
        "vote_2026": "party",
        "expected_N": "prob_raked",
        "state_abbrv": "state",
    })


def _run_mrp(country: str, year: int, week: int, backfill: bool = False, force: bool = False) -> None:
    """
    Run the MRP extended-frame R script for `country` / ISO week
    `year`-W`week` and fold the result into the longitudinal aggregates.

    `backfill=True` reads this week's survey results from the backfill
    historical-panel track (get_backfill_historical_panel_path) instead of
    the production one, and locks under a separate "mrp_backfill" job type
    so a backfill MRP run never collides with, or gets skipped by, a
    production MRP run for the same week.
    """
    week_label = iso_week_label(year, week)
    panel_date = isoweek_to_panel_date(year, week)
    job_type = "mrp_backfill" if backfill else "mrp"

    if not force and storage.already_ran(country, job_type, week_label):
        logger.info("MRP already ran for %s %s (job_type=%s) — skipping.", country, week_label, job_type)
        return

    survey_blob_path = (
        storage.get_backfill_historical_panel_path(country, week_label)
        if backfill else
        storage.get_historical_panel_path(country, week_label)
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        frame_path = tmp_path / f"{country}_strat_frame.csv"
        frame_df = storage.read_dataframe(storage.get_stratification_frame_path(country))
        frame_df = _prepare_frame_for_r(frame_df)
        frame_df.to_csv(frame_path, index=False)

        # Static per-country input the updated US vglmer formula requires
        # (state-level presidential + district-level congressional vote
        # shares). Only the US module takes this — post_strat_module_dk_se.R
        # doesn't, so don't require it for other countries.
        area_shares_path = None
        if country.lower() == "usa":
            area_shares_blob = storage.get_area_level_vote_shares_path(country)
            area_shares_df = storage.read_dataframe_or_none(area_shares_blob)
            if area_shares_df is None:
                raise FileNotFoundError(
                    f"No area-level vote shares file found for {country} "
                    f"(expected blob: {area_shares_blob}). Upload it before running MRP — "
                    f"post_strat_module_us.R's run_post_stratification() requires it."
                )
            area_shares_path = tmp_path / f"{country}_area_level_vote_shares.csv"
            area_shares_df.to_csv(area_shares_path, index=False)

        survey_df = storage.read_dataframe_or_none(survey_blob_path)
        if survey_df is None:
            raise FileNotFoundError(
                f"No panel results found for {country} {week_label} "
                f"(expected blob: {survey_blob_path}). "
                f"Panel must run successfully before MRP for the same week."
            )
        survey_df = _prepare_survey_for_r(survey_df, panel_date)
        survey_path = tmp_path / f"{country}_{week_label}_panel_results.csv"
        survey_df.to_csv(survey_path, index=False)

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        run_extension_script(
            survey_path=survey_path,
            frame_path=frame_path,
            output_dir=output_dir,
            country=country,
            compute_draws=COMPUTE_MRP_DRAWS,
            area_shares_path=area_shares_path,
        )

        r_output_path = output_dir / "mrp_extended_frame_predictions.csv"
        if not r_output_path.exists():
            raise FileNotFoundError(f"Expected R output not found: {r_output_path}")

        extended_frame = pd.read_csv(r_output_path)

        extended_frame_path = (
            storage.get_backfill_extended_frame_path(country, week_label)
            if backfill else
            storage.get_extended_frame_path(country, week_label)
        )
        storage.upload_dataframe(extended_frame, extended_frame_path)
        logger.info("[%s] Extended frame uploaded for %s.", country, week_label)

        national_summary_r_path = output_dir / NATIONAL_SUMMARY_R_FILENAME
        national_summary_exists = national_summary_r_path.exists()
        if national_summary_exists:
            national_summary_blob_path = (
                storage.get_backfill_national_summary_path(country, week_label)
                if backfill else
                storage.get_national_summary_path(country, week_label)
            )
            storage.upload_file(national_summary_r_path, national_summary_blob_path)
            logger.info("[%s] National summary uploaded for %s.", country, week_label)
        else:
            logger.warning(
                "[%s] %s not found in R output for %s — national summary not uploaded.",
                country, NATIONAL_SUMMARY_R_FILENAME, week_label,
            )

        if backfill:
            logger.info(
                "[%s] Skipping longitudinal aggregate update for %s — backfill runs never "
                "touch production aggregates.",
                country, week_label,
            )
        else:
            update_longitudinal_aggregates(
                country=country,
                extended_frame=_prepare_extended_frame_for_longitudinal(extended_frame),
                year=year,
                week=week,
                blob_client=storage.get_blob_service_client(),
                container=storage.CONTAINER_NAME,
            )
            if national_summary_exists:
                update_longitudinal_national_summary(
                    country=country,
                    year=year,
                    week=week,
                    blob_client=storage.get_blob_service_client(),
                    container=storage.CONTAINER_NAME,
                    summary_df=pd.read_csv(national_summary_r_path),
                )
            else:
                logger.warning(
                    "[%s] No national summary for %s — national summary aggregate not updated.",
                    country, week_label,
                )

    storage.mark_job_ran(country, job_type, week_label)
    logger.info("MRP complete: %s %s (job_type=%s)", country, week_label, job_type)


def run_country_job(country: str, year: int, week: int) -> None:
    """
    Run the configured job(s) for a single country. Each step manages its
    own job-lock check/skip internally (see generate_panel_results and
    _run_mrp above), so this function is just sequencing, not lock
    bookkeeping.
    """
    if "panel" in JOB_TYPES:
        logger.info("[%s] Running panel cycle (%d-W%02d)...", country, year, week)
        generate_panel_results(country=country, year=year, week=week, force=False)
        logger.info("[%s] Panel cycle done.", country)

    if "panel_prepare" in JOB_TYPES:
        logger.info("[%s] Preparing sharded panel run (%d-W%02d)...", country, year, week)
        prepare_panel_shards(country=country, year=year, week=week)
        logger.info("[%s] Prepare done.", country)

    if "panel_shard" in JOB_TYPES:
        logger.info("[%s] Running shard %d/%d (%d-W%02d)...", country, SHARD_INDEX + 1, NUM_SHARDS, year, week)
        run_panel_shard(country=country, year=year, week=week, shard_index=SHARD_INDEX, num_shards=NUM_SHARDS)
        logger.info("[%s] Shard done.", country)

    if "panel_merge" in JOB_TYPES:
        logger.info("[%s] Merging %d shards (%d-W%02d)...", country, NUM_SHARDS, year, week)
        merge_panel_shards(country=country, year=year, week=week, num_shards=NUM_SHARDS, force=False)
        logger.info("[%s] Merge done.", country)

    if "mrp" in JOB_TYPES:
        logger.info("[%s] Running MRP...", country)
        _run_mrp(country=country, year=year, week=week, backfill=False, force=False)
        logger.info("[%s] MRP done.", country)


def main() -> None:
    year, week = _this_week()

    # Orchestrator container: starts and supervises the prepare / shard /
    # finalize containers via the ACI API, then exits. Does no pipeline work itself.
    if "orchestrate" in JOB_TYPES:
        from .orchestrator import run_orchestrator
        try:
            run_orchestrator(
                countries=COUNTRIES, year=year, week=week,
                pipeline_job_type=PIPELINE_JOB_TYPE, num_shards=NUM_SHARDS,
            )
        except Exception:
            logger.exception("Orchestration failed")
            sys.exit(1)
        return

    if "mrp" in JOB_TYPES:
        check_r_available()

    failed: list[str] = []

    # Runs once per workflow, in the final stage — not in the prepare/shard
    # containers, where it would run 1 + NUM_SHARDS redundant times.
    if JOB_TYPES & {"panel", "panel_merge", "mrp"}:
        try:
            fetch_and_store_us_polls()
        except Exception:
            logger.exception("US polls pipeline failed")
            failed.append("usa_pollsters_download")

    for country in COUNTRIES:
        logger.info("Processing country: %s", country)
        try:
            run_country_job(country, year, week)
        except Exception:
            logger.exception("Country failed: %s", country)
            failed.append(country)

    if failed:
        logger.error("Job finished with failures: %s", failed)
        sys.exit(1)
    else:
        logger.info("All countries succeeded.")


if __name__ == "__main__":
    main()
