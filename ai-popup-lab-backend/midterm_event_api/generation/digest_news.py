"""
Step 2 of the news feed: turn the week's news into a short digest per persona.

Follows the paper's pipeline: each persona reads articles from their own media_outlets,
sampled weighted by tone_activity and scraped with fetch_article. The number of articles
uses the paper's formula (minutes reading / 20 minutes per article, max 30), with the
persona's media_hours instead of a random number. The model then writes, as the persona,
the few points that stuck with them. No coin flip: every persona reads (see base_system.md).

Run from ai-popup-lab-backend after fetch_news.py (needs the .env for model calls):

    python -m midterm_event_api.generation.digest_news                     # all personas
    python -m midterm_event_api.generation.digest_news --persona us_0001   # one or more personas
    python -m midterm_event_api.generation.digest_news --dry-run           # sample and scrape only

Output: generation/data/news_digests.json ({persona_id: [points]}).
On election day set MIDTERM_EVENTS_PATH to that file so the chat puts each persona's points
into {{RECENT_EVENTS}}.
"""

import argparse
import hashlib
import json
import os
import re

import pandas as pd
from openai import OpenAI

from data_generation.panel.news import fetch_article
from midterm_event_api.config import DEFAULT_PERSONAS_DIR
from midterm_event_api.generation.fetch_news import DATA_DIR, NEWS_PATH
from midterm_event_api.personas import load_personas
from midterm_event_api.prompts import persona_facts

DIGEST_PATH = DATA_DIR / "news_digests.json"
TEXT_CACHE_PATH = DATA_DIR / "news_text.json"  # scraped articles, so each is fetched once
MAX_ARTICLES = 30  # the paper's maximum (120 minutes a day, 5 days, 20 minutes per article)
ARTICLE_CHARS = 1500  # same snippet length the pipeline gives the model per article

DIGEST_PROMPT = (
    "You will now be presented with a number of articles that you have read this week. "
    "Embodying your persona entirely, note the few things from them that actually stuck with you, "
    "the way you would remember them, not the way the article put them. Only include what someone "
    "with your background and interests would notice and remember. It is fine if most of the "
    "articles meant nothing to you. Every point must come from one of the articles below. Don't add "
    "anything that isn't in them, including concerns from your own life.\n"
    "Write 3 to 5 points in your own words, about 150 words in total, one per line starting with '- '. "
    "Write nothing else.\n\nArticles:\n\n"
)


def persona_seed(persona_id: str) -> int:
    # same idea as the paper's per-respondent seed, so reruns pick the same articles
    return int.from_bytes(hashlib.sha256(persona_id.encode("utf-8")).digest(), "big") % (2 ** 32)


def sample_articles(persona, news: pd.DataFrame) -> pd.DataFrame:
    outlets = [str(outlet).lower() for outlet in persona.extra.get("media_outlets") or []]
    hours = int(persona.extra.get("media_hours") or 0)
    # paper's formula: minutes reading / 20 minutes per article
    n = min(MAX_ARTICLES, hours * 60 // 20)

    readable = news[news["SourceCommonName"].isin(outlets)]
    if n == 0 or readable.empty:
        return readable.iloc[0:0]

    weights = "tone_activity" if readable["tone_activity"].sum() > 0 else None
    sampled = readable.sample(n=n, replace=len(readable) < n, weights=weights, random_state=persona_seed(persona.id))
    return sampled.drop_duplicates("DocumentIdentifier")


def write_digest(client, model: str, persona, articles: list) -> list:
    article_text = "\n\n".join(f"{a['title']}\n{a['text'][:ARTICLE_CHARS]}" for a in articles)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": f"You are this person:\n{persona_facts(persona)}\n\n{persona.profile}"},
            {"role": "user", "content": DIGEST_PROMPT + article_text},
        ],
        max_completion_tokens=2500,
    )
    reply = response.choices[0].message.content or ""
    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL)
    return [line[2:].strip() for line in reply.splitlines() if line.startswith("- ")]


def main():
    parser = argparse.ArgumentParser(description="Write a news digest for each persona.")
    parser.add_argument("--persona", nargs="*", help="persona ids to do (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="sample and scrape only, no model calls")
    args = parser.parse_args()

    news = pd.read_csv(NEWS_PATH)
    news["SourceCommonName"] = news["SourceCommonName"].fillna("").str.lower()
    news["tone_activity"] = pd.to_numeric(news["tone_activity"], errors="coerce").fillna(0)

    personas = load_personas(DEFAULT_PERSONAS_DIR).personas
    ids = args.persona or sorted(personas)

    texts = json.loads(TEXT_CACHE_PATH.read_text()) if TEXT_CACHE_PATH.exists() else {}
    digests = json.loads(DIGEST_PATH.read_text()) if DIGEST_PATH.exists() else {}

    client, model = None, None
    if not args.dry_run:
        client = OpenAI(api_key=os.getenv("AZURE_OPENAI_API_KEY"), base_url=os.getenv("AZURE_OPENAI_BASE_URL"))
        model = os.getenv("MIDTERM_MODEL") or os.getenv("AZURE_OPENAI_MODEL")

    for persona_id in ids:
        persona = personas[persona_id]
        sampled = sample_articles(persona, news)

        articles = []
        for url in sampled["DocumentIdentifier"]:
            if url not in texts:
                texts[url] = fetch_article(url)
            # skip articles that didn't scrape (paywall, bot block, removed page)
            if texts[url]["text"] and texts[url]["text"].strip():
                articles.append(texts[url])
        TEXT_CACHE_PATH.write_text(json.dumps(texts))

        print(f"\n{persona_id}: {persona.extra.get('media_hours')} h/week, outlets {persona.extra.get('media_outlets')}, "
              f"{len(sampled)} sampled, {len(articles)} with text")
        if args.dry_run or not articles:
            for article in articles:
                print(f"  - {(article['title'] or '')[:90]}")
            continue

        digests[persona_id] = write_digest(client, model, persona, articles)
        DIGEST_PATH.write_text(json.dumps(digests, indent=1))
        for point in digests[persona_id]:
            print(f"  * {point}")


if __name__ == "__main__":
    main()
