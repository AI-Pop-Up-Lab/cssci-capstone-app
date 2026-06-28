'''
stores generated synthetic surveys and extended frames on the Azure storage account blob storage
only stores frames for now
'''
from pathlib import Path
from datetime import date
import os
import logging
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)

STORAGE_CONNECTION_STRING = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
CONTAINER_NAME = os.environ.get("BLOB_CONTAINER_NAME", "generated-data")

frame_filename_ending = '_extended_frame'
survey_filename_ending = '_survey'

def get_blob_client() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)

def get_file_suffix() -> str:
    today = date.today()
    year, week, _ = today.isocalendar()
    return f"{year}_{week:02d}"

def results_blob_name(country: str, year: int, week: int) -> str:
    return f"panel-results/{country}/{year}_{week:02d}_{country}_panel_results.csv"

def download_blob_to_path(client: BlobServiceClient, blob_name: str, dest_path: Path) -> Path:
    """Download a blob to a local path. Raises FileNotFoundError if the blob doesn't exist."""
    blob = client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
    try:
        data = blob.download_blob().readall()
    except Exception as exc:
        raise FileNotFoundError(f"Blob not found: {blob_name}") from exc

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(data)
    logger.info("Downloaded %s → %s", blob_name, dest_path)
    return dest_path

def store_frame(filepath: Path, country: str, client: BlobServiceClient) -> str:

    source = Path(filepath) / "mrp_extended_frame_predictions.csv"

    if not source.exists():
        raise FileNotFoundError(f"Expected R output not found: {source}")

    blob_name = f"extended-frames/{country}/{get_file_suffix()}_extended_frame.csv"
    blob = client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)

    with open(source, "rb") as f:
        blob.upload_blob(f, overwrite=True)

    logger.info("Uploaded %s → %s", source, blob_name)
    
    return blob_name