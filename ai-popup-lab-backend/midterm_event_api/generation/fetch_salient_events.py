"""
Fetch and distill 2025-2026 National Context and Election-Week Salient Events from Wikipedia.

Runs once (or on-demand before the watch party) to produce a single, human-readable
briefing of macro facts (bridging the 2024 model knowledge cutoff).

Output: generation/data/salient_events.json
Note: State-specific events are handled separately by fetch_state_events.py.
"""

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load backend .env
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_PATH = DATA_DIR / "salient_events.json"
OVERRIDE_PATH = DATA_DIR / "salient_events_override.json"

USER_AGENT = "MechanicalPollster/1.0 (midterm-event-demo; contact@aipopuplab.org)"

WIKI_PAGES = [
    "2025_in_the_United_States",
    "2026_in_the_United_States",
    "2026_United_States_elections",
]

DISTILLATION_PROMPT = """You are an expert nonpartisan political researcher providing an election-night briefing for a synthetic voter chat demo on Tuesday, 3 November 2026.

The underlying language models chatting with visitors have a knowledge cutoff in late 2024.
Your job is to read the Wikipedia timelines of 2025 and 2026 and extract an authoritative, structured, objective briefing covering the major national realities and events leading up to tonight's midterms.

Produce a JSON object with this exact structure (do NOT include any state_highlights; state events are managed in a separate dedicated database):
{
  "national_context": {
    "administration_and_governance": [
      ... (4-6 major executive/legislative developments: Trump 47th President inaugurated Jan 2025, JD Vance VP, GOP control of Congress with Johnson/Thune, DOGE spending cuts, executive orders, tariff policies, immigration enforcement)
    ],
    "foreign_affairs_and_security": [
      ... (4-5 major conflicts/developments: Iran conflict & airstrikes, Middle East, Russia/Ukraine & New START expiration, Venezuela, cyber & election security)
    ],
    "economy_and_cost_of_living": [
      ... (4-5 major economic realities: inflation status, grocery/gas/housing costs, Federal Reserve interest rate policy, tariff impacts on consumer prices, national debt)
    ],
    "technology_energy_and_society": [
      ... (3-4 items: AI datacenter construction boom, power grid demands, semiconductor investments, regulatory/court rulings)
    ],
    "election_week_headlines": [
      ... (5-6 top national headlines and campaign dynamics leading into tonight, Tuesday, November 3, 2026)
    ]
  }
}

REQUIREMENTS:
- Factual, neutral, concrete tone. No editorial spin.
- Expand each national category thoroughly (around 22-26 total national bullet points).
- Each bullet point should be 20-35 words, specific, and information-dense.
- Return pure JSON only without markdown formatting.
"""


def fetch_wikipedia_text(page_title: str) -> str:
    url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext&titles={page_title}&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for pid in pages:
                return pages[pid].get("extract", "")
    except Exception as e:
        print(f"Warning: Failed to fetch {page_title}: {e}")
    return ""


def main():
    parser = argparse.ArgumentParser(description="Fetch and distill expanded 2025-2026 national events from Wikipedia.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch Wikipedia text only without calling LLM")
    args = parser.parse_args()

    print("Fetching Wikipedia articles for 2025, 2026, and 2026 US Elections...")
    wiki_corpus = []
    for page in WIKI_PAGES:
        text = fetch_wikipedia_text(page)
        print(f"  - {page}: {len(text)} characters")
        if text:
            wiki_corpus.append(f"=== {page} ===\n{text[:25000]}")

    full_text = "\n\n".join(wiki_corpus)

    if args.dry_run:
        print(f"Dry run complete. Fetched {len(full_text)} characters.")
        return

    # Check for manual override first
    if OVERRIDE_PATH.exists():
        print(f"Found manual override at {OVERRIDE_PATH}. Merging/using it.")

    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("AZURE_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    model = os.getenv("MIDTERM_MODEL") or os.getenv("AZURE_OPENAI_MODEL") or "gpt-oss-120b"

    if not api_key:
        raise SystemExit("Missing AZURE_OPENAI_API_KEY or OPENAI_API_KEY in .env")

    client_kwargs = {"api_key": api_key.strip(), "timeout": 90.0, "max_retries": 2}
    if base_url and base_url.strip():
        client_kwargs["base_url"] = base_url.strip()

    client = OpenAI(**client_kwargs)
    print(f"Calling {model} to distill expanded national salient events...")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": DISTILLATION_PROMPT},
            {"role": "user", "content": f"Wikipedia Extracts:\n\n{full_text}"},
        ],
        temperature=0.3,
        max_completion_tokens=3500,
    )

    raw_content = response.choices[0].message.content or ""
    raw_content = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()
    raw_content = re.sub(r"^```(?:json)?\s*", "", raw_content, flags=re.MULTILINE)
    raw_content = re.sub(r"\s*```$", "", raw_content, flags=re.MULTILINE).strip()

    m = re.search(r"(\{.*\})", raw_content, flags=re.DOTALL)
    if m:
        raw_content = m.group(1)

    try:
        distilled = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        print(f"JSON decode error: {exc}\nRaw content was:\n{raw_content[:400]}")
        raise

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(distilled, indent=2), encoding="utf-8")
    print(f"Successfully saved expanded national salient events to {OUTPUT_PATH}")
    categories = distilled.get("national_context", {})
    for cat, items in categories.items():
        print(f"  - {cat}: {len(items)} items")


if __name__ == "__main__":
    main()
