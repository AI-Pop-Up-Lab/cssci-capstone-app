"""
Sample 1000 personas (20 per US state) from us_strat_frame.csv with uniform state coverage
and balanced, diverse demographic distributions.
"""

import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FRAME_PATH = DATA_DIR / "us_strat_frame.csv"
OUTPUT_PATH = DATA_DIR / "sampled_personas_1000.csv"

# Target attributes and allowed values
ATTRIBUTES = ("gender", "age_group", "education", "state", "race")
ALLOWED_GENDERS = ["Female", "Male"]
ALLOWED_AGE_GROUPS = [
    "18-22", "23-27", "28-32", "33-37", "38-42", "43-47",
    "48-52", "53-57", "58-62", "63-67", "68-72", "73-77", "78-82", "83+"
]
ALLOWED_EDUCATIONS = ["No HS", "HS grad", "Some college", "2-year", "4-year", "Post-grad"]
ALLOWED_RACES = ["Asian", "Black", "Hispanic", "Native American", "Other/Multi", "White"]

# recall vs construction: chance of being a recaller rises with education
# (education is the strongest predictor of political knowledge, delli carpini & keeter 1996)
# placeholder values, set these from the literature
RECALL_SHARE = {"No HS": 0.25, "HS grad": 0.30, "Some college": 0.35, "2-year": 0.35, "4-year": 0.45, "Post-grad": 0.50}

# personas per gender per state (10 + 10 = 20 per state, 1000 total)
PER_GENDER = 10


# weekly news hours: older and more educated people follow the news more (pew research)
# placeholder ranges, set these from the literature
def media_hours_range(age_group: str, education: str) -> tuple:
    age = int(age_group[:2])  # "43-47" -> 43, "83+" -> 83
    if age < 28:
        low, high = 1, 4
    elif age < 43:
        low, high = 2, 6
    elif age < 63:
        low, high = 3, 8
    else:
        low, high = 4, 12
    if education in ("4-year", "Post-grad"):
        high += 1
    if education == "No HS":
        high -= 1
    return low, high

# Map education column if needed
def clean_education(val: str) -> str:
    val = val.strip()
    if val in ALLOWED_EDUCATIONS:
        return val
    mapping = {
        "No High School": "No HS",
        "High School": "HS grad",
        "Some College": "Some college",
        "2-Year College": "2-year",
        "4-Year College": "4-year",
        "Post-Graduate": "Post-grad",
    }
    return mapping.get(val, val)


def sample_past_vote(votes_and_probs, rng: random.Random) -> str:
    """Sample past vote based on prob_raked."""
    votes = [item[0] for item in votes_and_probs]
    weights = [item[1] for item in votes_and_probs]
    total = sum(weights)
    if total <= 0:
        return "Did not vote"
    normalized_weights = [w / total for w in weights]
    return rng.choices(votes, weights=normalized_weights, k=1)[0]


