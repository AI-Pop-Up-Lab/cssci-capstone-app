"""
Audit and rebuild state_events.json using ground-truth Wikipedia election data.

Sources:
- wiki_senate_2026.txt (2026 U.S. Senate elections Wikipedia master text)
- wiki_gov_2026.txt (2026 U.S. Gubernatorial elections Wikipedia master text)
- wiki_fl_senate.txt / wiki_oh_senate.txt (special elections)

Rules:
1. Factual grounding: NEVER invent candidate names.
2. If a state has NO Senate election in 2026, state clearly that there is no Senate election this year.
3. If a state has NO Governor election in 2026, do not fabricate one.
4. Output 3-4 bullet points per state.
"""

import asyncio
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from midterm_event_api import attributes
from midterm_event_api.config import get_settings

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_PATH = DATA_DIR / "state_events.json"

SENATE_PATH = DATA_DIR / "wiki_senate_2026.txt"
GOV_PATH = DATA_DIR / "wiki_gov_2026.txt"


def extract_section(text: str, heading: str) -> str:
    pattern = rf"==\s*{re.escape(heading)}\s*==\s*\n(.*?)(?=\n==\s*|\Z)"
    m = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


async def process_state(
    client: AsyncOpenAI, model: str, abbr: str, full_name: str, senate_full: str, gov_full: str
) -> list[str]:
    # Check regular Senate section
    senate_sec = extract_section(senate_full, full_name)

    # Handle special cases for Florida and Ohio
    if not senate_sec:
        if abbr == "FL":
            senate_sec = (
                "Special U.S. Senate election to fill the remaining two years of Marco Rubio's term "
                "following his appointment as Secretary of State."
            )
        elif abbr == "OH":
            senate_sec = (
                "Special U.S. Senate election to fill the remaining two years of JD Vance's term "
                "following his election as Vice President."
            )

    gov_sec = extract_section(gov_full, full_name)

    prompt = f"""You are a nonpartisan factual research assistant for the 2026 US midterm elections.
State: {full_name} ({abbr})

[Senate Election Ground Truth from Wikipedia]:
{senate_sec if senate_sec else f"No U.S. Senate election in {full_name} in 2026."}

[Gubernatorial Election Ground Truth from Wikipedia]:
{gov_sec if gov_sec else f"No gubernatorial election in {full_name} in 2026."}

Task: Write 3-4 factual, concise bullet points for {full_name}'s 2026 midterm election context.
Rules:
1. NEVER invent candidate names. Only use candidates explicitly named in the extracts above.
2. If there is NO Senate election in 2026, state clearly that {full_name} has no regular U.S. Senate election in 2026.
3. If there is a gubernatorial election, accurately reflect the candidates and whether the incumbent is term-limited. If there is NO gubernatorial election, do not fabricate one.
4. Mention U.S. House elections (all seats contested) and notable state issues or ballot debates.
5. Return ONLY a valid JSON array of strings (e.g. ["point 1", "point 2", "point 3"]). No code fences, no extra text.
"""

    for attempt in range(3):
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=1500,
                temperature=0.1,
            )
            raw = (resp.choices[0].message.content or "").strip()
            # Clean possible markdown fences
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
            data = json.loads(raw)
            if isinstance(data, list) and len(data) >= 2:
                return data
        except Exception as e:
            if attempt == 2:
                print(f"Error on {abbr}: {e}")
            await asyncio.sleep(1.0)

    # Fallback if LLM fails
    fallback = []
    if senate_sec:
        fallback.append(f"U.S. Senate election: {senate_sec.splitlines()[0]}")
    else:
        fallback.append(f"{full_name} has no regular U.S. Senate election in 2026.")
    if gov_sec:
        fallback.append(f"Gubernatorial election: {gov_sec.splitlines()[0]}")
    fallback.append(f"All U.S. House seats in {full_name} are contested in the 2026 midterms.")
    return fallback


async def main():
    sys.stdout.reconfigure(encoding="utf-8")
    settings = get_settings()
    client = AsyncOpenAI(
        api_key=settings.azure_api_key,
        base_url=settings.azure_base_url,
        timeout=settings.llm_timeout_seconds,
    )

    senate_full = SENATE_PATH.read_text(encoding="utf-8")
    gov_full = GOV_PATH.read_text(encoding="utf-8")

    # Load existing state_events if any
    results = {}
    if OUTPUT_PATH.exists():
        try:
            results = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            results = {}

    all_states = dict(attributes.STATE_NAMES)
    all_states["DC"] = "District of Columbia"

    print(f"Rebuilding {len(all_states)} states with grounded Wikipedia data...")

    # Process in batches of 5 concurrent calls
    sem = asyncio.Semaphore(5)

    async def worker(abbr, name):
        async with sem:
            print(f"Processing {abbr} ({name})...")
            points = await process_state(client, settings.model, abbr, name, senate_full, gov_full)
            results[abbr] = points
            print(f"  ✓ {abbr} done ({len(points)} points)")

    tasks = [worker(abbr, name) for abbr, name in all_states.items()]
    await asyncio.gather(*tasks)

    OUTPUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSuccessfully wrote all {len(results)} states to {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
