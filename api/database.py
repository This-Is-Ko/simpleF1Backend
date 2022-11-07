import requests
import os
from dotenv import load_dotenv
load_dotenv()

MONGODB_API_URI = os.environ.get("MONGODB_API_URI")
MONGODB_API_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Request-Headers': '*',
    "api-key": os.environ.get("MONGODB_API_KEY")
}

def mongodb_api_find_one(payload):
    response = requests.post(MONGODB_API_URI + "/action/find", headers=MONGODB_API_HEADERS, json=payload)
    # print(response.json())
    if response.status_code != 200:
        return {}
    return response.json()["documents"][0]

def mongodb_api_insert_one(payload):
    response = requests.post(MONGODB_API_URI + "/action/insertOne", headers=MONGODB_API_HEADERS, json=payload)
    # print(response.json())
    if response.status_code != 200:
        return {}
    return response.json()