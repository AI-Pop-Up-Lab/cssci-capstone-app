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
    hotfix_backfill (usa-only, split-stage backfill track — see below)
        active panel (manually-seeded, week-(t-1) input; stage 1 advances this week by week)
        biography_panels
            per-week snapshot after attrition + biography/media_diet (stage 1 output, stage 2 input)
        vote_choice_panels
            per-week snapshot after the survey wave / vote choice (stage 2 output)
        extended_frames
            per-week MRP extended frame (stage 2 output)
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


def get_backfill_extended_frame_path(country, iso_week):
    """
    Per-week MRP extended-frame output for a backfilled week. Mirrors
    get_extended_frame_path but lives on the backfill track, so a backfill's
    MRP output never overwrites the production extended frame for that week.
    """
    return f"{country}/backfill_storage/extended_frames/{iso_week}_extended_frame.csv"


def get_backfill_panel_checkpoint_path(country, iso_week):
    """Scratch checkpoint for the week currently being backfilled. Never read as an input."""
    return f"{country}/backfill_storage/checkpoints/{iso_week}_panel_checkpoint.csv"


# ── Hotfix backfill (split-stage: sequential attrition+bio, then parallel
#    survey+MRP) — a second, independent backfill track alongside
#    backfill_storage above. Kept entirely separate so this hotfix never
#    reads or overwrites the (full-cycle, single-track) backfill_storage
#    blobs or production state. ─────────────────────────────────────────────

def get_hotfix_backfill_active_panel_path(country):
    """
    The manually-seeded 'current' active panel that hotfix-backfill stage 1
    advances week by week (attrition + replacement only). Seed this with a
    genuine week-(t-1) panel before the first week of a stage-1 run — stage 1
    itself never seeds it. Stage 2 never reads this blob directly; it reads
    the per-week snapshot in biography_panels instead, so multiple stage-2
    containers running in parallel never contend over this single blob.
    """
    return f"{country}/hotfix_backfill/{country}_active_panel.csv"


def get_hotfix_backfill_biography_panel_path(country, iso_week):
    """
    Per-week snapshot written by hotfix-backfill stage 1 once that week's
    attrition + biography/media_diet generation is done — the full panel,
    no vote-choice columns yet. This is what stage 2 reads as input for that
    week, and stage 2 for different weeks reads different blobs here, which
    is what lets those stage-2 runs happen in parallel with no contention.
    """
    return f"{country}/hotfix_backfill/biography_panels/{iso_week}_{country}_panel_biography.csv"


def get_hotfix_backfill_vote_panel_path(country, iso_week):
    """Per-week panel snapshot after hotfix-backfill stage 2's survey wave (vote choice included)."""
    return f"{country}/hotfix_backfill/vote_choice_panels/{iso_week}_{country}_panel_votes.csv"


def get_hotfix_backfill_extended_frame_path(country, iso_week):
    """Per-week MRP extended-frame output from hotfix-backfill stage 2."""
    return f"{country}/hotfix_backfill/extended_frames/{iso_week}_extended_frame.csv"


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
