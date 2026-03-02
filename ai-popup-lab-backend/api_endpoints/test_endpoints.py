from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/test_endpoint")

# using Pydantic model to define a model for json data
class Message(BaseModel):
    message_text: str

''' 
above class/model is equivalent to/expectant of a json object like this:
{
    message_text: "this is the message text!!!"
}

'''

# test/example for GET endpoint
@router.get("/")
def get_item():
    return {"message": "Text sent from FastAPI backend :D"}

# test/example for POST endpoint
@router.post("/")
def create_item(message: Message):
    return {"response_message": "received message!", "message": message.message_text}