from flask import Blueprint

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
host_bp = Blueprint("host", __name__, url_prefix="/host")
traveller_bp = Blueprint("traveller", __name__, url_prefix="/traveller")
reviews_bp = Blueprint('reviews', __name__)
host_community_bp = Blueprint("host_community", __name__, url_prefix="/community")
traveller_community_bp = Blueprint("traveller_community", __name__, url_prefix="/community")
