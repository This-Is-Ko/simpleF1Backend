from typing import Union

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

app = FastAPI()

prefix_router = APIRouter(prefix="/api")

class Item(BaseModel):
    name: str
    price: float
    is_offer: Union[bool, None] = None


@app.get("/status")
def read_root():
    return {"status": "healthy"}


@prefix_router.get("/latest")
def read_latest_race():
    return {"race": "Test Race"}

app.include_router(prefix_router)
