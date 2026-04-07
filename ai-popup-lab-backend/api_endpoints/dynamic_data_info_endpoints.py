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

    return {"column_to_rename": column_to_rename}

# GET endpoint to retrieve party colours for a specific country
@router.get("/party_colours")
def get_party_colours(country: str):

    # checking if requested country is in data
    if country not in root_keys:
        return {"error": "Country not found in data."}

    party_colours = country_data[country]['party_colours']

    return {"party_colours": party_colours}

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