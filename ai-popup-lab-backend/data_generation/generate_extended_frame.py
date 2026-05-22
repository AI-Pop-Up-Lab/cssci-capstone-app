from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
STRAT_FRAMES_DIR = BASE_DIR / "country_data" / "stratification_frames"
SURVEYS_DIR = BASE_DIR / "country_data" / "surveys"
COUNTRY_INFO_PATH = BASE_DIR / "country_data" / "country_data_info.json"

def load_country_data() -> dict:
    with open(COUNTRY_INFO_PATH) as f:
        return json.load(f)

def get_survey_path(country: str) -> Path:
    return SURVEYS_DIR / load_country_data()[country]["survey_filename"]

def get_frame_path(country: str) -> Path:
    return STRAT_FRAMES_DIR / load_country_data()[country]["stratification_frame_filename"]