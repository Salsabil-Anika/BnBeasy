from flask import Flask, render_template, session, redirect, url_for, request
import os
from config import listings_collection

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static/uploads')

# Import blueprints from the routes package
from routes import (
    auth_bp, host_bp, traveller_bp, reviews_bp,
    host_community_bp, traveller_community_bp
)

# Import route modules to register decorators
import routes.auth_routes
import routes.host_routes
import routes.traveller_routes
import routes.traveler_profile_routes
import routes.reviews_routes
import routes.host_community_routes
import routes.traveller_community_routes
import routes.listings_routes
import routes.bookings_routes

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(host_bp)
app.register_blueprint(traveller_bp)
app.register_blueprint(reviews_bp)
app.register_blueprint(host_community_bp)
app.register_blueprint(traveller_community_bp)

@app.route("/")
def index():
    if "user_id" in session and session.get("role") == "host":
        return redirect(url_for("host.dashboard"))
    return redirect(url_for("traveller.home"))

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    return render_template("dashboard.html", email=session["user"])

if __name__ == "__main__":
    app.run(debug=True)
