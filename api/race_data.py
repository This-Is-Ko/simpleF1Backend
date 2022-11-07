from schemas import race_classes
import requests
import requests_cache
from fastapi import HTTPException
import re
from datetime import datetime, timedelta
from pathlib import Path
from tzwhere import tzwhere
import pytz

import os
from dotenv import load_dotenv
load_dotenv()

from .weather_code_converter import convert_weather_code

from .database import mongodb_api_find_one, mongodb_api_insert_one

TRACK_INFORMATION = Path(__file__).parent /"./../data/tracks.csv"
HIGHLIGHTS_INFORMATION = Path(__file__).parent /"./../data/highlights.csv"

cache = {}

def get_latest_race_data():
    # Enable in dev env
    # requests_cache.install_cache("race_data_responses", allowable_methods=('GET'), allowable_codes=(200,), urls_expire_after={"http://ergast.com/api/f1/": 36000, })
    
    # Simple in-memory caching response - 15 minutes 
    global cache
    if "race_data" in cache:
        if cache["expiry"] > datetime.now():
            return cache["race_data"]
        else:
            cache = {}
    

    race_response = call_data_source("http://ergast.com/api/f1/current/last/results.json")
    if race_response == {}:
        raise HTTPException(status_code=503, detail="Upstream error")
    race = race_response["MRData"]["RaceTable"]["Races"][0]

    # Check if race data is stored in database
    race_find_payload = {
        "dataSource": os.environ.get("MONGODB_CLUSTER"),
        "database": os.environ.get("DB_NAME"),
        "collection": "race",
        "filter": {
            "race.season": int(race["season"]),
            "race.round": int(race["round"])
      }
    }
    race_response = mongodb_api_find_one(race_find_payload)
    if "race" in race_response:
        cache.update({"race_data": race_response})
        expiry = datetime.now() + timedelta(minutes=15)
        cache.update({"expiry": expiry})
        return race_response

    # Find race timezone
    tz = tzwhere.tzwhere()
    timezone = tz.tzNameAt(float(race["Circuit"]["Location"]["lat"]),float(race["Circuit"]["Location"]["long"]))
    race_timezone = pytz.timezone(timezone)
    # Create datetime object 
    race_datetime_str = str(race["date"]) + " " + str(race["time"])
    race_datetime = datetime.strptime(race_datetime_str, "%Y-%m-%d %H:%M:%SZ")
    # Set datetime to greenwich time
    gmt = pytz.timezone('GMT')
    race_datetime_gmt = gmt.localize(race_datetime)

    # Convert datetime to race location timezone and send
    race_info = race_classes.RaceInfo(
        name = race["raceName"],
        city = race["Circuit"]["Location"]["locality"],
        country = race["Circuit"]["Location"]["country"],
        season = race["season"],
        round = race["round"],
        raceDateTime = race_datetime_gmt.astimezone(race_timezone).strftime("%Y-%m-%d %H:%M:%S"),
        dateTimeUtc = race_datetime_gmt.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S GMT")
    )

    # Track data
    # Set default values
    track_name=map_uri = ""
    turns=laps=drs_detection_zones=drs_zones=distance=0
    track_find_payload = {
        "dataSource": os.environ.get("MONGODB_CLUSTER"),
        "database": os.environ.get("DB_NAME"),
        "collection": "tracks",
        "filter": {
            "name": race["Circuit"]["circuitName"]
      }
    }
    
    track_response = mongodb_api_find_one(track_find_payload)
    if "name" in track_response:
        track_name = track_response["name"]
        map_uri = track_response["mapUri"]
        turns = track_response["turns"]
        laps = track_response["laps"]
        distance = track_response["distance"]
        drs_detection_zones = track_response["drsDetectionZones"]
        drs_zones = track_response["drsZones"]
    # Save track data
    track = race_classes.Track(
        name = track_name,
        mapUri = map_uri,
        turns = turns,
        laps = laps,
        drsDetectionZones = drs_detection_zones,
        drsZones = drs_zones,
        distance = distance
    )
    
    # Highlights data
    highlights_uri = ""
    highlights_find_payload = {
        "dataSource": os.environ.get("MONGODB_CLUSTER"),
        "database": os.environ.get("DB_NAME"),
        "collection": "highlights",
        "filter": {
            "season": int(race["season"]),
            "round": int(race["round"])
      }
    }
    highlights_response = mongodb_api_find_one(highlights_find_payload)
    if "uri" in highlights_response:
        highlights_uri = highlights_response["uri"]
    # Save highlights data 
    highlights = race_classes.Highlights(
        uri = highlights_uri
    )  

    # Weather data
    weather_url = "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={long}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto&start_date={quali_date}&end_date={race_date}".format(
        lat=race["Circuit"]["Location"]["lat"],
        long=race["Circuit"]["Location"]["long"],
        quali_date=(datetime.strptime(race["date"], "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d"),
        race_date=race["date"]
    )
    weather_response = call_data_source(weather_url)
    quali_weather = race_classes.WeatherEntry(
        type = convert_weather_code(str(weather_response["daily"]["weathercode"][0])),
        temp = str(weather_response["daily"]["temperature_2m_min"][0]) + "°C - " + str(weather_response["daily"]["temperature_2m_max"][0]) + "°C",
    )
    race_weather = race_classes.WeatherEntry(
        type = convert_weather_code(str(weather_response["daily"]["weathercode"][1])),
        temp = str(weather_response["daily"]["temperature_2m_min"][1]) + "°C - " + str(weather_response["daily"]["temperature_2m_max"][1]) + "°C"
    )
    weather = race_classes.Weather(
        qualifying = quali_weather,
        race = race_weather
    )
    
    # Race result data
    race_results = []
    for entry in race["Results"]:
        # Handle timings after 1 lap and DNFs
        if entry["status"] != "Finished":
            if re.search("\+\d Lap[s]?", entry["status"]):
                race_time = entry["status"]
            else:
                race_time = "DNF"
        else:
            race_time = entry["Time"]["time"]

        driver_standing_entry = race_classes.ResultEntry(
            position = entry["position"],
            qualifying = entry["grid"],
            name = entry["Driver"]["givenName"] + " " + entry["Driver"]["familyName"],
            driverCode = entry["Driver"]["code"],
            time = race_time,
            points = entry["points"],
            team = entry["Constructor"]["name"],
            teamLogoUri = entry["Constructor"]["name"].replace(" ",""),
            teamLogoAlt = entry["Constructor"]["name"] + " logo",
            fastestLap = entry["FastestLap"]["Time"]["time"],
            fastestLapRank = entry["FastestLap"]["rank"]
        )
        race_results.append(driver_standing_entry)

    # Drivers standings data
    driver_standing_response = call_data_source("http://ergast.com/api/f1/current/driverStandings.json")
    if driver_standing_response == {}:
        raise HTTPException(status_code=503, detail="Upstream error")
    driver_standing = []
    for entry in driver_standing_response["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]:
        driver_standing_entry = race_classes.DriverStandingEntry(
            position = entry["position"],
            name = entry["Driver"]["givenName"] + " " + entry["Driver"]["familyName"],
            driverCode = entry["Driver"]["code"],
            points = entry["points"],
            team = entry["Constructors"][0]["name"],
            teamLogoUri = entry["Constructors"][0]["name"].replace(" ",""),
            teamLogoAlt = entry["Constructors"][0]["name"] + " logo"
        )
        driver_standing.append(driver_standing_entry)

    # Constructors standings data
    constructor_standing_response = call_data_source("http://ergast.com/api/f1/current/constructorStandings.json")
    if constructor_standing_response == {}:
        raise HTTPException(status_code=503, detail="Upstream error")
    constructor_standing = []
    for entry in constructor_standing_response["MRData"]["StandingsTable"]["StandingsLists"][0]["ConstructorStandings"]:
        constructor_standing_entry = race_classes.ConstructorStandingEntry(
            position = entry["position"],
            name = entry["Constructor"]["name"],
            points = entry["points"],
            teamLogoUri = entry["Constructor"]["name"].replace(" ",""),
            teamLogoAlt = entry["Constructor"]["name"] + " logo"
        )
        constructor_standing.append(constructor_standing_entry)

    # Next race data    
    url = "http://ergast.com/api/f1/{year}/{round}.json".format(year=race_info.season, round=race_info.round + 1)
    next_race_response = call_data_source(url)
    if next_race_response == {}:
        raise HTTPException(status_code=503, detail="Upstream error")
    next_race_data = next_race_response["MRData"]["RaceTable"]["Races"][0]
    
    # Find race timezone
    timezone = tz.tzNameAt(float(next_race_data["Circuit"]["Location"]["lat"]),float(next_race_data["Circuit"]["Location"]["long"]))
    next_race_timezone = pytz.timezone(timezone)
    # Create datetime object 
    next_race_datetime_str = str(next_race_data["date"]) + " " + str(next_race_data["time"])
    next_race_datetime = datetime.strptime(next_race_datetime_str, "%Y-%m-%d %H:%M:%SZ")
    # Set datetime to greenwich time
    gmt = pytz.timezone('GMT')
    next_race_datetime_gmt = gmt.localize(next_race_datetime)
    
    next_race = race_classes.NextRace(
        name = next_race_data["raceName"],
        country = next_race_data["Circuit"]["Location"]["country"],
        track = next_race_data["Circuit"]["circuitName"],
        raceDateTime = next_race_datetime_gmt.astimezone(next_race_timezone).strftime("%Y-%m-%d %H:%M:%S"),
        dateTimeUtc = next_race_datetime_gmt.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S GMT"),
    )

    race_data = race_classes.RaceData(
        race = race_info,
        track = track,
        weather = weather,
        highlights = highlights,
        results = race_results,
        driversStandings = driver_standing,
        constructorsStandings = constructor_standing,
        nextRace = next_race
    )

    cache.update({"race_data": race_data})
    expiry = datetime.now() + timedelta(minutes=15)
    cache.update({"expiry": expiry})
    # print(cache)
    # print(race_data.json())
    
    # Store all race data
    race_insert_payload = {
        "dataSource": os.environ.get("MONGODB_CLUSTER"),
        "database": os.environ.get("DB_NAME"),
        "collection": "race",
        "document": race_data.dict()
    }
    insert_response = mongodb_api_insert_one(race_insert_payload)
    if "insertedId" in insert_response:
        print("saved successfully")
    
    return race_data

def call_data_source(api_url):
    response = requests.get(api_url)
    # print("response" + response)
    if response.status_code != 200:
        return {}
    return response.json()
