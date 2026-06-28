"""
Synthetic panel survey runner.
Adapted from the panel project main.py.
All I/O (blob, local files) is handled by the caller; this module is pure logic.
"""
from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
import scipy.stats as stats
from tqdm import tqdm

from .biography import populate_panel
from .chat import send_message, send_message_cohere_rag
from .survey import generate_question, _questions_path
from .news import download_weekly_news, fetch_article

CHECKPOINT_INTERVAL = 10

_COUNTRY_NAMES = {
    "se": "Sweden",
    "nl": "Netherlands",
    "dk": "Denmark",
}


def _country_display_name(country_code: str) -> str:
    return _COUNTRY_NAMES.get(country_code, country_code.upper())


def _clear_wave_columns(panel_df: pd.DataFrame) -> pd.DataFrame:
    wave_cols = [
        c for c in panel_df.columns
        if len(c) >= 9 and c[:8].isdigit() and c[8] == "_"
    ]
    for c in wave_cols:
        panel_df[c] = pd.NA
    return panel_df


def _build_replacement_panelists(
    panel_name: str,
    country_code: str,
    active_columns,
    excluded_ids: set,
    replacement_count: int,
    panel_date: str,
    panels_dir: Path,
) -> pd.DataFrame:
    if replacement_count <= 0:
        return pd.DataFrame(columns=active_columns)

    source_path = panels_dir / f"{panel_name}.csv"
    if not source_path.exists():
        return pd.DataFrame(columns=active_columns)

    pool = pd.read_csv(source_path)
    if "cell_id" in pool.columns:
        pool = pool[~pool["cell_id"].isin(excluded_ids)]
    if pool.empty:
        return pd.DataFrame(columns=active_columns)

    sample_size = min(replacement_count, len(pool))
    pool = pool.sample(n=sample_size, random_state=int(panel_date)).copy()
    if "biography" not in pool.columns:
        pool["biography"] = pd.NA

    country_name = _country_display_name(country_code)
    # Biographies are generated in-memory; checkpoint written to a temp path
    checkpoint_tmp = panels_dir / f"{country_code}_replacement_bios_tmp.csv"
    pool = populate_panel(
        pool,
        country_name,
        delay_seconds=0.01,
        checkpoint_path=str(checkpoint_tmp),
    )
    pool = pool.reindex(columns=active_columns, fill_value=pd.NA)
    pool = _clear_wave_columns(pool)
    return pool


