from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
import json
from pathlib import Path
import io
import os
import re

from azure_storage_utils import (
    get_blob_service_client,
    read_dataframe,
    CONTAINER_NAME,
    get_simple_frame_aggregate_path,
    get_demographic_frame_aggregate_path,
    get_district_frame_aggregate_path,
    get_national_summary_aggregate_path,
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


# GET endpoint to retrieve the weekly national summary aggregate (week x vote
# choice: lower_95 / median / upper_95) used by the frontend for the main
# longitudinal graph
@router.get("/country_longitudinal_aggregated_national_summary")
def country_longitudinal_aggregated_national_summary(country: str):

    if country not in root_keys:
        raise HTTPException(status_code=404, detail="Country not found in data.")

    return _stream_blob_as_csv(get_national_summary_aggregate_path(country))


_WEEK_RE = re.compile(r"^(\d{4})[-_ ]?W?(\d{1,2})$", re.IGNORECASE)


def _week_sort_key(week) -> tuple[int, int]:
    """'2026-W30' / '2026_30' -> (2026, 30), so weeks compare numerically
    rather than as strings. Unparseable labels sort first and so never win."""
    m = _WEEK_RE.match(str(week).strip())
    return (int(m.group(1)), int(m.group(2))) if m else (-1, -1)


# GET endpoint to retrieve ONLY the most recent week of the national summary
# aggregate (same columns as the full aggregate: week, vote_choice, lower_95,
# median, upper_95), used by the landing page bar chart. The latest week is
# simply the highest ISO week present in the aggregate, so it needs no
# configuration and updates itself whenever the weekly job adds a week.
# Production aggregate only -- never reads backfill_storage / hotfix_backfill.
@router.get("/country_latest_national_summary")
def country_latest_national_summary(country: str):

    if country not in root_keys:
        raise HTTPException(status_code=404, detail="Country not found in data.")

    try:
        df = read_dataframe(get_national_summary_aggregate_path(country))
    except Exception:
        raise HTTPException(status_code=404, detail="National summary not yet available.")

    if df.empty or "week" not in df.columns:
        raise HTTPException(status_code=404, detail="National summary not yet available.")

    latest = max(df["week"].dropna().unique(), key=_week_sort_key)
    latest_rows = df[df["week"] == latest]

    return Response(
        content=latest_rows.to_csv(index=False),
        media_type="text/csv",
    )


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
