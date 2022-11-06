from pymongo import MongoClient
from dotenv import dotenv_values
config = dotenv_values(".env")

mongodb_client = MongoClient(config["ATLAS_URI"])
db = mongodb_client[config["DB_NAME"]]

def get_mongodb_client():
    return db

def shutdown_mongodb_client():
    mongodb_client.close()