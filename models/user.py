from flask import redirect, url_for
from config import users_collection
from werkzeug.security import generate_password_hash, check_password_hash


def add_user(name, email, password, role, otp=None):                                                                           #user add and hash password                                
    hashed_password = generate_password_hash(password)
    
    users_collection.insert_one({
        "name": name, 
        "email": email, 
        "password": hashed_password, 
        "role": role,
        "is_verified": False,
        "otp": otp
    })

def set_verified(email):
    users_collection.update_one({"email": email}, {"$set": {"is_verified": True}, "$unset": {"otp": ""}})

def update_otp(email, otp):
    users_collection.update_one({"email": email}, {"$set": {"otp": otp}})

def verify_user(email, password):  # find user and match password
    user = users_collection.find_one({"email": email})
    if user and check_password_hash(user["password"], password):
        return user
    return None

def get_user_by_email(email):
    return users_collection.find_one({"email": email})







