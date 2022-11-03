from datetime import date
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

class RaceInfo(BaseModel):
    name: str
    city: str
    country: str
    season: int
    round: int
    date: str
    time: str

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
    driverCode: str
    time: str
    points: int
    team: str
    teamLogoUri: str
    fastestLap: str

class DriverStandingEntry(BaseModel):
    position: int
    name: str
    driverCode: str
    points: int
    team: str
    teamLogoUri: str

class ConstructorStandingEntry(BaseModel):
    position: int
    name: str
    points: int
    teamLogoUri: str

class NextRace(BaseModel):
    name: str
    country: str
    track: str
    date: str
    time: str
    trackDescription: str

class RaceData(BaseModel):
    race: RaceInfo
    track: Track
    weather: Weather
    highlights: Highlights
    results: List[ResultEntry]
    driversStandings: List[DriverStandingEntry]
    constructorsStandings: List[ConstructorStandingEntry]
    nextRace: NextRace
