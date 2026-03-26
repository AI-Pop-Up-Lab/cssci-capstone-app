import asyncio
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

from app.db.init_db import init_db, seed_demo_data

from scheduled_routines import weekly_sample_generation, reset_ip_request_limits

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


# run every midnight Sunday --> Monday for sample gen (commented out cause auto gen not implemented yet)
# async def run_weekly():
#     while True:
#         now = datetime.now(AMSTERDAM)

#         # next Monday at midnight
#         days_until_monday = (7 - now.weekday()) % 7 or 7
#         next_monday = (now + timedelta(days=days_until_monday)).replace(
#             hour=0, minute=0, second=0, microsecond=0
#         )
#         await asyncio.sleep((next_monday - now).total_seconds())
#         weekly_sample_generation()



@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_demo_data()
    asyncio.create_task(run_daily())
    # asyncio.create_task(run_weekly())
    yield

# initalise FastAPI app
app = FastAPI(title="React + FastAPI Base App", lifespan=lifespan)

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


# routers defined in api_endpoints/__init__.py are included here with the prefix /api
app.include_router(test_router, prefix="/api") # this would be accessed through /api/test_endpoint for example
app.include_router(sample_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(dynamic_data_router, prefix="/api")