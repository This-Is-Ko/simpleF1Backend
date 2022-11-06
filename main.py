from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.tasks import repeat_every

import os
from dotenv import load_dotenv
load_dotenv()

from routers import race_router
from database import database
import pymongo

from api import race_data

app = FastAPI()

app.include_router(race_router.router)

@app.get("/status")
def server_status():
    return {"status": "healthy"}

@app.get("/database/status")
def database_status():
    try:
        db = database.get_mongodb_client()
        track_entry = db["tracks"].find_one({"name": "test"})
        if "name" in track_entry:
            return {"status": "healthy"}
    except pymongo.errors.PyMongoError as exc:
        return {"error": exc}

@app.on_event("startup")
@repeat_every(seconds=60 * 15)  # 15 min
def refresh_race_data_cache():
    print("Loading cache")
    return race_data.get_latest_race_data()

origins = [
    '*',
    os.environ.get("FRONTEND_URI"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)
