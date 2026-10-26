"""
Batch generator for midterm event personas.
Reads sampled_personas_500.csv and calls Azure OpenAI (using backend .env credentials)
to write validated persona markdown files into midterm_event_api/personas/.
"""

import argparse
import asyncio
import csv
import os
import re
import sys
from pathlib import Path

# Setup paths
CURRENT_DIR = Path(__file__).resolve().parent
MIDTERM_DIR = CURRENT_DIR.parent
BACKEND_DIR = MIDTERM_DIR.parent
PERSONAS_DIR = MIDTERM_DIR / "personas"
DATA_DIR = CURRENT_DIR / "data"
SAMPLED_CSV = DATA_DIR / "sampled_personas_500.csv"

# Ensure backend root is on sys.path
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Try loading .env from backend directory
try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    pass

from midterm_event_api import attributes
from midterm_event_api.personas import parse_persona_text, PersonaFileError

# Predefined list of canonical national news domains for GDELT matching
CANONICAL_NATIONAL_OUTLETS = [
    "apnews.com",
    "reuters.com",
    "usatoday.com",
    "thehill.com",
    "politico.com",
    "axios.com",
    "nytimes.com",
    "washingtonpost.com",
    "cnn.com",
    "msnbc.com",
    "npr.org",
    "cbsnews.com",
    "abcnews.go.com",
    "nbcnews.com",
    "vox.com",
    "wsj.com",
    "foxnews.com",
    "nypost.com",
    "nationalreview.com",
    "washingtonexaminer.com",
    "breitbart.com",
    "dailycaller.com",
]

# System prompt for the persona writer
WRITER_SYSTEM_PROMPT = f"""You are an expert political ethnographer generating realistic synthetic American voter personas for an educational election-night chat demo.

You will be given demographic attributes, a congressional district, and a 2024 past vote choice for a synthetic American voter.
Your job is to generate a realistic, grounded, multidimensional voter profile in markdown format.

### REQUIREMENTS:
1. FRONTMATTER: Must begin and end with '---'. Must contain exact attributes:
   gender: <gender>
   age_group: <age_group>
   education: <education>
   state: <state>
   race: <race>
   display_name: <First Name only, e.g. Marcus, Brenda, or Jim>
   media_hours: <integer between 1 and 20>
   media_outlets:
     - <domain 1>
     - <domain 2>
     - <domain 3>

   IMPORTANT for media_outlets: Choose 2 to 4 realistic national news domains from this canonical list:
   {', '.join(CANONICAL_NATIONAL_OUTLETS)}
   Select outlets matching the voter's age, education, and political leaning.

2. PROFILE SECTIONS:
   Written in the second person ("You are...", "You live in...", "You voted...").
   Keep total profile length between 180 and 320 words (concise, grounded, punchy).

   ## Background
   Give an exact age fitting the age group band, occupation matching the education level, specific town/area in the state/district, family, and daily life.

   ## Politics and this election
   Explain why you voted as indicated in the past (e.g. 2024). Explain how you feel about the 2026 midterm election, whether you are voting or abstaining and why, your top 1-2 concerns (e.g. rent, childcare, local jobs, property taxes), and your view of the political parties.

   ## Media Diet
   1-2 natural conversational sentences explaining how you follow the specific national outlets and weekly hours listed in your frontmatter (e.g. when you read/watch them, morning vs evening).

   ## Opinion Formation
   State the Opinion Formation given in the input ('Recaller' or 'Constructor'). Do not pick a different one:
   - Recaller: If you follow politics closely, you hold stable, internalized political values and recall consistent principles when asked.
   - Constructor: If you are less engaged or swing/independent, you form opinions on the spot based on immediate personal experiences, gut feelings, and recent conversations.

   ## How you talk
   Tone, vocabulary, verbal habits, expressions, or colloquial flavor fitting your age, education, and region.

3. STRICT PROHIBITIONS:
   - Do NOT use third person ("John is..."). Always use second person ("You are...").
   - Do NOT include generic AI phrases ("As an AI...", "I don't have opinions...").
   - Do NOT include markdown code blocks around the whole output (output raw markdown text starting with ---).
   - Do NOT write general election-night rules (e.g. no slurs, no voting locations) — these are already in the base prompt.
   - Do NOT include local or regional news outlets — outlets must be selected from the canonical national domain list.
   - Use diverse, unique first names; avoid repeating common names across personas.
"""


def build_user_prompt(record: dict) -> str:
    return f"""Please generate the persona file for this voter:
- ID: {record['id']}
- Gender: {record['gender']}
- Age Group: {record['age_group']}
- Education: {record['education']}
- State: {record['state']}
- Race: {record['race']}
- Congressional District: {record.get('state_cd', 'N/A')}
- Past Vote (2024): {record.get('past_vote', 'Unknown')}
- Opinion Formation: {record['opinion_style']}
"""