def run_survey(
    question_id: str,
    panel_df: pd.DataFrame,
    panel_date: str,
    news_df: pd.DataFrame | None = None,
    attrition_rate: float = 0.1,
    effort: float = 0.5,
    panels_dir: Path | None = None,
    panel_name: str | None = None,
    on_checkpoint=None,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """
    Run one survey wave on panel_df.

    Args:
        question_id:    Survey question ID, e.g. 'se_ge_1'.
        panel_df:       Active panel DataFrame (must contain a 'biography' column).
        panel_date:     ISO date string or YYYYMMDD; used to name wave columns.
        news_df:        Pre-loaded GDELT DataFrame, or None to download automatically.
        attrition_rate: Fraction of panelists replaced after each wave.
        effort:         Probability (0–1) that a respondent reads news this wave.
        panels_dir:     Path to directory holding base panel CSVs (for attrition replacement).
        panel_name:     Stem of the base panel CSV (e.g. 'sweden_panel_40').
        on_checkpoint:  Optional callable(panel_df) called every CHECKPOINT_INTERVAL respondents.

    Returns:
        (updated_panel_df, news_df)
    """
    panel_date = pd.to_datetime(panel_date).normalize().strftime("%Y%m%d")
    panel_end_date = pd.to_datetime(panel_date)
    country_code = question_id.split("_")[0]

    # Load question metadata for news source filter
    questions_df = pd.read_csv(_questions_path())
    question_row = questions_df.loc[questions_df["id"] == question_id].iloc[0]
    source_common_name = str(question_row["news"]).strip().lower()

    # Download GDELT if not provided
    if news_df is None:
        news_df = download_weekly_news(
            start_date=panel_end_date - pd.Timedelta(days=7),
            end_date=panel_end_date,
            domain=f".{country_code}",
            save_csv=False,
        )
    if news_df is None:
        raise RuntimeError(
            f"No GDELT news data available for '{country_code}' around {panel_date}."
        )

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
        # --- Step 1: initial thought process ---
        conversation = [{"role": "system", "content": str(persona.biography)}]
        first_prompt = generate_question(question_id, initial=True)
        first_response = send_message(first_prompt, conversation=conversation)
        conversation += [
            {"role": "user",      "content": first_prompt},
            {"role": "assistant", "content": first_response},
        ]

        # --- Step 2: maybe read news ---
        if stats.bernoulli.rvs(effort) == 1:
            news_read = random.randint(0, 120) * 5 / 20  # approx articles per week
            readable = news_df.copy()
            readable["SourceCommonName"] = (
                readable["SourceCommonName"].fillna("").str.lower()
            )
            readable["tone_activity"] = pd.to_numeric(
                readable["tone_activity"], errors="coerce"
            ).fillna(0)
            readable = readable[readable["SourceCommonName"] == source_common_name]

            if not readable.empty:
                n = max(1, min(len(readable), int(round(news_read))))
                sampled = readable.sample(
                    n=n,
                    replace=len(readable) < n,
                    weights="tone_activity",
                    random_state=int(panel_date),
                )
                collected_articles = []
                for _, art_row in sampled.iterrows():
                    doc_id = str(art_row["DocumentIdentifier"])
                    mask = news_df["DocumentIdentifier"].astype(str) == doc_id
                    cached = news_df.loc[mask].iloc[0] if mask.any() else None
                    if (
                        cached is not None
                        and pd.notna(cached.get("text"))
                        and str(cached.get("text")).strip()
                    ):
                        article = {
                            "title":   cached.get("title"),
                            "authors": cached.get("authors"),
                            "text":    cached.get("text"),
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
                answer, citations = send_message_cohere_rag(
                    prompt_news, conversation, collected_articles
                )
                panel_df.at[persona.Index, newsint_col]   = answer
                panel_df.at[persona.Index, citations_col] = str(citations)
                panel_df.at[persona.Index, urls_col]      = str(
                    sampled["DocumentIdentifier"].tolist()
                )
                conversation += [
                    {"role": "user",      "content": prompt_news},
                    {"role": "assistant", "content": answer},
                ]

        # --- Step 3: final answer ---
        second_prompt   = generate_question(question_id, initial=False)
        second_response = send_message(second_prompt, conversation=conversation)
        panel_df.at[persona.Index, vote_col] = second_response
        completed += 1

        if on_checkpoint and completed % CHECKPOINT_INTERVAL == 0:
            on_checkpoint(panel_df)

    # --- Attrition & replacement ---
    attrition_count = max(
        (1 if attrition_rate > 0 and len(panel_df) > 0 else 0),
        int(round(len(panel_df) * attrition_rate)),
    ) if attrition_rate > 0 else 0

    if attrition_count > 0:
        active_ids = set(panel_df.get("cell_id", pd.Series()))
        retired_idx = panel_df.sample(
            n=min(attrition_count, len(panel_df)), random_state=int(panel_date)
        ).index
        retired_rows = panel_df.loc[retired_idx].copy()
        retired_rows["retired_at"] = panel_date
        panel_df = panel_df.drop(index=retired_idx).reset_index(drop=True)

        if panels_dir and panel_name:
            replacements = _build_replacement_panelists(
                panel_name,
                country_code,
                panel_df.columns,
                active_ids.union(set(retired_rows.get("cell_id", pd.Series()))),
                replacement_count=len(retired_rows),
                panel_date=panel_date,
                panels_dir=panels_dir,
            )
            if not replacements.empty:
                panel_df = pd.concat([panel_df, replacements], ignore_index=True)
                if "cell_id" in panel_df.columns:
                    panel_df = panel_df.drop_duplicates(
                        subset=["cell_id"], keep="first"
                    ).reset_index(drop=True)

    return panel_df, news_df