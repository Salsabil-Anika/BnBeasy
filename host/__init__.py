from flask import Blueprint

host_bp = Blueprint("host", __name__, url_prefix="/host", template_folder='../templates/host')

from . import routes
