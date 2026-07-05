from ast import literal_eval
import ast
from pathlib import Path
import os
import random
import pandas as pd


def _questions_path() -> Path:
    """
    Resolve questions.csv.
    Can be overridden with QUESTIONS_PATH env var.
    Default: backend_root/country_data/questions.csv
    """
    override = os.getenv("QUESTIONS_PATH")
    if override:
        return Path(override)
    # __file__ = data_generation/panel/survey.py
    # parents[0] = data_generation/panel/
    # parents[1] = data_generation/
    # parents[2] = backend root
    return Path(__file__).resolve().parents[2] / "country_data" / "questions.csv"

def _house_candidates_path() -> Path:
    override = os.getenv("HOUSE_CANDIDATES_PATH")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "country_data" / "wikipedia" / "house_candidates.csv"

def to_list(val):
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            parsed = ast.literal_eval(val)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return [val] if val else []
    return []

def choose_candidate(cand_list, incumbent):
    cand_list = to_list(cand_list)
    if not cand_list:
        return None
    if isinstance(incumbent, str):
        inc_lower = incumbent.lower()
        for c in cand_list:
            if inc_lower == str(c).lower() or inc_lower in str(c).lower():
                return c
    return random.choice(cand_list)

def _normalize_district_code(panel_district_code: str, candidates_df: pd.DataFrame) -> str | None:
    """Panel uses codes like 'AK-1' for single-district states; house_candidates.csv
    uses 'AK-At-Large' for the same seat. Try exact match first, then fall back to
    state-prefix match only when the state has exactly one district on file (safe:
    multi-district states will have >1 match and correctly return no fallback)."""
    if panel_district_code in candidates_df["District"].values:
        return panel_district_code

    state_abbrev = panel_district_code.split("-")[0]
    state_matches = candidates_df[candidates_df["District"].str.startswith(f"{state_abbrev}-")]
    if len(state_matches) == 1:
        return state_matches.iloc[0]["District"]
    return None

def get_district_info(district: str) -> tuple[list[str], str | None]:
    """Look up candidate options + full state name for a US House district (e.g. 'CA-36').
    Returns ([], None) if the district isn't found in house_candidates.csv — caller must
    handle this case (fixes the original NameError bug when a district has no matching row)."""
    candidates_df = pd.read_csv(_house_candidates_path())
    resolved = _normalize_district_code(district, candidates_df)
    if resolved is None:
        return [], None

    row = candidates_df[candidates_df["District"] == resolved].iloc[0]
    inc = row.get("Incumbent")
    dem_candidate = choose_candidate(row.get("Democratic_Candidates"), inc)
    rep_candidate = choose_candidate(row.get("Republican_Candidates"), inc)
    ind_list = to_list(row.get("Independent_ThirdParty"))

    options = [
        *([f"{dem_candidate} (Democratic Party)"] if dem_candidate else []),
        *([f"{rep_candidate} (Republican Party)"] if rep_candidate else []),
        *[f"{c['name']} ({c['party']} Party)" for c in ind_list if isinstance(c, dict)],
    ]
    return options, row.get("State")

def generate_turnout_question(state_full_name: str) -> str:
    return (
        f"If the general election for U.S. House of Representatives in your state of "
        f"{state_full_name} was held today, would you choose NOT to vote? Consider all of your "
        "previous thoughts and background, and any additional context that has been provided. "
        "It is perfectly, absolutely fine to respond with either option. You may also consider "
        "your own personal circumstances, such as health, work, or family obligations. You may "
        "also consider the candidates and their positions on issues that matter to you. A lot of "
        "people did not manage to turnout last time. Please answer with 'Yes' or 'No'."
    )

def generate_question(question_id: str, initial: bool, district: str | None = None) -> str:
    questions_df = pd.read_csv(_questions_path())
    question_rows = questions_df[questions_df["id"] == question_id]
    if question_rows.empty:
        raise ValueError(f"Unknown question id: {question_id}")

    question_row = question_rows.iloc[0]
    question = question_row["question"]
    raw_options = question_row.get("options")

    if pd.isna(raw_options) or not str(raw_options).strip():
        # District-based dynamic options (currently: US House races)
        if not district:
            raise ValueError(f"Question '{question_id}' has no fixed options and requires a district.")
        options, _ = get_district_info(district)
        if not options:
            raise ValueError(f"No candidate data found for district '{district}'.")
    else:
        options = literal_eval(raw_options)

    random.shuffle(options)
    formatted_options = "\n".join(f"{i + 1}. {opt}" for i, opt in enumerate(options))

    if not initial:
        return (
            f"{question}\n"
            "I will now repeat the question. Consider all your previous thought processes "
            "and potentially any additional context. These might have changed your mind, or not. "
            "The options are below. Only respond with the exact format of the option you choose, "
            "do not include any other text. Do not include the number of the response. "
            "You must include a response. Do not include any styling for the response (e.g. bold). "
            "In this final response, consider all previous chats, as well as any additional context "
            "that has been provided.\n"
            f"{formatted_options}"
        )

    return (
        f"{question}\n"
        "The options are below. Do not provide an answer right now. Interpret the question, "
        "provide your reasoning in understanding what is meant by the question and what kind of "
        "information you need to answer this. Fully embody the person you are representing. "
        "You may be provided with more information later. Consider what options you are seriously "
        "thinking about, which ones you might be immediately discarding, what it would take to "
        "swing your mind one way or another. This should be in the range of 300-600 words. "
        "Express the thoughts in the first person. The options are:\n"
        f"{formatted_options}"
    )

