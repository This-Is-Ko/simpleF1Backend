import requests
from fastapi import HTTPException

def call_data_source(api_url):
    response = requests.get(api_url)
    # print("response" + response)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Upstream error")
    return response.json()
