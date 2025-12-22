from flask import Blueprint

review_bp = Blueprint("review", __name__)

@review_bp.get("/")
def review_home():
    return "Review Page working!"
