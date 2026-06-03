# doesn't do much now that i think about it, just prints innit

import logging
import os

logger = logging.getLogger(__name__)

ENV = os.getenv("ENV", "production")
COUNTRIES = os.environ.get("COUNTRIES", "denmark").split(",")

def generate_data():

    logger.info("Starting data generation. ENV=%s, countries=%s", ENV, COUNTRIES)