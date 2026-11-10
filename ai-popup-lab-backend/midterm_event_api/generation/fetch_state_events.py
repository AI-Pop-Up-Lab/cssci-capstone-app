"""
Fetch and distill state-specific developments and ballot measures for all 50 US states + DC.

Sources:
1. "2026 in <State>" (e.g. 2026 in Alaska, 2026 in California) for real local events,
   disasters, state government actions, and daily lived realities.
2. "2026 <State> elections" (e.g. 2026 Alaska elections) for state ballot measures,
   referendums, and Senate/House/Governor race dynamics.

Output: generation/data/state_events.json
At runtime, chat.py loads this file and injects ONLY the persona's specific state.
"""

import argparse
import json
import os
import re
import time
import urllib.request
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load backend .env
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from midterm_event_api import attributes

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_PATH = DATA_DIR / "state_events.json"

USER_AGENT = "MechanicalPollsterDemo/1.0 (mjnbalancier@gmail.com; educational watch party)"


def fetch_wikipedia_page(title: str) -> str:
    url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext&titles={title}&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            pages = d.get("query", {}).get("pages", {})
            for pid in pages:
                if pid != "-1":
                    return pages[pid].get("extract", "")
    except Exception:
        pass
    return ""


def clean_state_events_section(text: str) -> str:
    if not text:
        return ""
    # Skip preamble/incumbents list if "== Events ==" exists
    m = re.search(r"==\s*Events\s*==\s*\n(.*)", text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text.strip()


def get_state_text(abbr: str, full_name: str) -> str:
    safe_name = full_name.replace(" ", "_")

    # 1. State Year in Review (events, disasters, policy)
    year_pages = [f"2026_in_{safe_name}"]
    if abbr == "DC":
        year_pages = ["2026_in_Washington,_D.C.", "2026_in_the_District_of_Columbia"]
    elif abbr == "GA":
        year_pages = ["2026_in_Georgia_(U.S._state)", "2026_in_Georgia"]
    elif abbr == "WA":
        year_pages = ["2026_in_Washington_(state)", "2026_in_Washington"]

    year_text = ""
    chosen_year_page = year_pages[0]
    for yp in year_pages:
        t = fetch_wikipedia_page(yp)
        if t:
            year_text = t
            chosen_year_page = yp
            break
    year_events = clean_state_events_section(year_text)

    # 2. State Elections page (ballots, referendums, campaigns)
    elec_pages = [f"2026_{safe_name}_elections"]
    if abbr == "DC":
        elec_pages = ["2026_District_of_Columbia_elections", "2026_Washington,_D.C._elections"]
    elif abbr == "GA":
        elec_pages = ["2026_Georgia_gubernatorial_election", "2026_United_States_Senate_election_in_Georgia"]
    elif abbr == "WA":
        elec_pages = ["2026_Washington_gubernatorial_election", "2026_Washington_elections"]

    elec_text = ""
    chosen_elec_page = elec_pages[0]
    for ep in elec_pages:
        t = fetch_wikipedia_page(ep)
        if t:
            elec_text = t
            chosen_elec_page = ep
            break

    combined = []
    if year_events:
        combined.append(f"=== {chosen_year_page} (Local Events) ===\n{year_events[:2500]}")
    elif year_text:
        combined.append(f"=== {chosen_year_page} ===\n{year_text[:2500]}")

    if elec_text:
        combined.append(f"=== {chosen_elec_page} (Ballots & Elections) ===\n{elec_text[:2500]}")

    return "\n\n".join(combined).strip()


def parse_json_from_response(raw: str) -> dict:
    # Strip thinking blocks
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    # Strip markdown formatting
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    # Find outermost curly braces
    m = re.search(r"(\{.*\})", cleaned, flags=re.DOTALL)
    if m:
        return json.loads(m.group(1))
    return json.loads(cleaned)


def call_llm_for_states(client, model: str, batch: list[str], names: dict) -> dict:
    batch_corpus = []
    for s in batch:
        text = get_state_text(s, names[s])
        print(f"  - {s} ({names[s]}): {len(text)} chars of extracts")
        batch_corpus.append(f"[[STATE: {s} - {names[s]}]]\n{text}")
        time.sleep(0.1)

    full_batch_text = "\n\n".join(batch_corpus)

    prompt = (
        f"You are an expert political researcher preparing the comprehensive state-by-state reference for the November 3, 2026 US midterms.\n\n"
        f"Based on the provided extracts from '2026 in <State>' and '2026 <State> elections' for these states: {', '.join(batch)}\n"
        f"For EACH of these states, produce 4 to 5 concise, realistic bullet points (15-25 words each) capturing:\n"
        f"- Exactly 2 notable state events, natural disasters/weather, infrastructure, local economy, or government actions in 2026.\n"
        f"- Exactly 2 to 3 key ballot propositions, referendums, or major Senate, House, or gubernatorial race dynamics on tonight's ballot.\n\n"
        f"Return a pure JSON dictionary mapping 2-letter state codes to lists of 4-5 strings: {{\"STATE\": [\"point 1\", \"point 2\", \"point 3\", \"point 4\", \"point 5\"]}}\n"
        f"Output pure JSON only without any markdown formatting."
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Wikipedia State Extracts:\n\n{full_batch_text}"},
        ],
        temperature=0.3,
        max_completion_tokens=2500,
    )

    raw = response.choices[0].message.content or ""
    return parse_json_from_response(raw)


