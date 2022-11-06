from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

import os
from dotenv import load_dotenv, dotenv_values
load_dotenv()
config = dotenv_values(".env")

from routers import race_router

app = FastAPI()

app.include_router(race_router.router)

@app.get("/status")
def server_status():
    return {"status": "healthy"}

@app.get("/envtest")
def server_status():
    return config

@app.get("/envtest1")
def server_status():
    return os.environ

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

@app.on_event("startup")
def startup_db_client():
    app.mongodb_client = MongoClient(config["ATLAS_URI"])
    app.database = app.mongodb_client[config["DB_NAME"]]
    print("Connected to MongoDB")
    
@app.on_event("shutdown")
def shutdown_db_client():
    app.mongodb_client.close()