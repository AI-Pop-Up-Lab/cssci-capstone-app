from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware#

# defined routers must be imported here
from api_endpoints import test_router
from api_endpoints import sample_router
from api_endpoints import chat_router
from app.db.init_db import init_db, seed_demo_data

# initalise FastAPI app
app = FastAPI(title="React + FastAPI Base App")

# origins to allow CORS requests from react frontend
origins = [
    # Local development URLs, for use with React application
    "http://localhost:3000",  
    "http://127.0.0.1:3000",

    # production urls
    "https://ai-pollster.vercel.app",
    "https://delightful-bay-00709f403.6.azurestaticapps.net"
]

# configuring CORS middleware to allow requests from the above origins allowing all methods & headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,  
    allow_methods=["*"], 
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    seed_demo_data()

# routers defined in api_endpoints/__init__.py are included here with the prefix /api
app.include_router(test_router, prefix="/api") # this would be accessed through /api/test_endpoint for example
app.include_router(sample_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
