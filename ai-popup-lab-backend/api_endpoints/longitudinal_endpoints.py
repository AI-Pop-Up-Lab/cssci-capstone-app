from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
from pathlib import Path
import io
import os

from azure_storage_utils import (
    get_blob_service_client,
    CONTAINER_NAME,
    get_simple_frame_aggregate_path,
    get_demographic_frame_aggregate_path,
    get_district_frame_aggregate_path,
)

router = APIRouter(prefix="/longitudinal")

# loading data info json, finding relative filepath and opening
base_dir = Path(__file__).parent.parent  # goes up from api_endpoints/ to project root
json_path = base_dir / "country_data" / "country_data_info.json"

with open(json_path) as f:
    country_data = json.load(f)

root_keys = list(country_data.keys())


def _stream_blob_as_csv(blob_name: str) -> StreamingResponse:
    client = get_blob_service_client()
    blob = client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
    try:
        downloader = blob.download_blob()
    except Exception:
        raise HTTPException(status_code=404, detail="Longitudinal data not yet available.")

    def iter_chunks():
        # Yields each range-request chunk as it arrives from Azure instead of
        # buffering the entire blob into memory first (readall()) -- keeps
        # memory flat and starts sending bytes to the client immediately,
        # rather than only after the full multi-hundred-MB download finishes.
        for chunk in downloader.chunks():
            yield chunk

    return StreamingResponse(
        iter_chunks(),
        media_type="text/csv",
        headers={"Content-Disposition": f"inline; filename={blob_name.split('/')[-1]}"}
    )


# ENDPOINTS BELOW

# GET endpoint to retrieve base aggregated longitudinal data for a country
@router.get("/country_longitudinal_aggregated_simple")
def country_longitudinal_aggregated_simple(country: str):

    if country not in root_keys:
        raise HTTPException(status_code=404, detail="Country not found in data.")

    return _stream_blob_as_csv(get_simple_frame_aggregate_path(country))


# GET endpoint to retrieve aggregated longitudinal data with all demographics for a country
@router.get("/country_longitudinal_aggregated_demographics")
def country_longitudinal_aggregated_demographics(country: str):

    if country not in root_keys:
        raise HTTPException(status_code=404, detail="Country not found in data.")

    return _stream_blob_as_csv(get_demographic_frame_aggregate_path(country))


# GET endpoint to retrieve the district-level aggregate (week x congressional
# district x party) used by the frontend to project House seats
@router.get("/country_longitudinal_aggregated_districts")
def country_longitudinal_aggregated_districts(country: str):

    if country not in root_keys:
        raise HTTPException(status_code=404, detail="Country not found in data.")

    return _stream_blob_as_csv(get_district_frame_aggregate_path(country))


@router.get("/us_pollster_predictions")
def us_pollster_predictions():

    # defaults must match what the weekly worker writes (weekly-job.yml env)
    blob_name = os.environ.get("US_POLLS_OUTPUT_BLOB_NAME", "us_polls_model_output.json")
    container = os.environ.get("US_POLLS_BLOB_CONTAINER", "polling-data")

    client = get_blob_service_client()
    blob = client.get_blob_client(container=container, blob=blob_name)

    try:
        data = blob.download_blob().readall()
    except Exception:
        raise HTTPException(status_code=404, detail="US pollster predictions not yet available.")

    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/json",
        headers={"Content-Disposition": f"inline; filename={blob_name}"}
    )
