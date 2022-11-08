from datetime import date
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import List
from schemas import race_classes
from api import race_data

router = APIRouter(prefix="/api")

@router.get("/latest", response_model=race_classes.RaceData)
def latest_race_data():
    return race_data.get_latest_race_data()

@router.get("/update", status_code=200)
def update_race_data():
    return race_data.update_latest_race_data()
