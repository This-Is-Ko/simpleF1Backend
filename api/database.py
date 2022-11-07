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
    response = requests.post(MONGODB_API_URI, headers=MONGODB_API_HEADERS, json=payload)
    # print("response" + response)
    if response.status_code != 200:
        return {}
    return response.json()["documents"][0]