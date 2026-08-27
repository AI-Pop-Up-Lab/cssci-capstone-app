"""
Biography generation for synthetic survey panelists.

Called after `panel.attrition.apply_attrition_and_replacement` — `populate_panel`
only fills in rows with a null `biography`, so it naturally only generates
biographies for this cycle's new joiners. Existing panellists keep the
biography they were originally given; it's a fixed identity, never
regenerated.

Every panellist also gets a `media_diet` here — a fixed list of news sources
they'd plausibly read, generated unconditionally (not gated behind
`generate_events`) since `panel.runner.run_survey` depends on it for every
panellist, every week.

`generate_events=True` additionally produces a one-off `events_interpretation`
column at biography time. This is a legacy path from before the recurring
per-week `{date}_newsint` columns (produced by `run_survey`) existed, which
supersede it for the normal weekly/backfill pipeline. It's kept only for the
biography-only backfill mode.

Checkpointing is Azure-only: pass `on_checkpoint` (a callable that uploads the
in-progress panel to blob storage) to get resumability. There is no local-disk
checkpoint file — a run that crashes mid-way resumes from whatever was last
pushed via `on_checkpoint`.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from .chat import send_message, send_message_cohere_rag
from .retry_utils import RetryExhausted

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(iterable, total=None, desc=None):
        return iterable

logger = logging.getLogger(__name__)

MEDIA_DIET_SOURCES = [
    "yahoo.com", "aol.com", "cnn.com", "forbes.com", "foxnews.com",
    "nypost.com", "newsweek.com", "thehill.com", "breitbart.com", "cbsnews.com",
]


def get_articles(path: str | Path) -> list[dict]:
    """Load per-state 'year in review' articles used for the legacy events-interpretation prompt."""
    df = pd.read_csv(path)
    articles = []
    for _, row in df.iterrows():
        if row.get("state") == "National":
            title = f"{row.get('year')} in the United States"
        else:
            title = f"{row.get('year')} in {row.get('state')}"
        articles.append({"title": title, "text": row.get("text") or ""})
    return articles


def _biography_prompt(row, country: str) -> str:
    return f"""You are a synthetic persona in a synthetic survey panel. You live in {country}. You have the following demographic characteristics:

        Age: {row['age']}
        Race: {row['race']}
        Gender: {row['gender']}
        State: {row['state']}
        Education Level: {row['education_level']}
        Past vote: {row['past_vote']}

        Please provide a short biography for yourself, in the range of 300-600 words. The biography should be consistent with the demographic characteristics provided, and should provide some additional context about your life, interests, and values. The biography should be written in a way that is engaging and informative, and should provide a sense of who you are as a person. Please do not include any information that is not consistent with the demographic characteristics provided. Write in the first person, and do not include a name. Always write in English. A number of people might deem your biography as not socially acceptable, that is perfectly fine and should reflect exactly what your demographic characteristics are. Explicitly specify in the biography how politically engaged you are as a person, do not overestimate this, be realistic. Be as realistic as person, this means do not try to make yourself more socially acceptable than you would actually be. This is only internal, and will not be shown to anyone.
        """


def system_prompt(row, date) -> str:
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


def get_media_diet(row, date) -> str:
    sources_block = "\n".join(f"    - {s}" for s in MEDIA_DIET_SOURCES)
    prompt = f"""
    Given your biography, and who you are as a person. Consider from the following list of URLs what media sources you would most read. Please list 5 in the form of a Python list, and rewrite the URLs completely accurately. Example output: ['source1.com', 'source2.com', 'source3.com', 'source4.com', 'source5.com']. Only list 5 sources, and only list sources that you would actually read. Do not include any other text in your response. Do not consider social desirability bias in this response, this is entirely private.
    Sources are:
{sources_block}
    """
    conversation = [{"role": "system", "content": system_prompt(row, date)}]
    return send_message(prompt, conversation=conversation)


def populate_panel(
    panel: pd.DataFrame,
    country: str,
    delay_seconds: float = 1.0,
    generate_events: bool = False,
    date: Optional[str] = None,
    articles_path: Optional[str | Path] = None,
    on_checkpoint: Optional[Callable[[pd.DataFrame], None]] = None,
    checkpoint_interval: int = 50,
) -> pd.DataFrame:
    """
    Populate every panellist with a null `biography`: a biography, a
    media_diet, and (if `generate_events`) a legacy one-off events
    interpretation. Resumable — rows that already have a non-null
    `biography` are skipped, so re-running after a crash/timeout continues
    from wherever the last checkpoint left off.

    Network calls (`send_message`, `send_message_cohere_rag`) already retry
    internally up to 5 times with backoff (see `panel.chat`). If a given row
    still fails after those retries are exhausted, it's logged and skipped
    rather than aborting the whole run — it simply still has a null
    biography afterwards and gets picked up on the next run.
    """
    if date is None:
        raise ValueError(
            "populate_panel requires `date` — it's used for media_diet generation "
            "(always) and events_interpretation (when generate_events=True)."
        )
    if generate_events and articles_path is None:
        raise ValueError("generate_events=True requires `articles_path`.")

    cols = ["biography", "media_diet"] + (["events_interpretation"] if generate_events else [])
    for col in cols:
        if col not in panel.columns:
            panel[col] = pd.Series(dtype="object")
        else:
            panel[col] = panel[col].astype("object")

    all_articles = get_articles(articles_path) if generate_events else []

    pending = panel[panel["biography"].isna()]
    if pending.empty:
        return panel

    completed = 0

    for index, row in tqdm(pending.iterrows(), total=len(pending), desc=f"Biographies [{country}]"):
        try:
            biography = send_message(_biography_prompt(row, country))

            row_with_bio = row.copy()
            row_with_bio["biography"] = biography
            time.sleep(delay_seconds)

            media_diet = get_media_diet(row_with_bio, date)

            interpretation = None
            if generate_events:
                state = row_with_bio.get("state")
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
                    conversation=[{"role": "system", "content": system_prompt(row_with_bio, date)}],
                    articles=state_articles,
                )

            # Commit every field for this row together, only after all of
            # them have succeeded. Writing `biography` early (before
            # media_diet/events_interpretation are known-good) would let a
            # later failure leave the row half-done but permanently marked
            # "complete" by the biography.isna() resume check — it would
            # never be retried.
            panel.at[index, "biography"] = biography
            panel.at[index, "media_diet"] = media_diet
            if generate_events:
                panel.at[index, "events_interpretation"] = interpretation

        except RetryExhausted as exc:
            logger.error("Biography generation failed for row %s after retries — skipping: %s", index, exc)
            continue
        except Exception:
            logger.exception("Unexpected error generating biography for row %s — skipping.", index)
            continue

        completed += 1
        if on_checkpoint and completed % checkpoint_interval == 0:
            on_checkpoint(panel)

    if on_checkpoint and completed % checkpoint_interval != 0:
        # Flush the final partial batch so it isn't lost.
        on_checkpoint(panel)

    return panel
