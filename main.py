from typing import Union

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from routers import race_router


app = FastAPI()

app.include_router(race_router.router)

@app.get("/status")
def server_status():
    return {"status": "healthy"}
