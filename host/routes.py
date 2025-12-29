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
    
    user_id = session["user_id"]
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    
    # Use the central get_spaces_by_host function
    # It queries the 'spaces' collection, which is where add_listing and traveller view are looking
    from models.space import get_spaces_by_host
    listings = get_spaces_by_host(user_id)
    listing_count = len(listings)
    
    # Ensure listings have 'title' and 'image' keys for the template
    # The template expects 'title', 'city', 'price', 'image'
    # The space model uses 'space_title', 'location_city', 'price_per_night', 'photos'
    # We map them for compatibility
    for l in listings:
        l['title'] = l.get('space_title', 'Untitled')
        l['city'] = l.get('location_city', '')
        l['price'] = l.get('price_per_night', 0)
        photos = l.get('photos', [])
        l['image'] = photos[0] if photos else ''
        # Fix image path if it lists 'uploads/filename' vs just 'filename' for template
        if l['image'] and l['image'].startswith('uploads/'):
            l['image'] = l['image'].replace('uploads/', '')

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
        except Exception as e:
            print(f"Error creating space: {e}")
            pass # Or handle error appropriately

        return redirect(url_for("host.dashboard"))

    return render_template("host/add_listing.html")


@host_bp.route("/delete_listing/<space_id>", methods=["POST"])
def delete_listing_route(space_id):
    if "user_id" not in session or session.get("role") != "host":
        return redirect(url_for("auth.login"))

    from models.space import get_space_by_id, delete_space
    
    # Verify ownership
    space = get_space_by_id(space_id)
    if not space:
        return redirect(url_for("host.dashboard"))
    
    # Check if the current user is the owner of the space
    owner_id = str(space.get('host_id'))
    current_user_id = str(session.get('user_id'))
    
    if owner_id != current_user_id:
        return redirect(url_for("host.dashboard"))

    delete_space(space_id)
    return redirect(url_for("host.dashboard"))


@host_bp.route("/edit_listing/<space_id>", methods=["GET", "POST"])
def edit_listing_route(space_id):
    if "user_id" not in session or session.get("role") != "host":
        return redirect(url_for("auth.login"))

    from models.space import get_space_by_id, update_space
    
    # Verify ownership
    space = get_space_by_id(space_id)
    if not space:
        return redirect(url_for("host.dashboard"))
    
    owner_id = str(space.get('host_id'))
    current_user_id = str(session.get('user_id'))
    
    if owner_id != current_user_id:
        return redirect(url_for("host.dashboard"))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        price = request.form.get("price")
        city = request.form.get("city")
        location = request.form.get("location")
        # For simplicity, we'll only update text fields and latitude/longitude if provided
        # Handling image update is more complex (optional upload), valid for v2
        
        update_data = {
            "space_title": title,
            "description": description,
            "price_per_night": float(price) if price else 0,
            "location_city": city,
            "location": location,
        }
        
        # Optional: Lat/Lng
        lat = request.form.get("latitude")
        lng = request.form.get("longitude")
        if lat: update_data["latitude"] = float(lat)
        if lng: update_data["longitude"] = float(lng)
        
        amenities = request.form.getlist('amenities')
        if amenities:
            update_data["amenities"] = amenities
            
        # Handle Image Update (Optional)
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                # Update photo list (replacing old one for simplicity in this swift edit)
                update_data["photos"] = [f"uploads/{filename}"]

        update_space(space_id, update_data)
        return redirect(url_for("host.dashboard"))

    # GET: Render form with existing data
    # Flatten structure for template if needed, but template can access space dict directly
    return render_template("host/edit_listing.html", space=space)
