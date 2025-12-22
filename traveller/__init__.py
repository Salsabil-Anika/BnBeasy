from flask import Blueprint

traveller_bp = Blueprint("traveller", __name__, url_prefix="/traveller")

from . import routes
