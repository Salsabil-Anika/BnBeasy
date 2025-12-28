from config import db
from bson.objectid import ObjectId

bookings_collection = db['bookings']

def add_booking(user_id, listing_id, start_date, end_date):
    result = bookings_collection.insert_one({
        "user_id": ObjectId(user_id),
        "listing_id": ObjectId(listing_id),
        "start_date": start_date,
        "end_date": end_date,
        "status": "confirmed"
    })
    return result.inserted_id

def get_user_bookings(user_id):
    return list(bookings_collection.find({"user_id": ObjectId(user_id)}))

def cancel_booking(booking_id):
    bookings_collection.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "cancelled"}}
    )
