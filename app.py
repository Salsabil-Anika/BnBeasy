from flask import Flask, render_template, session, redirect, url_for, request
from auth import auth_bp


import os
from config import listings_collection
from models.space import filter_spaces, get_all_spaces

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static/uploads')

from host import host_bp
from traveller import traveller_bp

from traveller.space import space_bp

# community blueprints (host and traveller)
from host.community import community_bp as host_community_bp
from traveller.community import community_bp as traveller_community_bp

app.register_blueprint(auth_bp)
app.register_blueprint(host_bp)
app.register_blueprint(traveller_bp)


# register community blueprints
app.register_blueprint(host_community_bp)
app.register_blueprint(traveller_community_bp)
app.register_blueprint(space_bp)

@app.route("/")
def index():
    if "user_id" in session and session.get("role") == "host":
        return redirect(url_for("host.dashboard"))

    # Use the central space model filters so we always read from the same collection
    filters = {}
    city = request.args.get("city")
    if city:
        filters['location'] = city

    price = request.args.get("price")
    if price:
        filters['max_price'] = price

    amenities = request.args.getlist("amenities")
    if amenities:
        filters['amenities'] = amenities

    try:
        spaces = filter_spaces(filters)
        # normalize shape expected by traveller/home.html
        normalized = []
        for s in spaces:
            photo = None
            photos = s.get('photos') or []
            if photos:
                first = photos[0]
                if isinstance(first, str) and ('/' in first):
                    photo = os.path.basename(first)
                else:
                    photo = first

            normalized.append({
                '_id': str(s.get('_id')),
                'title': s.get('space_title') or s.get('title') or s.get('name'),
                'image': photo,
                'price': s.get('price_per_night') or s.get('price'),
                'city': s.get('location_city') or s.get('city'),
                'location': s.get('location') or s.get('location_city'),
                'amenities': s.get('amenities', [])
            })
    except Exception:
        normalized = []

    return render_template("traveller/home.html", listings=normalized)

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    return render_template("dashboard.html", email=session["user"])

if __name__ == "__main__":
    app.run(debug=True)
