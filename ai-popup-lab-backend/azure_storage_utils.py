'''
helpers for interacting with azure storage, for downloading and getting files,
as well as determining file paths
'''


'''
STRUCTURE OF DATA IN AZURE

Country
    Stratification frame
    Panels
        Active panel
        Historical panels
        Checkpoints
            Latest checkpoint for every and current week
    Extended frames
        Extended frame for every week
    Aggregates
        Simple frame aggregate
        Demographic frame aggregate
        Panel aggregate
    gdelt cache
        gdelt cache for every week
    backfill storage
        biography only panels
            all panels generated biography only from backfill
        backfill active panel (manually-seeded, week-(t-1) input for a backfill run)
        backfill historical panels
            per-week result snapshot for each backfilled week
        backfill checkpoints
            in-progress checkpoint for the week currently being backfilled
    Job runs
        job type
            lock files
    Fieldwork data
    Codebooks
        all codebooks
'''

import io
import os
import pandas as pd
from azure.storage.blob import BlobServiceClient

CONNECTION_STRING = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
CONTAINER_NAME = os.environ.get("BLOB_CONTAINER_NAME", "generated-data")

_blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
_container_client = _blob_service_client.get_container_client(CONTAINER_NAME)


'''----------------
PATH HELPERS
----------------'''

def get_stratification_frame_path(country):
    return f"{country}/{country}_strat_frame.csv"


def get_active_panel_path(country):
    return f"{country}/panels/{country}_active_panel.csv"


def get_historical_panel_path(country, iso_week):
    return f"{country}/panels/{iso_week}_{country}_panel_results.csv"


def get_panel_checkpoint_path(country, iso_week):
    return f"{country}/panels/checkpoints/{iso_week}_panel_checkpoint.csv"


def get_extended_frame_path(country, iso_week):
    return f"{country}/extended_frames/{iso_week}_extended_frame.csv"


def get_simple_frame_aggregate_path(country):
    return f"{country}/aggregates/{country}_simple_frame_aggregate.csv"


def get_demographic_frame_aggregate_path(country):
    return f"{country}/aggregates/{country}_demographic_frame_aggregate.csv"


def get_panel_aggregate_path(country):
    return f"{country}/aggregates/{country}_panel_aggregate.csv"


def get_gdelt_cache_path(country, iso_week):
    return f"{country}/gdelt_cache/{iso_week}_gdelt.csv"


def get_backfill_biography_panel_path(country, iso_week):
    return f"{country}/backfill_storage/biography_only_panels/{iso_week}_{country}_panel_biography.csv"


def get_backfill_active_panel_path(country):
    """
    The manually-seeded 'current' active panel a backfill run advances week by
    week. Place the week-(t-1) panel here before kicking off a backfill run —
    this lives on a separate track from the production `get_active_panel_path`
    blob, so backfills never read or overwrite live panel state.
    """
    return f"{country}/backfill_storage/{country}_active_panel.csv"


def get_backfill_historical_panel_path(country, iso_week):
    """
    Per-week output snapshot for a backfilled week. Mirrors
    get_historical_panel_path but lives on the backfill track, so results
    from different backfilled weeks (or a backfill re-running a week also
    covered by production) never collide with each other or with production.
    """
    return f"{country}/backfill_storage/historical_panels/{iso_week}_{country}_panel_results.csv"


def get_backfill_panel_checkpoint_path(country, iso_week):
    """Scratch checkpoint for the week currently being backfilled. Never read as an input."""
    return f"{country}/backfill_storage/checkpoints/{iso_week}_panel_checkpoint.csv"


def get_job_lock_path(country, job_type, iso_week):
    return f"{country}/job_runs/{job_type}/{iso_week}.lock"


'''----------------
UPLOAD HELPERS
----------------'''

def upload_dataframe(df, blob_path, overwrite=True):
    '''
    Uploads a pandas DataFrame to Azure Blob Storage as a CSV at blob_path.
    '''
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)

    blob_client = _container_client.get_blob_client(blob_path)
    blob_client.upload_blob(csv_buffer.getvalue(), overwrite=overwrite)


def upload_file(local_path, blob_path, overwrite=True):
    '''
    Uploads a local file as-is to Azure Blob Storage at blob_path.
    '''
    blob_client = _container_client.get_blob_client(blob_path)
    with open(local_path, "rb") as f:
        blob_client.upload_blob(f, overwrite=overwrite)


def mark_job_ran(country, job_type, iso_week):
    '''Writes a lock blob marking a job type as complete for a given country/week.'''
    blob_client = _container_client.get_blob_client(get_job_lock_path(country, job_type, iso_week))
    blob_client.upload_blob(b"done", overwrite=True)


'''----------------
DOWNLOAD / READ HELPERS
----------------'''

def read_dataframe(blob_path):
    '''
    Reads a CSV blob from Azure Blob Storage into a pandas DataFrame.
    Raises azure.core.exceptions.ResourceNotFoundError if blob_path doesn't exist.
    '''
    blob_client = _container_client.get_blob_client(blob_path)
    stream = blob_client.download_blob()
    return pd.read_csv(io.BytesIO(stream.readall()))


def read_dataframe_or_none(blob_path):
    '''Like read_dataframe, but returns None instead of raising if the blob is missing.'''
    try:
        return read_dataframe(blob_path)
    except Exception:
        return None


def blob_exists(blob_path):
    '''
    Returns True if a blob exists at blob_path, False otherwise.
    '''
    return _container_client.get_blob_client(blob_path).exists()


def already_ran(country, job_type, iso_week):
    '''Returns True if a lock blob already exists for this country/job_type/week.'''
    return blob_exists(get_job_lock_path(country, job_type, iso_week))


def get_blob_service_client():
    '''
    Returns the underlying BlobServiceClient, for callers that need a raw
    client rather than one of the path helpers above (e.g. aggregate_longitudinal.py,
    which takes a BlobServiceClient + container name directly).
    '''
    return _blob_service_client
