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
    raceDateTime: str
    dateTimeUtc: str

class Track(BaseModel):
    name: str
    mapUri: str
    description: str
    turns: int
    laps: int
    distance: int
    drsDetectionZones: int
    drsZones: int

class Weather(BaseModel):
    qualifying: str
    qualifyingTemp: str
    race: str
    raceTemp: str

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
    teamLogoAlt: str
    fastestLap: str

class DriverStandingEntry(BaseModel):
    position: int
    name: str
    driverCode: str
    points: int
    team: str
    teamLogoUri: str
    teamLogoAlt: str

class ConstructorStandingEntry(BaseModel):
    position: int
    name: str
    points: int
    teamLogoUri: str
    teamLogoAlt: str

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
