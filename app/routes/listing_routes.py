from flask import Blueprint

listing_bp = Blueprint("listing", __name__)

@listing_bp.get("/")
def listing_home():
    return "Listing Page working!"