def main():
    rng = random.Random(20261103)  # deterministic seed (election day 2026)
    style_rng = random.Random(1)  # separate seed so opinion style doesn't change which cells are sampled
    media_rng = random.Random(2)  # separate seed so media hours don't change which cells are sampled

    print(f"Reading frame from {FRAME_PATH}...")
    
    # Group rows by cell_id
    # cell_info[cell_id] = {
    #   'state': state_abbrv,
    #   'state_cd': state_cd,
    #   'gender': gender,
    #   'age_group': age_group,
    #   'race': race,
    #   'education': education,
    #   'weight': float(N),
    #   'votes': [(past_vote, prob_raked), ...]
    # }
    cells = {}
    state_cells = defaultdict(list)

    with open(FRAME_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row["cell_id"]
            if cid not in cells:
                weight = float(row.get("N", 1.0))
                cells[cid] = {
                    "cell_id": cid,
                    "state": row["state_abbrv"].strip(),
                    "state_cd": row.get("state_cd", "").strip(),
                    "gender": row["gender"].strip(),
                    "age_group": row["age_group"].strip(),
                    "race": row["race"].strip(),
                    "education": clean_education(row.get("education_level", "")),
                    "weight": weight,
                    "votes": []
                }
                state_cells[cells[cid]["state"]].append(cid)
            
            prob_raked = float(row.get("prob_raked", 0.0) or 0.0)
            cells[cid]["votes"].append((row["past_vote"].strip(), prob_raked))

    print(f"Loaded {len(cells)} unique demographic cells across {len(state_cells)} states.")

    # target: 50 states * 20 personas each = 1000 total personas
    sampled_records = []
    persona_counter = 1

    for state in sorted(state_cells.keys()):
        cids_in_state = state_cells[state]
        
        # split by gender: 10 female, 10 male per state
        females = [cid for cid in cids_in_state if cells[cid]["gender"] == "Female"]
        males = [cid for cid in cids_in_state if cells[cid]["gender"] == "Male"]
        
        # Sort/sample ensuring diversity across age, education, and race
        # for each gender, pick PER_GENDER diverse cells
        for gender_name, gender_pool in [("Female", females), ("Male", males)]:
            rng.shuffle(gender_pool)
            
            # Greedy diversity selection: select PER_GENDER cells trying to cover distinct age and education tiers
            selected_cids = []
            used_ages = set()
            used_edus = set()
            
            # First pass: try not to repeat age group and education level
            for cid in gender_pool:
                c = cells[cid]
                if c["age_group"] not in used_ages and c["education"] not in used_edus:
                    selected_cids.append(cid)
                    used_ages.add(c["age_group"])
                    used_edus.add(c["education"])
                if len(selected_cids) == PER_GENDER:
                    break
            
            # Second pass: fill if still under PER_GENDER
            if len(selected_cids) < PER_GENDER:
                for cid in gender_pool:
                    if cid not in selected_cids:
                        selected_cids.append(cid)
                    if len(selected_cids) == PER_GENDER:
                        break
                        
            # Final fallback if pool < PER_GENDER
            while len(selected_cids) < PER_GENDER and gender_pool:
                selected_cids.append(rng.choice(gender_pool))

            for cid in selected_cids:
                cell = cells[cid]
                sampled_vote = sample_past_vote(cell["votes"], rng)
                opinion_style = "Recaller" if style_rng.random() < RECALL_SHARE[cell["education"]] else "Constructor"
                media_hours = media_rng.randint(*media_hours_range(cell["age_group"], cell["education"]))
                pid = f"us_{persona_counter:04d}"
                persona_counter += 1
                
                sampled_records.append({
                    "id": pid,
                    "gender": cell["gender"],
                    "age_group": cell["age_group"],
                    "education": cell["education"],
                    "state": cell["state"],
                    "race": cell["race"],
                    "state_cd": cell["state_cd"],
                    "past_vote": sampled_vote,
                    "opinion_style": opinion_style,
                    "media_hours": media_hours,
                })

    print(f"Sampled {len(sampled_records)} personas.")
    
    # Write to CSV
    fieldnames = ["id", "gender", "age_group", "education", "state", "race", "state_cd", "past_vote", "opinion_style", "media_hours"]
    with open(OUTPUT_PATH, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sampled_records)

    print(f"Saved to {OUTPUT_PATH}")

    # Summary statistics
    state_counts = defaultdict(int)
    gender_counts = defaultdict(int)
    age_counts = defaultdict(int)
    edu_counts = defaultdict(int)
    race_counts = defaultdict(int)
    vote_counts = defaultdict(int)

    for r in sampled_records:
        state_counts[r["state"]] += 1
        gender_counts[r["gender"]] += 1
        age_counts[r["age_group"]] += 1
        edu_counts[r["education"]] += 1
        race_counts[r["race"]] += 1
        vote_counts[r["past_vote"]] += 1

    print("\n--- Summary of Sampled Personas ---")
    print(f"Total: {len(sampled_records)}")
    print(f"States: {len(state_counts)} states, min={min(state_counts.values())}, max={max(state_counts.values())}")
    print(f"Gender: {dict(gender_counts)}")
    print(f"Education: {dict(edu_counts)}")
    print(f"Race: {dict(race_counts)}")
    print(f"Past Vote: {dict(vote_counts)}")
    print(f"Opinion style: {dict(Counter(r['opinion_style'] for r in sampled_records))}")
    print(f"Age groups covered: {len(age_counts)} / {len(ALLOWED_AGE_GROUPS)}")


if __name__ == "__main__":
    main()
