from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware#

# defined routers must be imported here
from api_endpoints import test_router
from api_endpoints import sample_router

# initalise FastAPI app
app = FastAPI(title="React + FastAPI Base App")

# origins to allow CORS requests from react frontend
origins = [
    # Local development URLs, for use with React application
    "http://localhost:3000",  
    "http://127.0.0.1:3000",
    # production frontend url to be added here when deployed
]

# configuring CORS middleware to allow requests from the above origins allowing all methods & headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,  
    allow_methods=["*"], 
    allow_headers=["*"],
)

# routers defined in api_endpoints/__init__.py are included here with the prefix /api
app.include_router(test_router, prefix="/api") # this would be accessed through /api/test_endpoint for example
app.include_router(sample_router, prefix="/api")
