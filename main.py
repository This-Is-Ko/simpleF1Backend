from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import os
from dotenv import load_dotenv
load_dotenv()

from routers import race_router
from database import database
import pymongo

app = FastAPI()

app.include_router(race_router.router)

@app.get("/status")
def server_status():
    return {"status": "healthy"}

@app.get("/database/status")
def database_status():
    try:
        db = database.get_mongodb_client()
        track_entry = db["tracks"].find_one({"name": race["Circuit"]["circuitName"]})
        if "name" in track_entry:
            return {"status": "healthy"}
    except pymongo.errors.PyMongoError as exc:
        return {"error": exc}

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
