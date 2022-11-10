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
    turns: int
    length: float
    laps: int
    distance: float
    drsDetectionZones: int
    drsZones: int
    
class WeatherEntry(BaseModel):
    type: str
    temp: str

class Weather(BaseModel):
    qualifying: WeatherEntry
    race: WeatherEntry

class Highlights(BaseModel):
    uri: str

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
    fastestLapRank: int
    gridPosition: int
    positionChange: int
    # positionChangeDirection: str

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
    raceDateTime: str
    dateTimeUtc: str

class RaceData(BaseModel):
    race: RaceInfo
    track: Track
    weather: Weather
    highlights: Highlights
    results: List[ResultEntry]
    driversStandings: List[DriverStandingEntry]
    constructorsStandings: List[ConstructorStandingEntry]
    nextRace: NextRace
