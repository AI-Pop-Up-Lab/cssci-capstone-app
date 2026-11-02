"""
Step 1 of the news feed: download the last 7 days of GDELT articles from the persona outlets.

Uses the weekly pipeline's own download_weekly_news (same 7-day window as the paper).
Run from ai-popup-lab-backend:

    python -m midterm_event_api.generation.fetch_news                    # week up to today
    python -m midterm_event_api.generation.fetch_news --end 2026-11-02   # week up to a given day

Output: generation/data/news_week.csv (article urls, outlets and tone, no text yet).
Takes about 8 minutes. Then run digest_news.py.
"""

import argparse
from datetime import date, timedelta
from pathlib import Path

from data_generation.panel.news import MASTERLIST_URLS, download_weekly_news
from midterm_event_api.generation.generate_personas import CANONICAL_NATIONAL_OUTLETS

DATA_DIR = Path(__file__).resolve().parent / "data"
NEWS_PATH = DATA_DIR / "news_week.csv"


def main():
    parser = argparse.ArgumentParser(description="Download the week's news for the persona outlets.")
    parser.add_argument("--end", default=date.today().isoformat(), help="last day of the week, yyyy-mm-dd")
    args = parser.parse_args()

    end = date.fromisoformat(args.end)
    # english list only, the outlets are never in the translation list
    news = download_weekly_news(
        end - timedelta(days=7),
        end,
        domain=CANONICAL_NATIONAL_OUTLETS,
        save_csv=False,
        masterlist_urls=[MASTERLIST_URLS[0]],
    )
    if news is None:
        raise SystemExit("No articles found for the outlets in that week.")

    news.to_csv(NEWS_PATH, index=False)
    print(f"Saved {len(news)} articles to {NEWS_PATH}")


if __name__ == "__main__":
    main()
