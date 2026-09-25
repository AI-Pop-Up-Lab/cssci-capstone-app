'''
endpoints for 
retrieving the country data object derived from country_data_info.json, as well as data from azure
'''
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
from pathlib import Path
import pandas as pd

router = APIRouter(prefix="/country_data")

# loading data info json, finding relative filepath and opening
base_dir = Path(__file__).parent.parent  # goes up from api_endpoints/ to project root
json_path = base_dir / "country_data" / "country_data_info.json"

with open(json_path) as f:
    country_data = json.load(f)

root_keys = list(country_data.keys())

# GET endpoint to retrieve country data obj
@router.get("/country_object")
def get_country_object(country: str):

    if country not in root_keys:
        raise HTTPException(status_code=404, detail="Country not found in data.")

    return country_data[country]