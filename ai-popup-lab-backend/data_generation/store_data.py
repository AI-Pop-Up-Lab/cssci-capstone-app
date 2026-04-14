from pathlib import Path
from datetime import date
import shutil

BASE_DIR = Path(__file__).resolve().parent.parent
EXTENDED_FRAMES_DIR = BASE_DIR / "country_data" / "extended_frames"
SURVEYS_DIR = BASE_DIR / "country_data" / "surveys"

frame_filename_ending = '_extended_frame'
survey_filename_ending = '_survey'

def store_survey(environment, filepath, country):

    file_suffix = f"{date.today().year}_{date.today().isocalendar().week}" # e.g. 2026_16 (year, week of year)

    if environment == "development":
        # local store
        pass
    else:
        # azure store
        pass

def store_frame(environment, filepath, country):

    file_suffix = f"{date.today().year}_{date.today().isocalendar().week}" # e.g. 2026_16 (year, week of year)

    EXTENDED_FRAME_PATH = Path(filepath) / "mrp_extended_frame_predictions.csv"

    if environment == "development":
        
        shutil.copy(EXTENDED_FRAME_PATH, EXTENDED_FRAMES_DIR / f"{country}{frame_filename_ending}{file_suffix}.csv")

    else:
        # azure store
        pass