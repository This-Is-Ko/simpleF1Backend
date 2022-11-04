from schemas import race_classes
import requests
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import List
import requests_cache
from fastapi import FastAPI, HTTPException
import re
from datetime import datetime, timedelta
import csv
from pathlib import Path
from unidecode import unidecode
from tzwhere import tzwhere
import pytz

from .weather_code_converter import convert_weather_code

TRACK_INFORMATION = Path(__file__).parent /"./../data/tracks.csv"

def get_latest_race_data():
    requests_cache.install_cache("race_data_responses", allowable_methods=('GET'), allowable_codes=(200,), urls_expire_after={"http://ergast.com/api/f1/": 36000, })

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

    # Track data
    # Set default values
    map_uri=description = ""
    turns=laps=drs_detection_zones=drs_zones=distance=0
    
    # Retrieve track data from local csv
    track_csv = csv.reader(open(TRACK_INFORMATION, "r"))
    for track in track_csv:
        if track[0] == unidecode(race["Circuit"]["circuitName"]):
            map_uri = track[1]
            turns = track[2]
            laps = track[3]
            distance = track[4]
            drs_detection_zones = track[5]
            drs_zones = track[6]
            description = track[7]
            
    track = race_classes.Track(
        name = race["Circuit"]["circuitName"],
        mapUri = map_uri,
        description = description,
        turns = turns,
        laps = laps,
        drsDetectionZones = drs_detection_zones,
        drsZones = drs_zones,
        distance = distance
    )

    # Weather data
    weather_url = "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={long}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto&start_date={quali_date}&end_date={race_date}".format(
        lat=race["Circuit"]["Location"]["lat"],
        long=race["Circuit"]["Location"]["long"],
        quali_date=(datetime.strptime(race["date"], "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d"),
        race_date=race["date"]
    )
    weather_response = call_data_source(weather_url)
    weather = race_classes.Weather(
        qualifying = convert_weather_code(str(weather_response["daily"]["weathercode"][0])),
        qualifyingTemp = str(weather_response["daily"]["temperature_2m_min"][0]) + "°C - " + str(weather_response["daily"]["temperature_2m_max"][0]) + "°C",
        race = convert_weather_code(str(weather_response["daily"]["weathercode"][1])),
        raceTemp = str(weather_response["daily"]["temperature_2m_min"][0]) + "°C - " + str(weather_response["daily"]["temperature_2m_max"][0]) + "°C"
    )

    highlights = race_classes.Highlights(
        link = ""
    )
    
    # Race result data
    race_results = []
    for entry in race["Results"]:

        # Store only fastest lap driver
        fastest_lap = ""
        if entry["FastestLap"]["rank"] == "1":
            fastest_lap = entry["FastestLap"]["Time"]["time"]

        # Handle timings after 1 lap and DNFs
        if entry["status"] != "Finished":
            if re.search("\+\d Lap[s]?", entry["status"]):
                time = entry["status"]
            else:
                time = "DNF"
        else:
            time = entry["Time"]["time"]

        driver_standing_entry = race_classes.ResultEntry(
            position = entry["position"],
            qualifying = entry["grid"],
            name = entry["Driver"]["givenName"] + " " + entry["Driver"]["familyName"],
            driverCode = entry["Driver"]["code"],
            time = time,
            points = entry["points"],
            team = entry["Constructor"]["name"],
            teamLogoUri = entry["Constructor"]["name"].replace(" ",""),
            teamLogoAlt = entry["Constructor"]["name"] + " logo",
            fastestLap = fastest_lap
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
    # TODO trackDescription
    url = "http://ergast.com/api/f1/{year}/{round}.json".format(year=race_info.season, round=race_info.round + 1)
    next_race_response = call_data_source(url)
    if next_race_response == {}:
        raise HTTPException(status_code=503, detail="Upstream error")
    next_race_data = next_race_response["MRData"]["RaceTable"]["Races"][0]
    next_race = race_classes.NextRace(
        name = next_race_data["raceName"],
        country = next_race_data["Circuit"]["Location"]["country"],
        track = next_race_data["Circuit"]["circuitName"],
        date = next_race_data["date"],
        time = next_race_data["time"],
        trackDescription = ""
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

    return race_data

def call_data_source(api_url):
    response = requests.get(api_url)
    # print("response" + response)
    if response.status_code != 200:
        return {}
    return response.json()