from datetime import date
from azure.storage.blob import BlobServiceClient
import os

STORAGE_CONNECTION_STRING = os.environ["AZURE_STORAGE_CONNECTION_STRING"]

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