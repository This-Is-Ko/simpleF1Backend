from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import os
from dotenv import load_dotenv
load_dotenv()

from routers import race_router

app = FastAPI()

app.include_router(race_router.router)

@app.get("/status")
def server_status():
    return {"status": "healthy"}

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