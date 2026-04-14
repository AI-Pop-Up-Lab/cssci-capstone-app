from dotenv import load_dotenv
import os

from .generate_survey import generate_survey
from .generate_extended_frame import generate_extended_frame

countries = [
    # "netherlands",
    # "sweden",
    "denmark"
]

load_dotenv()

def generate_data():

    try:
        ENV = os.getenv("ENV")
    except:
        ENV = "deployment"

    for country in countries:
        # generate_survey(country, ENV)
        generate_extended_frame(country, ENV)