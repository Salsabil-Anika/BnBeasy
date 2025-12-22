# models/traveler_profile.py
# Ei file ta traveler er profile, emergency contact, ebong booking history manage kore.

from datetime import datetime
from bson.objectid import ObjectId
from config import users_collection


def get_user_profile(user_obj_id):
    """
    User er unique MongoDB _id diye tar shob profile data database theke fetch kore.
    """
    # CORRECTED: Query by '_id' and convert the string from the session to an ObjectId
    return users_collection.find_one({"_id": ObjectId(user_obj_id)})


def update_traveler_profile_info(user_obj_id, data, new_profile_pic_path=None):
    """
    Traveler profile page theke je field gulo update kora hoy, shegulo database e save kore.
    """
    # Je je field update kora hobe, shegular jonno ekta dictionary toiri kora hocche.
    update_data = {
        'first_name': data.get('first_name'),
        'last_name': data.get('last_name'),
        'bio': data.get('bio'),
        'max_budget': int(data.get('max_budget', 1000)),
        'min_wifi_speed': int(data.get('min_wifi_speed', 25)),
        'looking_for': data.get('looking_for', '')
    }

    # Jodi notun profile picture upload kora hoy, tahole shetar path add kora hobe.
    if new_profile_pic_path:
        update_data['profile_picture_url'] = new_profile_pic_path

    # CORRECTED: Query by '_id' to update the correct user document.
    users_collection.update_one(
        {'_id': ObjectId(user_obj_id)},
        {'$set': update_data}
    )

    # Change confirm korar jonno updated profile ta abar fetch kore return kora hocche.
    return get_user_profile(user_obj_id)

def get_emergency_contacts(user_obj_id):
    """
    Ekjon user er shob emergency contact er list fetch kore.
    """
    # CORRECTED: Query by '_id'
    user = users_collection.find_one({"_id": ObjectId(user_obj_id)})
    # Jodi user thake ebong tar emergency_contacts field thake, sheta return korbe, noile empty list.
    return user.get('emergency_contacts', []) if user else []

def update_emergency_contacts(user_obj_id, contacts):
    """
    Ekjon user er emergency contact list update kore.
    """
    # CORRECTED: Query by '_id'
    users_collection.update_one(
        {'_id': ObjectId(user_obj_id)},
        # Puro list take notun list diye replace kora hocche.
        {'$set': {'emergency_contacts': contacts}}
    )
