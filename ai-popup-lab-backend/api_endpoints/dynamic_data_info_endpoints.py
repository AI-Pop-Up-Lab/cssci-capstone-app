from fastapi import APIRouter
from pydantic import BaseModel
import json
from pathlib import Path

router = APIRouter(prefix="/dynamicdata")

# loading data info json, finding relative filepath and opening
base_dir = Path(__file__).parent.parent  # goes up from api_endpoints/ to project root
json_path = base_dir / "country_data" / "country_data_info.json"

with open(json_path) as f:
    country_data = json.load(f)

root_keys = list(country_data.keys())


# ENDPOINTS BELOW

# GET endpoint to retrieve sample data for a specific country
@router.get("/nextGE_col_name")
def get_nextGE_col_name(country: str):

    # checking if requested country is in data
    if country not in root_keys:
        return {"error": "Country not found in data."}

    column_to_rename = country_data[country]['next_GE_vote_colname']

    # reading csv to dataframe then converting to list of dicts for json response

    return {"column_to_rename": column_to_rename}