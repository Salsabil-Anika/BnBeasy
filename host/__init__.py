from flask import Blueprint

host_bp = Blueprint("host", __name__, url_prefix="/host")

from . import routes
