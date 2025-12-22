from flask import Flask, render_template, session, redirect, url_for, request
from auth import auth_bp

import os
from config import listings_collection

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static/uploads')

from host import host_bp
from traveller import traveller_bp
from traveller.traveler_profile_routes import traveler_profiles_bp

# community blueprints (host and traveller)
from host.community import community_bp as host_community_bp
from traveller.community import community_bp as traveller_community_bp

app.register_blueprint(auth_bp)
app.register_blueprint(host_bp)
app.register_blueprint(traveller_bp)
app.register_blueprint(traveler_profiles_bp)

# register community blueprints
app.register_blueprint(host_community_bp)
app.register_blueprint(traveller_community_bp)

@app.route("/")
def index():
    if "user_id" in session and session.get("role") == "host":
        return redirect(url_for("host.dashboard"))

    query = {}
    
    city = request.args.get("city")
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
        
    price = request.args.get("price")
    if price:
        try:
            query["price"] = {"$lte": int(price)}
        except ValueError:
            pass
            
    amenities = request.args.getlist("amenities")
    if amenities:
        query["amenities"] = {"$all": amenities}

    listings = list(listings_collection.find(query))
    return render_template("traveller/home.html", listings=listings)

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    return render_template("dashboard.html", email=session["user"])

if __name__ == "__main__":
    app.run(debug=True)
