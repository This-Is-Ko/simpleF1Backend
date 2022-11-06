from schemas import race_classes
import requests
import requests_cache
from fastapi import HTTPException
import re
from datetime import datetime, timedelta
import csv
from pathlib import Path
from tzwhere import tzwhere
import pytz
import pymongo

from .weather_code_converter import convert_weather_code

from database import database

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
            if cache["database_status"] == "success":
                return cache["race_data"]
        else:
            cache = {}

    race_response = call_data_source("http://ergast.com/api/f1/current/last/results.json")
    if race_response == {}:
        raise HTTPException(status_code=503, detail="Upstream error")
    race = race_response["MRData"]["RaceTable"]["Races"][0]

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

    # Track and highlight data
    # Set default values
    track_name=map_uri = ""
    turns=laps=drs_detection_zones=drs_zones=distance=0
    highlights_uri = ""

    try:
        with pymongo.timeout(10):
            db = database.get_mongodb_client()
            # Retrieve track data from database
            track_entry = db["tracks"].find_one({"name": race["Circuit"]["circuitName"]})
            if "name" in track_entry:
                track_name = track_entry["name"]
                map_uri = track_entry["mapUri"]
                turns = track_entry["turns"]
                laps = track_entry["laps"]
                distance = track_entry["distance"]
                drs_detection_zones = track_entry["drsDetectionZones"]
                drs_zones = track_entry["drsZones"]
            
            # Retrieve highlights data from database
            highlights_entry = db["highlights"].find_one({"year": int(race["season"]), "round": int(race["round"])})
            if "uri" in highlights_entry:
                highlights_uri = highlights_entry["uri"]
    
    except pymongo.errors.PyMongoError as exc:
        if exc.timeout:
            print(f"Database call timed out: {exc!r}")
        else:
            print(f"Database call failed with non-timeout error: {exc!r}")
    
    # Save track and highlight data
    track = race_classes.Track(
        name = track_name,
        mapUri = map_uri,
        turns = turns,
        laps = laps,
        drsDetectionZones = drs_detection_zones,
        drsZones = drs_zones,
        distance = distance
    )
    
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

        # Store only fastest lap driver
        # fastest_lap_rank = ""
        # if entry["FastestLap"]["rank"] == "1":
        #     fastest_lap = entry["FastestLap"]["Time"]["time"]

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
    if map_uri == "":
        cache.update({"database_status": "error"})
    else:
        cache.update({"database_status": "success"})
    expiry = datetime.now() + timedelta(minutes=15)
    cache.update({"expiry": expiry})
    # print(cache)
    return race_data

def call_data_source(api_url):
    response = requests.get(api_url)
    # print("response" + response)
    if response.status_code != 200:
        return {}
    return response.json()