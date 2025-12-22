# models/community.py

import os
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from datetime import datetime

# --- MongoDB Connect ---
try:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/nomadnest")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client.get_database("nomadnest")
    community_collection = db.community_threads
    community_collection.create_index([("created_at", DESCENDING)])
    print("Community Model: MongoDB connected successfully.")
except Exception as e:
    print(f"Community Model: Error connecting to MongoDB: {e}")

# --- CRUD helpers ---

def create_thread(title, content, user_id, role):
    thread = {
        "title": title,
        "content": content,
        "user_id": str(user_id),
        "role": role,   # "host" or "traveler"
        "created_at": datetime.utcnow(),
        "comments": []
    }
    return community_collection.insert_one(thread)

def get_all_threads():
    return list(community_collection.find().sort("created_at", DESCENDING))

def get_thread(thread_id):
    try:
        return community_collection.find_one({"_id": ObjectId(thread_id)})
    except Exception:
        return None

def add_comment(thread_id, comment, user_id, role):
    new_comment = {
        "comment": comment,
        "user_id": str(user_id),
        "role": role,
        "created_at": datetime.utcnow()
    }
    return community_collection.update_one(
        {"_id": ObjectId(thread_id)},
        {"$push": {"comments": new_comment}}
    )

def delete_thread(thread_id):
    return community_collection.delete_one({"_id": ObjectId(thread_id)})

def delete_comment(thread_id, comment_id, user_id):
    """
    Deletes a comment from a thread if the user is the author.
    """
    return community_collection.update_one(
        {"_id": ObjectId(thread_id)},
        {"$pull": {"comments": {"_id": ObjectId(comment_id), "user_id": user_id}}}
    )
