from pymongo import MongoClient

import os
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
# Added 5-second timeout so the app fails fast instead of hanging if the DB is unreachable
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

db = client["Bnbeasy"]
users_collection = db["users"]
listings_collection = db["listings"]
bookings_collection = db["bookings"]

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")
