"""
The five persona attributes and their allowed values.

These mirror the US demographic dropdowns on the website's polling page (they come from
the US survey data, see create_unique_column_vals.ipynb in the repo root), so a visitor's
dropdown choice can be matched directly against persona files.

This file is the single source of truth: persona files, the /match endpoint and the
/attributes endpoint (which the frontend can use to build its dropdowns) all use it.
"""

import re

ATTRIBUTES = ("gender", "age_group", "education", "state", "race")

# the value the frontend sends when a dropdown is left on "all"
ANY_VALUE = "all"

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

# order matters for age_group and education: it is used to find the closest persona
# when there is no exact match (see PersonaStore.match)
ALLOWED_VALUES = {
    "gender": ["Female", "Male"],
    "age_group": [
        "18-22", "23-27", "28-32", "33-37", "38-42", "43-47", "48-52",
        "53-57", "58-62", "63-67", "68-72", "73-77", "78-82", "83+",
    ],
    "education": ["No HS", "HS grad", "Some college", "2-year", "4-year", "Post-grad"],
    "state": sorted(STATE_NAMES),
    "race": ["Asian", "Black", "Hispanic", "Native American", "Other/Multi", "White"],
}

ORDERED_ATTRIBUTES = ("age_group", "education")

# how each value is described to the model in the "Who you are" section of the prompt
EDUCATION_DESCRIPTIONS = {
    "No HS": "did not finish high school",
    "HS grad": "high school graduate",
    "Some college": "some college, no degree",
    "2-year": "2-year college (associate) degree",
    "4-year": "4-year college (bachelor's) degree",
    "Post-grad": "postgraduate degree",
}

LABELS = {
    "gender": "Gender",
    "age_group": "Age",
    "education": "Education",
    "state": "State",
    "race": "Race/ethnicity",
}


def _key(value: str) -> str:
    # forgiving comparison: ignore case and extra spaces, and treat the en/em dashes that
    # Word and Google Docs insert as normal hyphens
    value = re.sub(r"[–—]", "-", value)
    return re.sub(r"\s+", " ", value).strip().casefold()


_LOOKUP = {
    attribute: {_key(value): value for value in values}
    for attribute, values in ALLOWED_VALUES.items()
}
# states can also be written out in full ("Florida")
_LOOKUP["state"].update({_key(name): code for code, name in STATE_NAMES.items()})


def normalize(attribute: str, raw) -> str:
    """Return the canonical spelling of `raw` for `attribute`, or raise ValueError."""
    if attribute not in ALLOWED_VALUES:
        raise ValueError(f"unknown attribute '{attribute}'")

    canonical = _LOOKUP[attribute].get(_key(str(raw)))
    if canonical is None:
        allowed = ", ".join(ALLOWED_VALUES[attribute])
        raise ValueError(f"'{raw}' is not a valid {attribute}. Allowed values: {allowed}")
    return canonical


def describe(attribute: str, value: str) -> str:
    """Human-readable version of a canonical value, for the model prompt."""
    if attribute == "age_group":
        return f"{value} years old"
    if attribute == "education":
        return EDUCATION_DESCRIPTIONS[value]
    if attribute == "state":
        return f"{STATE_NAMES[value]} ({value})"
    return value
