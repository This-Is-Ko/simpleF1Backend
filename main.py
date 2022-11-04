from typing import Union

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from routers import race_router

from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()

app.include_router(race_router.router)

@app.get("/status")
def server_status():
    return {"status": "healthy"}

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins
)