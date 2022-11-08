import requests
import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import HTTPException

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
        raise HTTPException(status_code=500, detail="Upstream error")
    if len(response.json()["documents"]) != 1:
         raise HTTPException(status_code=403, detail="Race not found")
    return response.json()["documents"][0]

def mongodb_api_is_present(payload):
    response = requests.post(MONGODB_API_URI + "/action/find", headers=MONGODB_API_HEADERS, json=payload)
    # print(response.json())
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Upstream error")
    if len(response.json()["documents"]) == 0:
        return False
    else:
        return True

def mongodb_api_insert_one(payload):
    response = requests.post(MONGODB_API_URI + "/action/insertOne", headers=MONGODB_API_HEADERS, json=payload)
    if response.status_code != 201:
        raise HTTPException(status_code=500, detail="Upstream error")
    return response.json()