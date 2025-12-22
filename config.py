from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27017"
client = MongoClient(MONGO_URI)

db = client["Bnbeasy"]
users_collection = db["users"]
listings_collection = db["listings"]

SECRET_KEY = "supersecretkey123"
