"""
Synthetic panel survey runner.

Attrition/replacement is handled separately by `panel.attrition` and run
*before* this, as part of the weekly/backfill orchestration in
`generate_panel_results.py` — by the time `run_survey` runs, `panel_df`
already contains this cycle's new joiners (with biographies + media_diet
populated) alongside existing panellists. This module only runs the survey
wave itself; it does not retire or replace anyone.

Checkpointing is Azure-only: pass `on_checkpoint` (a callable that uploads the
in-progress panel to blob storage) to get resumability. There is no local-disk
checkpoint file.
"""
from __future__ import annotations

import json
import logging
import random

import pandas as pd
import scipy.stats as stats
from tqdm import tqdm

from .chat import send_message, send_message_cohere_rag
from .survey import generate_question, _questions_path, generate_turnout_question, get_district_info, to_list
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

    Args:
        question_id:    Survey question ID, e.g. 'us_midterms_1'.
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

    vote_col      = f"{panel_date}_vote"
    newsint_col   = f"{panel_date}_newsint"
    citations_col = f"{panel_date}_citations"
    urls_col      = f"{panel_date}_article_urls"

    for col in (vote_col, newsint_col, citations_col, urls_col):
        if col not in panel_df.columns:
            panel_df[col] = None

    pending = panel_df[panel_df[vote_col].isna()]
    if pending.empty:
        return panel_df, news_df

    completed = int(panel_df[vote_col].notna().sum())

    for persona in tqdm(pending.itertuples(), total=len(pending), desc=f"Surveying [{country_code}]"):
        try:
            conversation = [{"role": "system", "content": str(persona.biography)}]

            district = getattr(persona, "state_cd", None) if country_code == "us" else None

            first_prompt = generate_question(question_id, initial=True, district=district)
            first_response = send_message(first_prompt, conversation=conversation)
            conversation += [
                {"role": "user", "content": first_prompt},
                {"role": "assistant", "content": first_response},
            ]

            # --- news coin toss ---
            if stats.bernoulli.rvs(effort) == 1:
                news_read = random.randint(0, 120) * 5 / 20  # approx articles read this week
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
                        random_state=int(panel_date),
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

            # --- turnout gate (US only) ---
            if country_code == "us":
                district = getattr(persona, "state_cd", None)
                if not district:
                    logger.warning("Persona %s has no state_cd — skipping.", _persona_label(persona))
                    continue

                _, full_state_name = get_district_info(district)
                if full_state_name is None:
                    logger.warning(
                        "No house_candidates.csv match for district '%s' — skipping persona %s.",
                        district, _persona_label(persona),
                    )
                    continue

                turnout_prompt = generate_turnout_question(full_state_name)
                turnout_response = send_message(turnout_prompt, conversation=conversation)
                conversation += [
                    {"role": "user", "content": turnout_prompt},
                    {"role": "assistant", "content": turnout_response},
                ]
                if turnout_response.strip().lower() == "yes":
                    panel_df.at[persona.Index, vote_col] = "Did not vote"
                    completed += 1
                    if on_checkpoint and completed % CHECKPOINT_INTERVAL == 0:
                        on_checkpoint(panel_df)
                    continue

            # --- final vote choice ---
            second_prompt   = generate_question(question_id, initial=False, district=district)
            second_response = send_message(second_prompt, conversation=conversation)
            panel_df.at[persona.Index, vote_col] = second_response
            completed += 1

        except RetryExhausted as exc:
            logger.error(
                "Survey generation failed for persona %s after retries — skipping this run: %s",
                _persona_label(persona), exc,
            )
            continue
        except Exception:
            logger.exception("Unexpected error surveying persona %s — skipping this run.", _persona_label(persona))
            continue

        if on_checkpoint and completed % CHECKPOINT_INTERVAL == 0:
            on_checkpoint(panel_df)

    return panel_df, news_df