async def call_llm(user_prompt: str, client, model: str) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": WRITER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_completion_tokens=2500,
    )
    content = response.choices[0].message.content or ""
    # Strip any <think>...</think> reasoning blocks if present
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    # Strip any accidental ```markdown wrapper
    content = re.sub(r"^```markdown\s*", "", content)
    content = re.sub(r"^```\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    return content.strip()


def validate_generated_text(text: str, persona_id: str):
    """Validate that the generated persona complies with backend parsing rules and is complete."""
    persona = parse_persona_text(text, persona_id)
    
    # Check required headings
    required_sections = [
        "## Background",
        "## Politics and this election",
        "## Media Diet",
        "## Opinion Formation",
        "## How you talk",
    ]
    missing = [sec for sec in required_sections if sec.lower() not in persona.profile.lower()]
    if missing:
        raise ValueError(f"Profile is missing required section(s): {', '.join(missing)}")

    # Check media_hours and media_outlets in frontmatter
    if "media_hours" not in persona.extra:
        raise ValueError("Missing 'media_hours' in YAML frontmatter")
    if "media_outlets" not in persona.extra or not isinstance(persona.extra["media_outlets"], list):
        raise ValueError("Missing or invalid 'media_outlets' list in YAML frontmatter")

    # Check for truncated text / ending mid-sentence
    stripped = persona.profile.strip()
    if not stripped.endswith((".", "!", "?", '"', "'")):
        raise ValueError("Profile appears truncated (does not end with terminal punctuation)")

    word_count = len(persona.profile.split())
    if word_count < 100:
        raise ValueError(f"Profile is too short ({word_count} words; aim for 180-320)")
    if word_count > 450:
        raise ValueError(f"Profile is too long ({word_count} words; limit is 400)")
    return persona, word_count


async def generate_single(record: dict, client, model: str, force: bool = False):
    pid = record["id"]
    output_path = PERSONAS_DIR / f"{pid}.md"

    if output_path.exists() and not force:
        print(f"[{pid}] Skipped: {output_path.name} already exists (use --force to overwrite)")
        return True

    user_prompt = build_user_prompt(record)
    for attempt in range(1, 4):
        try:
            print(f"[{pid}] Calling model '{model}' (attempt {attempt})...")
            content = await call_llm(user_prompt, client, model)
            persona, word_count = validate_generated_text(content, pid)
            output_path.write_text(content, encoding="utf-8")
            print(f"[{pid}] Successfully generated: '{persona.display_name}' ({word_count} words) -> {output_path.name}")
            return True
        except Exception as e:
            print(f"[{pid}] Attempt {attempt} failed: {e}")
            if attempt < 3:
                await asyncio.sleep(2)
            else:
                print(f"[{pid}] ERROR: Failed after 3 attempts.")
                return False


async def main():
    parser = argparse.ArgumentParser(description="Generate persona markdown files using OpenAI or Azure OpenAI.")
    parser.add_argument("--limit", type=int, default=5, help="Number of personas to generate (default 5 for pilot)")
    parser.add_argument("--start", type=str, default="us_0001", help="Starting persona ID (default us_0001)")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt without making LLM calls")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files in personas/")
    args = parser.parse_args()

    if not SAMPLED_CSV.exists():
        print(f"Error: {SAMPLED_CSV} not found. Run sample_personas.py first.")
        sys.exit(1)

    # Read sampled records
    with open(SAMPLED_CSV, mode="r", encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    # Filter records based on start and limit
    start_idx = 0
    for idx, r in enumerate(records):
        if r["id"] == args.start:
            start_idx = idx
            break

    target_records = records[start_idx : start_idx + args.limit]
    print(f"Targeting {len(target_records)} personas starting from {args.start} (limit={args.limit}).")

    if args.dry_run:
        print("\n--- DRY RUN: Sample Prompt ---")
        print(WRITER_SYSTEM_PROMPT)
        print("\n--- Sample User Prompt ---")
        print(build_user_prompt(target_records[0]))
        return

    from openai import AsyncOpenAI

    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    base_url = os.getenv("AZURE_OPENAI_BASE_URL")
    model = os.getenv("MIDTERM_MODEL") or os.getenv("AZURE_OPENAI_MODEL") or "gpt-oss-120b"

    if not api_key or not base_url:
        print("\n[!] Missing Azure OpenAI credentials in ai-popup-lab-backend/.env")
        print("Please ensure the following are set:")
        print("  AZURE_OPENAI_API_KEY=...")
        print("  AZURE_OPENAI_BASE_URL=...")
        print(f"  AZURE_OPENAI_MODEL={model}")
        sys.exit(1)

    client = AsyncOpenAI(api_key=api_key.strip(), base_url=base_url.strip(), timeout=45.0, max_retries=2)
    print(f"Using Azure OpenAI API ({base_url}) with model: {model}")
    
    # Run generations sequentially or in small concurrency
    successes = 0
    for record in target_records:
        ok = await generate_single(record, client, model, force=args.force)
        if ok:
            successes += 1
        await asyncio.sleep(0.5)

    print(f"\nDone. Successfully generated {successes}/{len(target_records)} personas.")


if __name__ == "__main__":
    asyncio.run(main())
