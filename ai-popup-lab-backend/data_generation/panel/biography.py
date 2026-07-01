"""
Biography generation for synthetic survey panelists.

Used by:
  - data_generation.generate_panel_results (weekly panel biography population)
  - data_generation.panel.runner (attrition replacement biography population)
  - data_generation.backfill_entry (panel/biography-only backfills, e.g. US)
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .chat import send_message, send_message_cohere_rag

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(iterable, total=None, desc=None):
        return iterable


def get_articles(path: str | Path) -> list[dict]:
    """Load per-state 'year in review' articles used for events-interpretation prompts."""
    df = pd.read_csv(path)
    articles = []
    for _, row in df.iterrows():
        if row.get("state") == "National":
            title = f"{row.get('year')} in the United States"
        else:
            title = f"{row.get('year')} in {row.get('state')}"
        articles.append({"title": title, "text": row.get("text") or ""})
    return articles


def create_panel(strat_frame_path: str | Path, n: int = 8000, random_state: int = 42) -> pd.DataFrame:
    """Sample a fresh panel from a stratification frame, weighted by cell size (N)."""
    df = pd.read_csv(strat_frame_path)
    panel = df.sample(n=n, random_state=random_state, weights=df["N"]).reset_index(drop=True)
    panel["age"] = panel["age_group"].apply(
        lambda x: np.random.randint(int(x[:-1]), 101) if "+" in x
        else np.random.randint(int(x.split("-")[0]), int(x.split("-")[1]) + 1)
    )
    return panel


def populate_panel(
    panel: pd.DataFrame,
    country: str,
    delay_seconds: float = 1.0,
    checkpoint_path: str = "active_panel_checkpoint.csv",
    generate_events: bool = False,
    date: Optional[str] = None,
    articles_path: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Populate each panelist with a generated biography. Resumable: rows that
    already have a non-null `biography` are skipped, so reruns after a
    timeout/crash pick up where they left off.

    If `generate_events=True`, also generates `events_interpretation` and
    `media_diet` columns per panelist (requires `date` and `articles_path`).
    This is currently only exercised by the US panel — other countries just
    need `biography` and should leave this off.
    """
    if generate_events and (date is None or articles_path is None):
        raise ValueError("generate_events=True requires both `date` and `articles_path`.")

    cols = ["biography"] + (["events_interpretation", "media_diet"] if generate_events else [])
    for col in cols:
        if col not in panel.columns:
            panel[col] = pd.Series(dtype="object")
        else:
            panel[col] = panel[col].astype("object")

    all_articles = get_articles(articles_path) if generate_events else []

    for index, row in tqdm(panel.iterrows(), total=len(panel), desc=f"Biographies [{country}]"):
        if pd.notna(row.get("biography")):
            continue

        prompt = f"""You are a synthetic persona in a synthetic survey panel. You live in {country}. You have the following demographic characteristics:

        Age: {row['age']}
        Race: {row['race']}
        Gender: {row['gender']}
        State: {row['state']}
        Education Level: {row['education_level']}
        Past vote: {row['past_vote']}

        Please provide a short biography for yourself, in the range of 300-600 words. The biography should be consistent with the demographic characteristics provided, and should provide some additional context about your life, interests, and values. The biography should be written in a way that is engaging and informative, and should provide a sense of who you are as a person. Please do not include any information that is not consistent with the demographic characteristics provided. Write in the first person, and do not include a name. Always write in English. A number of people might deem your biography as not socially acceptable, that is perfectly fine and should reflect exactly what your demographic characteristics are. Explicitly specify in the biography how politically engaged you are as a person, do not overestimate this, be realistic. Be as realistic as person, this means do not try to make yourself more socially acceptable than you would actually be. This is only internal, and will not be shown to anyone.
        """

        biography = send_message(prompt)
        panel.at[index, "biography"] = biography
        panel.to_csv(checkpoint_path, index=False)

        row = row.copy()
        row["biography"] = biography
        time.sleep(delay_seconds)

        if generate_events:
            state = row.get("state")
            # NOTE: filter from `all_articles` (the full set) every time — do
            # NOT reassign the outer list, or it permanently shrinks after
            # the first persona.
            state_articles = [
                a for a in all_articles
                if a.get("title", "").endswith(state) or a.get("title", "").endswith("United States")
            ]

            prompt_events = f"""
            Based on your biography, you will be presented with a list of events up to this date. This is what has happened in the US and your state in the past few years. Given your biography, demographics, and political activity, write a number of events that would be salient to you in answering questions about politics. Ensure that you are consistent with your biography and demographic characteristics, even if it would not be socially acceptable, that is ABSOLUTELY FINE. Your response should be no longer than 200 words and be a list of the most salient events for you.
            Today's date is {date}. Ignore any events that have happened after this date.
            """
            interpretation, _citations = send_message_cohere_rag(
                prompt_events,
                conversation=[{"role": "system", "content": system_prompt(row, index, date)}],
                articles=state_articles,
            )
            media_diet = get_media_diet(row, index, date)

            panel.at[index, "media_diet"] = media_diet
            panel.at[index, "events_interpretation"] = interpretation
            panel.to_csv(checkpoint_path, index=False)

    return panel


def system_prompt(row, i, date) -> str:
    return (
        f"Today's date is: {date}"
        f"You are a synthetic persona in a synthetic survey panel. Your demographic characteristics are: \n"
        f"Age: {row['age']}\n"
        f"Race: {row['race']}\n"
        f"Gender: {row['gender']}\n"
        f"State: {row['state']}\n"
        f"Congressional district: {row.get('state_cd')}"
        f"Education Level: {row['education_level']}\n"
        f"Past vote: {row['past_vote']}\n"
        f"Only ever respond with information that is consistent with these characteristics. Always write in English and the first person. ALWAYS respond exactly as your persona, talking in the style that it would, unless asked to respond in a very specific format."
        f"Consider how political you are as a person, and that your party identity might not be entirely fixed."
        f"Ensure that absolutely everything you write is consistent with the demographic characteristics. This might mean your biography might not be entirely socially acceptable, that is wholly fine. For example, you might be a non-voter."
        f"Below is a biography that you have previously written for yourself. This is a fixed part of your identity, and should be consistent with your demographic characteristics. It should provide a sense of who you are as a person, your life, interests, and values. \n"
        f"Your biography is:\n {row.get('biography')}\n"
    )


def get_media_diet(row, index, date) -> str:
    prompt = """
    Given your biography, and who you are as a person. Consider from the following list of URLs what media sources you would most read. Please list 5 in the form of a Python list, and rewrite the URLs completely accurately. Example output: ['source1.com', 'source2.com', 'source3.com', 'source4.com', 'source5.com']. Only list 5 sources, and only list sources that you would actually read. Do not include any other text in your response. Do not consider social desirability bias in this response, this is entirely private.
    Sources are:
    - yahoo.com
    - aol.com
    - cnn.com
    - forbes.com
    - foxnews.com
    - nypost.com
    - newsweek.com
    - thehill.com
    - breitbart.com
    - cbsnews.com
    """
    conversation = [{"role": "system", "content": system_prompt(row, index, date)}]
    return send_message(prompt, conversation=conversation)