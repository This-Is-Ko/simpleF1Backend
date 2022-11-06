from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()

mongodb_client = MongoClient(os.environ.get("ATLAS_URI"))
db = mongodb_client[os.environ.get("DB_NAME")]

def get_mongodb_client():
    return db

def shutdown_mongodb_client():
    mongodb_client.close()