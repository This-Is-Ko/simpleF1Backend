from schemas import race_classes
import requests
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import List
import requests_cache

def get_latest_race_data():
    requests_cache.install_cache("race_data_responses", allowable_methods=('GET'), allowable_codes=(200), urls_expire_after={"http://ergast.com/api/f1/": 36000, })

    race_response = call_data_source("http://ergast.com/api/f1/current/last/results.json")
    race = race_response["MRData"]["RaceTable"]["Races"][0]

    race_info = race_classes.RaceInfo(
        name = race["raceName"],
        city = race["Circuit"]["Location"]["locality"],
        country = race["Circuit"]["Location"]["country"],
        season = race["season"],
        round = race["round"],
        date = race["date"],
        time = race["time"]
    )

    # TODO Need to add track data
    track = race_classes.Track(
        name = race["Circuit"]["circuitName"],
        map = "",
        trackDescription = "",
        turns = 1,
        laps = 1,
        distance = 1
    )

    # TODO Need to add weather data
    weather = race_classes.Weather(
        qualifying = "",
        race = ""
    )

    highlights = race_classes.Highlights(
        link = ""
    )
    
    # Map race result data
    race_results = []
    for entry in race["Results"]:

        # Store only fastest lap driver
        fastest_lap = ""
        if entry["FastestLap"]["rank"] == "1":
            fastest_lap = entry["FastestLap"]["Time"]["time"]

        if entry["status"] != "Finished":
            time = entry["status"]
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
            teamLogoUri = entry["Constructor"]["url"],
            fastestLap = fastest_lap
        )
        race_results.append(driver_standing_entry)

    # Map drivers standings data
    driver_standing_response = call_data_source("http://ergast.com/api/f1/current/driverStandings.json")
    driver_standing = []
    for entry in driver_standing_response["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]:
        driver_standing_entry = race_classes.DriverStandingEntry(
            position = entry["position"],
            name = entry["Driver"]["givenName"] + " " + entry["Driver"]["familyName"],
            driverCode = entry["Driver"]["code"],
            points = entry["points"],
            team = entry["Constructors"][0]["name"],
            teamLogoUri = entry["Constructors"][0]["url"]
        )
        driver_standing.append(driver_standing_entry)

    # Map constructors standings data
    constructor_standing_response = call_data_source("http://ergast.com/api/f1/current/constructorStandings.json")
    constructor_standing = []
    for entry in constructor_standing_response["MRData"]["StandingsTable"]["StandingsLists"][0]["ConstructorStandings"]:
        constructor_standing_entry = race_classes.ConstructorStandingEntry(
            position = entry["position"],
            name = entry["Constructor"]["name"],
            points = entry["points"],
            teamLogoUri = entry["Constructor"]["url"]
        )
        constructor_standing.append(constructor_standing_entry)

    # Map info on next race
    # TODO trackDescription
    url = "http://ergast.com/api/f1/{year}/{round}.json".format(year=race_info.season, round=race_info.round + 1)
    next_race_response = call_data_source(url)
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

    print(race_data)
    return race_data

def call_data_source(api_url):
    response = requests.get(api_url)
    return response.json()