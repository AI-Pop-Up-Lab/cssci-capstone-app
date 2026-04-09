from fastapi import APIRouter
from pydantic import BaseModel
import json
from pathlib import Path
import pandas as pd

router = APIRouter(prefix="/samples")

# loading data info json, finding relative filepath and opening
base_dir = Path(__file__).parent.parent  # goes up from api_endpoints/ to project root
json_path = base_dir / "country_data" / "country_data_info.json"

with open(json_path) as f:
    country_data = json.load(f)

root_keys = list(country_data.keys())


# ENDPOINTS BELOW

# GET endpoint to retrieve sample data for a specific country
@router.get("/country_sample")
def get_country_sample(country: str):

    # print(f"Received request for country: {country}")

    # checking if requested country is in data
    if country not in root_keys:
        return {"error": "Country not found in data."}

    country_sample_filename = country_data[country]['daily_sample_filename']
    country_sample_path = base_dir / "country_data" / 'daily_sample' / country_sample_filename

    # reading csv to dataframe then converting to list of dicts for json response
    df = pd.read_csv(country_sample_path)
    dict_list_for_js = json.loads(df.to_json(orient="records")) # returns a list of row objects

    return {"data": dict_list_for_js}

# GET endpoint to retrieve stratification frame for a specific country
@router.get("/country_stratification_frame")
def get_country_stratification_frame(country: str):

    # checking if requested country is in data
    if country not in root_keys:
        return {"error": "Country not found in data."}

    country_frame_filename = country_data[country]['stratification_frame_filename']
    country_frame_path = base_dir / "country_data" / 'stratification_frames' / country_frame_filename

    # reading csv to dataframe then converting to list of dicts for json response
    df = pd.read_csv(country_frame_path)
    df = df.astype(object).where(pd.notna(df), other=None)
    dict_list_for_js = df.to_dict(orient="records")  # returns a list of row objects

    return {"data": dict_list_for_js}

# GET endpoint to retrieve columns and respective unique values for a specific country
@router.get("/columns_and_uniques")
def get_country_cols_uniques(country: str):

    # checking if requested country is in data
    if country not in root_keys:
        return {"error": "Country not found in data."}

    relevant_columns = country_data[country]['demographic_search_columns']
    column_unique_vals = country_data[country]['column_unique_vals']

    for key in column_unique_vals:
        if not isinstance(column_unique_vals[key][0], str):
            continue

        column_unique_vals[key].sort()
    

    data = {"relevant_columns": relevant_columns, "column_unique_vals": column_unique_vals}

    return data