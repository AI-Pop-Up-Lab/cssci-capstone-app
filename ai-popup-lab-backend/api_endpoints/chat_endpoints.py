from fastapi import APIRouter
from pydantic import BaseModel
import json
from pathlib import Path
import pandas as pd
import time

router = APIRouter(prefix="/chat")

# chat message request model
class ChatMessage(BaseModel):
    message: str
    persona_details: dict  
    persona_country: str # used to access the correct country in the biographies json (if used)

# loading data info json, finding relative filepath and opening
base_dir = Path(__file__).parent.parent  # goes up from api_endpoints/ to project root
biographies_json_path = base_dir / "persona_chat" / "biographies.json"
# ^ this is if you want to use a .json file to store the biographies

with open(biographies_json_path) as f:
    biography_data = json.load(f)

root_keys = list(biography_data.keys())

# ENDPOINTS BELOW

# POST endpoint to send message and receive a response from a message
@router.post("/chat_message")
def post_message(request_body: ChatMessage):

    # checking if requested country is in biography data
    if request_body.persona_country not in root_keys:
        return {"error": "Passed country not found in data."}

    # can use the request_body.persona_country and request_body.persona_details['index'] to find the country in biographies.json and then the index to check if the persona already has a biography (each persona has a unique index)

    # calls to external files in the .../ai-popup-lab-backend/persona_chat would be made here, passing the persona details and biography (or biography can be accessed in those files either works), then the response is sent back to the user below as key "message"

    return {"message": f"This would be the persona response. Hello hi hello hello hi it's me the persona. You said {request_body.message}. nice."}
