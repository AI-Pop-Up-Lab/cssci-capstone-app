from pathlib import Path
from .run_scripts import run_extension_script
from .store_data import store_frame
import json

BASE_DIR = Path(__file__).resolve().parent.parent
STRAT_FRAMES_DIR = BASE_DIR / "country_data" / "stratification_frames"
SURVEYS_DIR = BASE_DIR / "country_data" / "surveys"
COUNTRY_INFO_PATH = BASE_DIR / "country_data" / "country_data_info.json"

with open(COUNTRY_INFO_PATH) as f:
    country_data = json.load(f)

def generate_extended_frame(country, environment):

    stratframe_filename = country_data[country]['stratification_frame_filename']
    FRAME_FILEPATH = STRAT_FRAMES_DIR / stratframe_filename

    if environment == "development":

        survey_filename = country_data[country]['survey_filename']

        SURVEY_FILEPATH = SURVEYS_DIR / survey_filename

    else:

        # take current survey from azure, add to surveys folder
        # get file path and pass to r script

        pass

    output_path = run_extension_script(survey_path=SURVEY_FILEPATH, frame_path=FRAME_FILEPATH, environment=environment, country=country)

    store_frame(environment=environment, filepath=output_path, country=country)