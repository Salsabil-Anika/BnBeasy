from flask import render_template, request, session, redirect, url_for, current_app
from . import host_bp
from models.user import users_collection
from models.listings import add_listing
from config import listings_collection
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import os


@host_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session or session.get("role") != "host":
        return redirect(url_for("auth.login"))
    
    user = users_collection.find_one({"_id": ObjectId(session["user_id"])})
    listing_count = listings_collection.count_documents({"host_id": session["user_id"]})
    listings = list(listings_collection.find({"host_id": session["user_id"]}))
    return render_template("host/dashboard.html", user=user, listing_count=listing_count, listings=listings)
    
@host_bp.route("/profile", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session or session.get("role") != "host":
        return redirect(url_for("auth.login"))

    user = users_collection.find_one({"_id": ObjectId(session["user_id"])})

    if request.method == "POST":
        name = request.form.get("name")
        bio = request.form.get("bio")
        location = request.form.get("location")
        
        update_data = {"name": name, "bio": bio, "location": location}

        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename != '':
                filename = secure_filename(f"profile_{session['user_id']}_{file.filename}")
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                update_data["profile_image"] = filename

        users_collection.update_one(
            {"_id": ObjectId(session["user_id"])},
            {"$set": update_data}
        )

        return redirect(url_for("host.dashboard"))

    return render_template("host/profile.html", user=user)

@host_bp.route("/add_listing", methods=["GET", "POST"])
def add_listing_route():
    if "user_id" not in session or session.get("role") != "host":
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        title = request.form.get("title")
        price = request.form.get("price")
        city = request.form.get("city")
        location = request.form.get("location")
        description = request.form.get("description")

        if 'image' not in request.files:
            return redirect(request.url)
        
        file = request.files['image']
        image_filename = None
        
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

        amenities = request.form.getlist('amenities')

        add_listing(session["user_id"], title, price, city, location, description, image_filename, amenities)

        return redirect(url_for("host.dashboard"))

    return render_template("host/add_listing.html")

