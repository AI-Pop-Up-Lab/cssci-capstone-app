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


def store_survey(filepath, country):

    # azure store for when surveys are implemented

    pass

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