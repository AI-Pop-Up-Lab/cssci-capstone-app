'''
endpoints for 
sending files for the not yet finished and deployed 'data hub' for users to download
'''
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
import json
from pathlib import Path
import pandas as pd

router = APIRouter(prefix="/download")

# loading data info json, finding relative filepath and opening
base_dir = Path(__file__).parent.parent  # goes up from api_endpoints/ to project root
json_path = base_dir / "country_data" / "country_data_info.json"

with open(json_path) as f:
    country_data = json.load(f)

root_keys = list(country_data.keys())


# ENDPOINTS BELOW

# GET endpoint to retrieve raw stratification frame for a country
@router.get("/country_frame_raw")
def country_frame_raw(country: str):

    # checking if requested country is in data
    if country not in root_keys:
        return {"error": "Country not found in data."}

    country_sample_filename = country_data[country]['survey_filename']
    country_sample_path = base_dir / "country_data" / 'surveys' / country_sample_filename

    return FileResponse(
        path=country_sample_path,
        media_type='text/csv',
        filename=f"{country}_stratification_frame.csv"
    )


# endpoint to retrieve either fieldwork transcripts or survey data, from either the pilot study or the main study
@router.get("/fieldwork_file")
def fieldwork_file(studyType: str, dataType: str):

    if studyType not in ['pilot', 'main'] or dataType not in ['survey', 'transcript']:
        return {"error": "invalid studyType or dataType. studyType must be 'pilot' or 'main'. dataType must be 'survey' or 'transcript'."}

    fieldwork_files_path = base_dir / "fieldwork_data"

    if studyType == 'pilot' and dataType == 'survey':

        filepath = fieldwork_files_path / "pilot_survey.csv"
        filename = "pilot_survey.csv"

    elif studyType == 'pilot' and dataType == 'transcript':

        filepath = fieldwork_files_path / "pilot_transcripts.zip"
        filename = "pilot_transcripts.zip"

    elif studyType == 'main' and dataType == 'survey':

        filepath = fieldwork_files_path / "fieldwork_survey.csv"
        filename = "fieldwork_survey.csv"

    elif studyType == 'main' and dataType == 'transcript':

        filepath = fieldwork_files_path / "fieldwork_transcripts.zip"
        filename = "fieldwork_transcripts.zip"

    return FileResponse(
        path=filepath,
        media_type='text/csv',
        filename=filename,
        headers={"Access-Control-Expose-Headers": "Content-Disposition"}
    )