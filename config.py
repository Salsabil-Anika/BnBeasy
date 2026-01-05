from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

def get_db():
    # This is called inside workers after forking to avoid "Opened before fork" warnings
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return client["Bnbeasy"]

class CollectionProxy:
    def __init__(self, collection_name):
        self.name = collection_name
        self._collection = None

    def _get_col(self):
        if self._collection is None:
            self._collection = get_db()[self.name]
        return self._collection

    def __getattr__(self, attr):
        # Forward everything (find_one, insert_one, etc) to the real collection
        return getattr(self._get_col(), attr)

    def __getitem__(self, key):
        # Handle dict-like access if needed
        return self._get_col()[key]

class DatabaseProxy:
    def __getattr__(self, collection_name):
        return CollectionProxy(collection_name)
    
    def __getitem__(self, collection_name):
        return CollectionProxy(collection_name)

# Central database proxy
db = DatabaseProxy()

# Specific collection proxies for direct imports in models
users_collection = CollectionProxy("users")
listings_collection = CollectionProxy("listings")
bookings_collection = CollectionProxy("bookings")

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")
