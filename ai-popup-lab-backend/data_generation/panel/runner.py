"""
Synthetic panel survey runner.

Attrition/replacement is handled separately by `panel.attrition` and run
*before* this, as part of the weekly/backfill orchestration in
`generate_panel_results.py` — by the time `run_survey` runs, `panel_df`
already contains this cycle's new joiners (with biographies + media_diet
populated) alongside existing panellists. This module only runs the survey
wave itself; it does not retire or replace anyone.

Two-stage survey (mirrors the reference pipeline's main.py)
-----------------------------------------------------------
When questions.csv has a turnout question paired with the vote question
(e.g. `us_midterms_turnout` for `us_midterms_1`), a wave is two passes, each
a fully separate conversation per respondent:

  1. TURNOUT pass — every respondent is asked the turnout question
     (system prompt -> turnout question -> optional news reading -> final
     turnout answer). The raw answer is stored in `{panel_date}_turnout`.
  2. VOTE pass — respondents whose turnout answer is "Yes" (i.e. "Yes, I
     will not vote") are assigned "Did not vote" without being asked
     anything further. Everyone else is surveyed on the vote question
     (system prompt -> vote question -> optional news reading -> final
     vote answer), stored in `{panel_date}_vote`.

Countries with no turnout question (e.g. Sweden/Denmark, whose vote
question already offers "Did not vote") run only the vote pass.

News exposure is seeded per respondent (biography hash + panel date), so a
respondent who reads the news, and which articles they read, is the same in
both passes — as in the reference pipeline.

Checkpointing is Azure-only: pass `on_checkpoint` (a callable that uploads the
in-progress panel to blob storage) to get resumability. There is no local-disk
checkpoint file. Each pass resumes from its own column (`_turnout` / `_vote`),
so a crash in either pass picks up where it left off.
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import re

import pandas as pd
import scipy.stats as stats
from tqdm import tqdm

from .chat import send_message, send_message_cohere_rag
from .survey import (
    generate_question, _questions_path, find_unformatted_placeholders,
    get_state_full_name, to_list,
)
from .news import download_weekly_news, fetch_article
from .retry_utils import RetryExhausted

CHECKPOINT_INTERVAL = 50

US_NEWS_DOMAINS = [
    "yahoo.com", "aol.com", "cnn.com", "forbes.com", "foxnews.com",
    "nypost.com", "newsweek.com", "thehill.com", "breitbart.com", "cbsnews.com",
]

logger = logging.getLogger(__name__)


def _persona_label(persona):
    """Prefer the stable panelist_id for logging; fall back to cell_id, then row index."""
    return getattr(persona, "panelist_id", None) or getattr(persona, "cell_id", None) or persona.Index


def _format_citations(citations) -> str:
    """
    Serialize Cohere RAG citations compactly — span offsets + matched text
    only, not the full source document snippets. The raw `Citation` objects
    each embed the entire cached document snippet, which bloats storage and
    duplicates article content already sitting in the GDELT/news cache.
    """
    if not citations:
        return "[]"
    compact = [
        {
            "start": getattr(c, "start", None),
            "end": getattr(c, "end", None),
            "text": getattr(c, "text", None),
        }
        for c in citations
    ]
    return json.dumps(compact)


def _persona_seed(persona, panel_date: str) -> int:
    """
    Deterministic per-respondent seed (biography hash + panel date), so the
    news-reading decision/sample is identical across the turnout and vote
    passes and across resumed runs. Reduced mod 2**32 because numpy's
    RandomState (used by scipy/pandas sampling) rejects larger seeds.
    """
    digest = hashlib.sha256(str(persona.biography).encode("utf-8")).digest()
    return (int.from_bytes(digest, "big") + int(panel_date)) % (2 ** 32)


def _find_turnout_question_id(questions_df: pd.DataFrame, question_id: str) -> str | None:
    """
    Turnout question paired with `question_id`, if questions.csv defines one:
    "us_midterms_1" -> "us_midterms_turnout". Returns None when there isn't
    one (e.g. "se_ge_1"), in which case only the vote pass runs.
    """
    candidate = f"{question_id.rsplit('_', 1)[0]}_turnout"
    return candidate if candidate in set(questions_df["id"]) else None


def _chose_not_to_vote(turnout_answer) -> bool:
    """
    True if the raw turnout answer says the respondent will NOT vote. The
    turnout question's options are "Yes, I will not vote." / "No, I will
    vote." — "Yes" means abstain. Case-insensitive, and tolerant of stray
    leading quotes, bold markers or list numbering ('**Yes, ...', '2. Yes, ...').
    Missing/unparseable answers return False.
    """
    if pd.isna(turnout_answer):
        return False
    text = re.sub(r"^[^a-z]+", "", str(turnout_answer).strip().lower())
    return text.startswith("yes")


def _preflight_turnout_prompts(turnout_question_id: str, panel_df: pd.DataFrame) -> None:
    """
    Fail fast (before any LLM spend) if the turnout prompts aren't fully
    formatted — e.g. an unresolved {state} placeholder would otherwise send a
    literal "{state}" to every respondent.

    Uses the first panel district that actually resolves in
    house_candidates.csv, so one panelist with a bad/missing state_cd doesn't
    abort the whole job (those are skipped per-respondent in _run_pass).
    """
    district = None
    if "state_cd" in panel_df.columns:
        for candidate in panel_df["state_cd"].dropna().unique():
            if get_state_full_name(candidate):
                district = candidate
                break

    for initial in (True, False):
        try:
            prompt = generate_question(turnout_question_id, initial=initial, district=district)
        except ValueError as exc:
            raise RuntimeError(
                f"Turnout prompt preflight failed for '{turnout_question_id}' (initial={initial}); "
                f"no panelist district could be resolved to fill it in: {exc}"
            ) from exc
        leftovers = find_unformatted_placeholders(prompt)
        if leftovers:
            raise RuntimeError(
                f"Turnout prompt for '{turnout_question_id}' (initial={initial}) contains "
                f"unformatted placeholder(s) {sorted(set(leftovers))} — check generate_question "
                f"in survey.py: {prompt!r}"
            )


def _interview_persona(
    *,
    persona,
    question_id: str,
    district,
    panel_df: pd.DataFrame,
    news_df: pd.DataFrame,
    source_common_name: str,
    panel_date: str,
    effort: float,
    news_col_prefix: str,
) -> str:
    """
    One full conversation for one respondent on one question: system prompt ->
    initial question -> (optional) news reading -> final question. Returns the
    final answer text. News interpretation/citations/urls are written onto
    panel_df under `{news_col_prefix}_newsint` / `_citations` / `_article_urls`, so each
    pass keeps its own (turnout: '<date>_turnout_*', vote: '<date>_*').
    """
    newsint_col   = f"{news_col_prefix}_newsint"
    citations_col = f"{news_col_prefix}_citations"
    urls_col      = f"{news_col_prefix}_article_urls"

    system_prompt = f"{str(persona.biography)} \n {str(persona.events_interpretation)}"
    conversation = [{"role": "system", "content": system_prompt}]

    first_prompt = generate_question(question_id, initial=True, district=district)
    first_response = send_message(first_prompt, conversation=conversation)
    conversation += [
        {"role": "user", "content": first_prompt},
        {"role": "assistant", "content": first_response},
    ]

    # --- news coin toss (seeded per respondent so both passes agree) ---
    seed = _persona_seed(persona, panel_date)
    if stats.bernoulli.rvs(effort, random_state=seed) == 1:
        news_read = random.Random(seed).randint(0, 120) * 5 / 20  # approx articles read this week
        readable = news_df.copy()
        readable["SourceCommonName"] = readable["SourceCommonName"].fillna("").str.lower()
        readable["tone_activity"] = pd.to_numeric(readable["tone_activity"], errors="coerce").fillna(0)

        persona_media_diet = getattr(persona, "media_diet", None)
        if pd.notna(persona_media_diet) and str(persona_media_diet).strip():
            media_diet_list = [str(s).strip().lower() for s in to_list(persona_media_diet)]
            readable = readable[readable["SourceCommonName"].isin(media_diet_list)]
        else:
            readable = readable[readable["SourceCommonName"] == source_common_name]

        if not readable.empty:
            n = max(1, min(len(readable), int(round(news_read))))
            sampled = readable.sample(
                n=n, replace=len(readable) < n, weights="tone_activity",
                random_state=seed,
            )
            collected_articles = []
            for _, art_row in sampled.iterrows():
                doc_id = str(art_row["DocumentIdentifier"])
                mask = news_df["DocumentIdentifier"].astype(str) == doc_id
                cached = news_df.loc[mask].iloc[0] if mask.any() else None
                if cached is not None and pd.notna(cached.get("text")) and str(cached.get("text")).strip():
                    article = {
                        "title": cached.get("title"),
                        "authors": cached.get("authors"),
                        "text": cached.get("text"),
                    }
                else:
                    article = fetch_article(doc_id)
                    news_df.loc[mask, "title"]   = article["title"]
                    news_df.loc[mask, "authors"] = article["authors"]
                    news_df.loc[mask, "text"]    = article["text"]
                collected_articles.append(article)

            prompt_news = (
                "You will now be presented with a number of articles that you have read this week. "
                "Embodying your persona entirely, interpret these articles in light of the question "
                "that has been asked. Consider your previous thought process, and whether any of the "
                "information in these articles would change your mind. It is equally likely that none "
                "of these articles will change your mind and that they might not be related to the "
                "question whatsoever. Respond with a 300-600 word interpretation of these articles "
                "and how they do or don't relate to the question."
            )
            answer, citations = send_message_cohere_rag(prompt_news, conversation, collected_articles)
            panel_df.at[persona.Index, newsint_col]   = answer
            panel_df.at[persona.Index, citations_col] = _format_citations(citations)
            panel_df.at[persona.Index, urls_col]      = str(sampled["DocumentIdentifier"].tolist())
            conversation += [
                {"role": "user", "content": prompt_news},
                {"role": "assistant", "content": answer},
            ]

    # --- final answer ---
    second_prompt = generate_question(question_id, initial=False, district=district)
    return send_message(second_prompt, conversation=conversation)


def _run_pass(
    *,
    pass_name: str,
    question_id: str,
    answer_col: str,
    news_col_prefix: str,
    rows: pd.DataFrame,
    panel_df: pd.DataFrame,
    news_df: pd.DataFrame,
    country_code: str,
    source_common_name: str,
    panel_date: str,
    effort: float,
    on_checkpoint,
) -> None:
    """Interview every respondent in `rows` on `question_id`, writing each
    final answer into `panel_df[answer_col]`. Failed/skipped respondents are
    left empty so a rerun picks them up."""
    done = 0
    for persona in tqdm(rows.itertuples(), total=len(rows), desc=f"Surveying [{country_code}] {pass_name}"):
        try:
            district = None
            if country_code == "us":
                district = getattr(persona, "state_cd", None)
                if not district or pd.isna(district):
                    logger.warning("Persona %s has no state_cd — skipping.", _persona_label(persona))
                    continue
                if get_state_full_name(district) is None:
                    logger.warning(
                        "No house_candidates.csv match for district '%s' — skipping persona %s.",
                        district, _persona_label(persona),
                    )
                    continue

            answer = _interview_persona(
                persona=persona,
                question_id=question_id,
                district=district,
                panel_df=panel_df,
                news_df=news_df,
                source_common_name=source_common_name,
                panel_date=panel_date,
                effort=effort,
                news_col_prefix=news_col_prefix,
            )
            panel_df.at[persona.Index, answer_col] = answer
            done += 1

        except RetryExhausted as exc:
            logger.error(
                "[%s pass] Survey generation failed for persona %s after retries — skipping this run: %s",
                pass_name, _persona_label(persona), exc,
            )
            continue
        except Exception:
            logger.exception(
                "[%s pass] Unexpected error surveying persona %s — skipping this run.",
                pass_name, _persona_label(persona),
            )
            continue
        else:
            if on_checkpoint and done % CHECKPOINT_INTERVAL == 0:
                on_checkpoint(panel_df)


def run_survey(
    question_id: str,
    panel_df: pd.DataFrame,
    panel_date: str,
    news_df: pd.DataFrame | None = None,
    effort: float = 0.5,
    on_checkpoint=None,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """
    Run one survey wave on panel_df (existing panellists + this cycle's new
    joiners together — attrition/replacement must already have happened).

    If questions.csv defines a turnout question paired with `question_id`
    (e.g. us_midterms_turnout for us_midterms_1), the wave is two passes:
    a turnout pass over the whole panel, then a vote pass over respondents
    who didn't opt out ("Did not vote" is assigned to those who did).

    Args:
        question_id:    Vote question ID, e.g. 'us_midterms_1'.
        panel_df:       Active panel DataFrame (must contain `biography` for every row).
        panel_date:     ISO date string or YYYYMMDD; used to name this wave's columns.
        news_df:        Pre-loaded GDELT DataFrame, or None to download automatically.
        effort:         Probability (0-1) that a respondent reads news this wave.
        on_checkpoint:  Optional callable(panel_df) called every CHECKPOINT_INTERVAL respondents.

    Returns:
        (updated_panel_df, news_df)
    """
    panel_date = pd.to_datetime(panel_date).normalize().strftime("%Y%m%d")
    panel_end_date = pd.to_datetime(panel_date)
    # Local survey-logic code derived from the question id (e.g. "us" from
    # "us_midterms_1"). This is NOT the storage country key ("usa") — never
    # use this value to build a blob path.
    country_code = question_id.split("_")[0]

    questions_df = pd.read_csv(_questions_path())
    question_row = questions_df.loc[questions_df["id"] == question_id].iloc[0]
    source_common_name = str(question_row["news"]).strip().lower()
    turnout_question_id = _find_turnout_question_id(questions_df, question_id)

    # per-country domain filter: the news question filters on sources like 'dn.se',
    # which can never appear in a .com-only download
    if news_df is None:
        if country_code == "us":
            news_df = download_weekly_news(
                start_date=panel_end_date - pd.Timedelta(days=7),
                end_date=panel_end_date,
                domain=US_NEWS_DOMAINS,
                save_csv=False,
            )
        else:
            news_df = download_weekly_news(
                start_date=panel_end_date - pd.Timedelta(days=7),
                end_date=panel_end_date,
                domain=f".{country_code}",
                save_csv=False,
            )
    if news_df is None:
        raise RuntimeError(f"No GDELT news data available for '{country_code}' around {panel_date}.")

    for col in ("title", "authors", "text"):
        if col not in news_df.columns:
            news_df[col] = pd.NA

    turnout_col   = f"{panel_date}_turnout"
    vote_col      = f"{panel_date}_vote"
    newsint_col   = f"{panel_date}_newsint"
    citations_col = f"{panel_date}_citations"
    urls_col      = f"{panel_date}_article_urls"

    turnout_news_cols = [f"{turnout_col}_newsint", f"{turnout_col}_citations", f"{turnout_col}_article_urls"]
    wave_cols = [vote_col, newsint_col, citations_col, urls_col]
    if turnout_question_id:
        wave_cols = [turnout_col, *turnout_news_cols] + wave_cols
    for col in wave_cols:
        if col not in panel_df.columns:
            panel_df[col] = None
        # A column that was entirely empty when the panel was last saved comes
        # back from CSV as float64; force object so string answers can be set.
        panel_df[col] = panel_df[col].astype(object)

    pass_kwargs = dict(
        panel_df=panel_df,
        news_df=news_df,
        country_code=country_code,
        source_common_name=source_common_name,
        panel_date=panel_date,
        effort=effort,
        on_checkpoint=on_checkpoint,
    )

    # ── Pass 1: turnout (whole panel) ────────────────────────────────────
    if turnout_question_id:
        pending_turnout = panel_df[panel_df[turnout_col].isna() & panel_df[vote_col].isna()]
        if pending_turnout.empty:
            logger.info("[%s] Turnout pass: nothing pending.", country_code)
        else:
            logger.info(
                "[%s] Turnout pass (%s): %d respondents pending.",
                country_code, turnout_question_id, len(pending_turnout),
            )
            _preflight_turnout_prompts(turnout_question_id, panel_df)
            _run_pass(
                pass_name="turnout",
                question_id=turnout_question_id,
                answer_col=turnout_col,
                news_col_prefix=turnout_col,
                rows=pending_turnout,
                **pass_kwargs,
            )

        # Abstainers get "Did not vote" without a vote conversation. Derived
        # from the turnout column each run, so it's safe to repeat on resume.
        abstain = panel_df[vote_col].isna() & panel_df[turnout_col].apply(_chose_not_to_vote)
        if abstain.any():
            panel_df.loc[abstain, vote_col] = "Did not vote"
            logger.info("[%s] %d respondents opted out of voting.", country_code, int(abstain.sum()))
            if on_checkpoint:
                on_checkpoint(panel_df)

    # ── Pass 2: vote (everyone who didn't opt out) ───────────────────────
    pending_vote = panel_df[panel_df[vote_col].isna()]
    if turnout_question_id:
        # Respondents whose turnout pass failed have no turnout answer: leave
        # them empty (a rerun retries the turnout pass) rather than silently
        # treating them as voters.
        no_turnout = pending_vote[turnout_col].isna()
        if no_turnout.any():
            logger.warning(
                "[%s] %d respondents have no turnout answer — skipping them in the vote pass.",
                country_code, int(no_turnout.sum()),
            )
        pending_vote = pending_vote[~no_turnout]

    if pending_vote.empty:
        logger.info("[%s] Vote pass: nothing pending.", country_code)
        return panel_df, news_df

    logger.info("[%s] Vote pass (%s): %d respondents pending.", country_code, question_id, len(pending_vote))
    _run_pass(
        pass_name="vote",
        question_id=question_id,
        answer_col=vote_col,
        news_col_prefix=panel_date,
        rows=pending_vote,
        **pass_kwargs,
    )

    return panel_df, news_df
