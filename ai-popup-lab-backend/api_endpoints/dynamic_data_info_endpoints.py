from fastapi import APIRouter
from pydantic import BaseModel
import json
from pathlib import Path
import pandas as pd
import os
from datetime import datetime, timedelta, timezone
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

router = APIRouter(prefix="/dynamicdata")

# loading data info json, finding relative filepath and opening
base_dir = Path(__file__).parent.parent  # goes up from api_endpoints/ to project root
json_path = base_dir / "country_data" / "country_data_info.json"

with open(json_path) as f:
    country_data = json.load(f)

root_keys = list(country_data.keys())


# helper to generate a download url that lasts for 1 hour, for extended frame from azure blob storage
def generate_download_url(country: str, year: int, week: int) -> str:
    """
    Generate a 1-hour SAS download URL for a specific country's extended frame blob.
    Requires AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY env vars.
    """
    blob_name    = f"extended-frames/{country}/{year}_{week:02d}_extended_frame.csv"
    account_name = os.environ["AZURE_STORAGE_ACCOUNT_NAME"]
    account_key  = os.environ["AZURE_STORAGE_ACCOUNT_KEY"]
    container    = os.environ.get("BLOB_CONTAINER_NAME", "generated-data")

    sas = generate_blob_sas(
        account_name=account_name,
        container_name=container,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    return f"https://{account_name}.blob.core.windows.net/{container}/{blob_name}?{sas}"

# ENDPOINTS BELOW

# get endpoint to retrieve download url for extended frame
@router.get("/extended_frame_url")
def get_extended_frame_url(country: str, year: int, week: int):
    if country not in root_keys:
        return {"error": "Country not found in data."}

    url = generate_download_url(country=country, year=year, week=week)
    return {"url": url}

# GET endpoint to retrieve sample data for a specific country
@router.get("/nextGE_col_name")
def get_nextGE_col_name(country: str):

    # checking if requested country is in data
    if country not in root_keys:
        return {"error": "Country not found in data."}

    column_to_rename = country_data[country]['next_GE_vote_colname']

    return {"column_to_rename": column_to_rename}

# GET endpoint to retrieve party colours for a specific country
@router.get("/party_colours")
def get_party_colours(country: str):

    # checking if requested country is in data
    if country not in root_keys:
        return {"error": "Country not found in data."}

    party_colours = country_data[country]['party_colours']

    return {"party_colours": party_colours}

# GET endpoint to retrieve party colours for a specific country
@router.get("/party_info")
def get_party_info(country: str):

    # checking if requested country is in data
    if country not in root_keys:
        return {"error": "Country not found in data."}

    country_info_filename = country_data[country]['party_info_filename']
    country_info_path = base_dir / "country_data" / 'country_parties' / country_info_filename

    # reading csv to dataframe then converting to list of dicts for json response
    df = pd.read_csv(country_info_path, sep=';')
    dict_list_for_js = json.loads(df.to_json(orient="records")) # returns a list of row objects

    alternative_data = {
        row['party']: {k: v for k, v in row.items() if k != 'party'}
        for row in dict_list_for_js
    }

    return {"data": dict_list_for_js, "alternative_data": alternative_data}

# GET endpoint to retrieve sentences for columns in the chart demographic search for a specific country
@router.get("/column_sentences")
def get_column_sentences(country: str):

    # checking if requested country is in data
    if country not in root_keys:
        return {"error": "Country not found in data."}

    column_sentences = country_data[country]['column_sentences']

    return {"column_sentences": column_sentences}

# GET endpoint to retrieve the order of sentences for the chart demographic search for a specific country
@router.get("/search_sentence_order")
def get_search_sentence_order(country: str):

    # checking if requested country is in data
    if country not in root_keys:
        return {"error": "Country not found in data."}

    search_sentence_order = country_data[country]['search_sentence_order']

    return {"search_sentence_order": search_sentence_order}

# GET endpoint to retrieve the 'all' placeholder for the chart demographic search for a specific country
@router.get("/all_placeholder")
def get_all_placeholder(country: str):

    # checking if requested country is in data
    if country not in root_keys:
        return {"error": "Country not found in data."}

    all_placeholder = country_data[country]['all_placeholder']

    return {"all_placeholder": all_placeholder}

# GET endpoint to retrieve the seat allocation method for a specific country
@router.get("/seat_allocation_method")
def get_seat_allocation_method(country: str):

    # checking if requested country is in data
    if country not in root_keys:
        return {"error": "Country not found in data."}

    seat_allocation_method = country_data[country]['seat_allocation_function_name']

    return {"seat_allocation_method": seat_allocation_method}

# GET endpoint to retrieve total electoral seats for a specific country
@router.get("/total_seats")
def get_total_seats(country: str):

    # checking if requested country is in data
    if country not in root_keys:
        return {"error": "Country not found in data."}

    total_seats = country_data[country]['total_seats']

    return {"total_seats": total_seats}