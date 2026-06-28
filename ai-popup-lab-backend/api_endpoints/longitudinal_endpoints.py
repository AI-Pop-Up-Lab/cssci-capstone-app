from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import json
from pathlib import Path
import pandas as pd
import io

from data_generation.store_data import get_blob_client, CONTAINER_NAME
from data_generation.aggregate_longitudinal import _longitudinal_blob_name, _longitudinal_demographic_blob_name

router = APIRouter(prefix="/longitudinal")

# loading data info json, finding relative filepath and opening
base_dir = Path(__file__).parent.parent  # goes up from api_endpoints/ to project root
json_path = base_dir / "country_data" / "country_data_info.json"

with open(json_path) as f:
    country_data = json.load(f)

root_keys = list(country_data.keys())

def _stream_blob_as_csv(blob_name: str) -> StreamingResponse:
    client = get_blob_client()
    blob = client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
    try:
        data = blob.download_blob().readall()
    except Exception:
        raise HTTPException(status_code=404, detail=f"Longitudinal data not yet available.")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv",
        headers={"Content-Disposition": f"inline; filename={blob_name.split('/')[-1]}"}
    )

# ENDPOINTS BELOW

# GET endpoint to retrieve base aggregated longitudinal data for a country
# @router.get("/country_longitudinal_aggregated_simple")
# def country_longitudinal_aggregated_simple(country: str):

#     if country not in root_keys:
#         raise HTTPException(status_code=404, detail="Country not found in data.")
    
#     return _stream_blob_as_csv(_longitudinal_blob_name(country))

@router.get("/country_longitudinal_aggregated_simple")
def country_longitudinal_aggregated_simple(country: str):

    if country not in root_keys:
        raise HTTPException(status_code=404, detail="Country not found in data.")
    
    test_file = Path(__file__).parent / "simple_test.csv"
    return FileResponse(test_file, media_type="text/csv")

# GET endpoint to retrieve aggregated longitudinal data with all demographics for a country
# @router.get("/country_longitudinal_aggregated_demographics")
# def country_longitudinal_aggregated_demographics(country: str):

#     if country not in root_keys:
#         raise HTTPException(status_code=404, detail="Country not found in data.")
    
#     return _stream_blob_as_csv(_longitudinal_demographic_blob_name(country))

@router.get("/country_longitudinal_aggregated_demographics")
def country_longitudinal_aggregated_demographics(country: str):

    if country not in root_keys:
        raise HTTPException(status_code=404, detail="Country not found in data.")
    
    test_file = Path(__file__).parent / "demographic_test.csv"
    return FileResponse(test_file, media_type="text/csv")