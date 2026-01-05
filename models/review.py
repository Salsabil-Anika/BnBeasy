from config import db
from datetime import datetime
from bson.objectid import ObjectId

# Indexing can be done manually in Atlas or lazily
reviews_collection = db.reviews
# try:
#     reviews_collection.create_index("space_id")
# except:
#     pass

def create_review(review_data):
    """Creates a new review."""
    review_data["created_at"] = datetime.utcnow()
    return reviews_collection.insert_one(review_data)

def get_reviews_by_space(space_id):
    """Fetches all reviews for a specific space."""
    return list(reviews_collection.find({"space_id": space_id}).sort("created_at", -1))

def get_reviews_by_user(user_id):
    """Fetches all reviews written by a specific user."""
    return list(reviews_collection.find({"user_id": user_id}).sort("created_at", -1))

def delete_review(review_id):
    """Deletes a review by its ID."""
    return reviews_collection.delete_one({"_id": ObjectId(review_id)})
