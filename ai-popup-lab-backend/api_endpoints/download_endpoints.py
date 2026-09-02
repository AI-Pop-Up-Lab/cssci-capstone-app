'''
endpoints for 
sending files for the not yet finished and deployed 'data hub' for users to download
'''
from fastapi import APIRouter, HTTPException
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
        raise HTTPException(status_code=404, detail="Country not found in data.")

    country_frame_filename = country_data[country]['stratification_frame_filename']
    if country_frame_filename is None:
        raise HTTPException(status_code=404, detail=f"Stratification frame not available for {country}.")

    country_frame_path = base_dir / "country_data" / 'stratification_frames' / country_frame_filename
    if not country_frame_path.exists():
        raise HTTPException(status_code=404, detail=f"Stratification frame file missing for {country}.")

    return FileResponse(
        path=country_frame_path,
        media_type='text/csv',
        filename=f"{country}_stratification_frame.csv"
    )


# endpoint to retrieve either fieldwork transcripts or survey data, from either the pilot study or the main study
# optionally scoped to a country: if a country-specific file exists (e.g. netherlands_pilot_survey.csv) it is served, otherwise falls back to the shared file
@router.get("/fieldwork_file")
def fieldwork_file(studyType: str, dataType: str, country: str | None = None):

    if studyType not in ['pilot', 'main'] or dataType not in ['survey', 'transcript']:
        raise HTTPException(status_code=400, detail="invalid studyType or dataType. studyType must be 'pilot' or 'main'. dataType must be 'survey' or 'transcript'.")

    if country is not None and country not in root_keys:
        raise HTTPException(status_code=404, detail="Country not found in data.")

    fieldwork_files_path = base_dir / "fieldwork_data"

    if studyType == 'pilot' and dataType == 'survey':
        filename = "pilot_survey.csv"

    elif studyType == 'pilot' and dataType == 'transcript':
        filename = "pilot_transcripts.zip"

    elif studyType == 'main' and dataType == 'survey':
        filename = "fieldwork_survey.csv"

    elif studyType == 'main' and dataType == 'transcript':
        filename = "fieldwork_transcripts.zip"

    filepath = fieldwork_files_path / filename

    if country is not None:
        country_filename = f"{country}_{filename}"
        country_filepath = fieldwork_files_path / country_filename
        if country_filepath.exists():
            filepath = country_filepath
            filename = country_filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Fieldwork file not available: {filename}")

    media_type = 'application/zip' if filename.endswith('.zip') else 'text/csv'

    return FileResponse(
        path=filepath,
        media_type=media_type,
        filename=filename,
        headers={"Access-Control-Expose-Headers": "Content-Disposition"}
    )