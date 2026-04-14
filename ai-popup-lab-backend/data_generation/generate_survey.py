from pathlib import Path
from .run_scripts import run_survey_script
from .store_data import store_survey
import json

BASE_DIR = Path(__file__).resolve().parent.parent
STRAT_FRAMES_DIR = BASE_DIR / "country_data" / "stratification_frames"
COUNTRY_INFO_PATH = BASE_DIR / "country_data" / "country_data_info.json"

with open(COUNTRY_INFO_PATH) as f:
    country_data = json.load(f)

def generate_survey(country, environment):

    stratframe_filename = country_data[country]['stratification_frame_filename']
    FRAME_FILEPATH = STRAT_FRAMES_DIR / stratframe_filename

    output_path = run_survey_script(frame_filepath=FRAME_FILEPATH, environment=environment, country=country)

    store_survey(environment=environment, filepath=output_path, country=country)