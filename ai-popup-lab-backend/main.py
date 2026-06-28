'''
entry point for API
runs api and takes in all routers and endpoint defined in other files
also runs a function daily that resets some IP limiting
'''

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware#

# defined routers must be imported here
from api_endpoints import test_router
from api_endpoints import sample_router
from api_endpoints import chat_router
from api_endpoints import dynamic_data_router
from api_endpoints import admin_router
from api_endpoints import download_router
from api_endpoints import longitudinal_router

# from app.db.init_db import init_db, seed_demo_data
from user_limiting.ip_reset import reset_ip_request_limits

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# timezone data for amsterdam
AMSTERDAM = ZoneInfo("Europe/Amsterdam")

# run every midnight
async def run_daily():
    while True:
        now = datetime.now(AMSTERDAM)
        next_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        await asyncio.sleep((next_midnight - now).total_seconds())
        reset_ip_request_limits()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # init_db()
    # seed_demo_data()
    logger.info("API starting up")
    asyncio.create_task(run_daily())
    # asyncio.create_task(run_weekly())
    yield
    logger.info("API shutting down")

# initalise FastAPI app
app = FastAPI(title="React + FastAPI Base App", lifespan=lifespan)
# origins to allow CORS requests from react frontend
origins = [
    # Local development URLs, for use with React application
    "http://localhost:3000",  
    "http://127.0.0.1:3000",

    # production urls
    # "https://ai-pollster.vercel.app", oldie but not goldie
    "https://www.mechanical-pollster.com",
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


# routers defined in api_endpoints/__init__.py are included here with the prefix /api
app.include_router(test_router, prefix="/api") # this would be accessed through /api/test_endpoint for example
app.include_router(sample_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(dynamic_data_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(download_router, prefix="/api")
app.include_router(longitudinal_router, prefix="/api")
