"""
    entry point for weekly data generation worker container

    run worker locally without docker container via 
    export &(cat .env | xargs)
    python -m data_generation.run_job

    test locally with docker

    docker build -f Dockerfile.worker -t worker-test .
    docker run --rm \
        -e AZURE_STORAGE_CONNECTION_STRING="inserthere" \
        -e COUNTRIES="denmark" \
        -e BLOB_CONTAINER_NAME="generated-data" \
        worker-test

"""

import logging
import os
import sys
import tempfile
from pathlib import Path
import json

from .run_scripts import run_extension_script, check_r_available
from .store_data import store_frame, get_blob_client
from .job_guard import already_ran, mark_ran

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

COUNTRIES = os.environ.get("COUNTRIES", "denmark").split(",")
CONTAINER_NAME = os.environ.get("BLOB_CONTAINER_NAME", "generated-data")
BASE_DIR = Path(__file__).resolve().parent.parent
STRAT_FRAMES_DIR = BASE_DIR / "country_data" / "stratification_frames"
SURVEYS_DIR = BASE_DIR / "country_data" / "surveys"


def run_country_job(country: str, blob_client):

    with open(BASE_DIR / "country_data" / "country_data_info.json") as f:
        country_data = json.load(f)

    frame_path  = STRAT_FRAMES_DIR / country_data[country]["stratification_frame_filename"]
    survey_path = SURVEYS_DIR      / country_data[country]["survey_filename"]

    # use a temp dir so the worker container filesystem stays clean.
    # output is uploaded to blob storage before the temp dir is deleted.
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "output"
        output_dir.mkdir()

        run_extension_script(
            survey_path=survey_path,
            frame_path=frame_path,
            output_dir=output_dir,
            country=country,
        )
        store_frame(filepath=output_dir, country=country, client=blob_client)


def main():
    check_r_available()
    blob_client = get_blob_client()
    failed = []

    for country in COUNTRIES:
        logger.info("Processing country: %s", country)

        if already_ran(blob_client, CONTAINER_NAME, country):
            logger.info("Already ran for %s this week, skipping.", country)
            continue

        try:
            run_country_job(country, blob_client)
            mark_ran(blob_client, CONTAINER_NAME, country)
            logger.info("Success: %s", country)
        except Exception:
            logger.exception("Country failed: %s", country)
            failed.append(country)

    if failed:
        logger.error("Job finished with failures: %s", failed)
        sys.exit(1)
    else:
        logger.info("All countries success.")


if __name__ == "__main__":
    main()