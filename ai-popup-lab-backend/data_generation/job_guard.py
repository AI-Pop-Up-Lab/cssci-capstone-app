from datetime import date
from azure.storage.blob import BlobServiceClient
import os

STORAGE_CONNECTION_STRING = os.environ["AZURE_STORAGE_CONNECTION_STRING"]

def _this_week() -> tuple[int, int]:
    today = date.today()
    year, week, _ = today.isocalendar()
    return year, week

def get_run_key(country: str) -> str:
    today = date.today()
    year, week, _ = today.isocalendar()
    return f"job-runs/{country}/{year}_{week:02d}.lock"

def already_ran(client: BlobServiceClient, container: str, country: str) -> bool:
    blob = client.get_blob_client(container=container, blob=get_run_key(country))
    try:
        blob.get_blob_properties()
        return True
    except Exception:
        return False

def mark_ran(client: BlobServiceClient, container: str, country: str):
    blob = client.get_blob_client(container=container, blob=get_run_key(country))
    blob.upload_blob(b"done", overwrite=True)


# Typed guards for differentiating MRP and panel runs

def get_run_key_typed(country: str, job_type: str, year: int | None = None, week: int | None = None) -> str:
    if year is None or week is None:
        year, week = _this_week()
    return f"job-runs/{job_type}/{country}/{year}_{week:02d}.lock"

def already_ran_typed(
    client: BlobServiceClient,
    container: str,
    country: str,
    job_type: str,
    year: int | None = None,
    week: int | None = None,
) -> bool:
    blob = client.get_blob_client(
        container=container, blob=get_run_key_typed(country, job_type, year, week)
    )
    try:
        blob.get_blob_properties()
        return True
    except Exception:
        return False

def mark_ran_typed(
    client: BlobServiceClient,
    container: str,
    country: str,
    job_type: str,
    year: int | None = None,
    week: int | None = None,
) -> None:
    blob = client.get_blob_client(
        container=container, blob=get_run_key_typed(country, job_type, year, week)
    )
    blob.upload_blob(b"done", overwrite=True)