def main():
    parser = argparse.ArgumentParser(description="Generate 50-state events reference from '2026 in <State>' and election pages.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch Wikipedia text without model call")
    parser.add_argument("--batch-size", type=int, default=2, help="States per LLM prompt (default 2)")
    args = parser.parse_args()

    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("AZURE_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    model = os.getenv("MIDTERM_MODEL") or os.getenv("AZURE_OPENAI_MODEL") or "gpt-oss-120b"

    if not api_key:
        raise SystemExit("Missing API key in .env")

    client_kwargs = {"api_key": api_key.strip(), "timeout": 90.0, "max_retries": 2}
    if base_url and base_url.strip():
        client_kwargs["base_url"] = base_url.strip()

    client = OpenAI(**client_kwargs)

    states = attributes.ALLOWED_VALUES["state"]
    names = attributes.STATE_NAMES

    # Load existing state events if partially populated
    all_data = {}
    if OUTPUT_PATH.exists():
        try:
            all_data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            all_data = {}

    batch_size = args.batch_size
    state_batches = [states[i : i + batch_size] for i in range(0, len(states), batch_size)]

    for b_idx, batch in enumerate(state_batches, 1):
        # Skip if all states in this batch are already populated with >= 4 points
        if all(s in all_data and len(all_data[s]) >= 4 for s in batch):
            print(f"Batch {b_idx}/{len(state_batches)} ({batch[0]}..{batch[-1]}) already completed with 4+ points, skipping.")
            continue

        print(f"\nProcessing Batch {b_idx}/{len(state_batches)} ({len(batch)} states: {batch[0]}..{batch[-1]})...")
        if args.dry_run:
            for s in batch:
                text = get_state_text(s, names[s])
                print(f"  - {s} ({names[s]}): {len(text)} chars")
            continue

        try:
            batch_result = call_llm_for_states(client, model, batch, names)
            all_data.update(batch_result)
            print(f"  Successfully extracted {len(batch_result)} states from batch {b_idx}.")
            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT_PATH.write_text(json.dumps(all_data, indent=2), encoding="utf-8")
        except Exception as exc:
            print(f"  Batch {b_idx} failed: {exc}. Retrying state-by-state...")
            for single_state in batch:
                if single_state in all_data and len(all_data[single_state]) >= 4:
                    continue
                try:
                    res = call_llm_for_states(client, model, [single_state], names)
                    all_data.update(res)
                    print(f"    Recovered state {single_state}")
                    OUTPUT_PATH.write_text(json.dumps(all_data, indent=2), encoding="utf-8")
                except Exception as inner_exc:
                    print(f"    Failed single state {single_state}: {inner_exc}")

    if not args.dry_run:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(all_data, indent=2), encoding="utf-8")
        print(f"\nFinished. Successfully saved {len(all_data)} states to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
