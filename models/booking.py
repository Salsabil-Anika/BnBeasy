from datetime import datetime
from bson.objectid import ObjectId
from config import db

bookings_collection = db.bookings

def create_booking(booking_data):
    booking_data.setdefault('created_at', datetime.utcnow())
    result = bookings_collection.insert_one(booking_data)
    return str(result.inserted_id)

def get_bookings_by_user(user_id):
    return list(bookings_collection.find({'user_id': user_id}))

def get_bookings_by_host(host_id):
    return list(bookings_collection.find({'host_id': host_id}))

def get_booking_by_id(booking_id):
    try:
        return bookings_collection.find_one({'_id': ObjectId(booking_id)})
    except Exception:
        return None

def cancel_booking(booking_id):
    try:
        result = bookings_collection.delete_one({'_id': ObjectId(booking_id)})
        return result.deleted_count > 0
    except Exception:
        return False
