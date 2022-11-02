from datetime import date
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api")

class Race(BaseModel):
    name: str
    city: str
    country: str
    raceDatetime: date

class Track(BaseModel):
    name: str
    map: str
    trackDescription: str
    turns: int
    laps: int
    distance: int

class Weather(BaseModel):
    qualifying: str
    race: str

class Highlights(BaseModel):
    link: str

class ResultEntry(BaseModel):
    position: int
    name: str
    time: str
    points: int

class DriverStandingEntry(BaseModel):
    position: int
    name: str
    points: int

class ConstructorStandingEntry(BaseModel):
    position: int
    name: str
    points: int

class NextRace(BaseModel):
    name: str
    country: str
    track: str
    raceDatetime: date
    trackDescription: str

class RaceData(BaseModel):
    race: Race
    track: Track
    weather: Weather
    highlights: Highlights
    results: List[ResultEntry]
    driversStandings: List[DriverStandingEntry]
    constructorsStandings: List[ConstructorStandingEntry]
    nextRace: NextRace

@router.get("/latest", response_model=RaceData)
def latest_race_data():
    
    return {"race": "Test Race"}
