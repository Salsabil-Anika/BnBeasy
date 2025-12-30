from flask import Blueprint

traveller_bp = Blueprint("traveller", __name__, url_prefix="/traveller", template_folder='../templates/traveller')
 
from . import routes
from . import traveler_profile_routes

