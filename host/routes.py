from flask import render_template, request, session, redirect, url_for, current_app
from . import host_bp
from models.user import users_collection

from config import listings_collection
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import os
from models.space import (
    create_space as create_space_in_db, 
    get_space_by_id, 
    update_space, 
    filter_spaces,
    get_all_spaces,
    get_popular_spaces_in_location,
    delete_space
)

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
        longitude = request.form.get("longitude")
        latitude = request.form.get("latitude")

        if 'image' not in request.files:
            return redirect(request.url)
        
        file = request.files['image']
        image_filename = None
        
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

        amenities = request.form.getlist('amenities')

        # assemble space document compatible with models.space.create_space
        space_data = {
            'host_id': session.get('user_id'),
            'space_title': title,
            'description': description,
            'price_per_night': float(price) if price else 0,
            'location_city': city,
            'location': location,
            'photos': [f"uploads/{image_filename}"] if image_filename else [],
            'amenities': amenities,
            'latitude': float(latitude) if latitude else None,
            'longitude': float(longitude) if longitude else None,
            'space_type': request.form.get('space_type', 'Private Room'),
            'has_coworking_space': 'has_coworking_space' in request.form
        }

        try:
            create_space_in_db(space_data)
        except Exception:
            # fallback: insert directly into listings_collection if models call fails
            listings_collection.insert_one({
                'host_id': session.get('user_id'),
                'title': title,
                'price': float(price) if price else 0,
                'city': city,
                'location': location,
                'description': description,
                'image': image_filename,
                'amenities': amenities,
            })

        return redirect(url_for("host.dashboard"))

    return render_template("host/add_listing.html")

