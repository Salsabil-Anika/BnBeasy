from flask import render_template, request, session, redirect, url_for, current_app
from . import host_bp
from models.user import users_collection

from config import listings_collection
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import os


@host_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session or session.get("role") != "host":
        return redirect(url_for("auth.login"))
    
    user_id = session["user_id"]
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    
    # Use the listings model as requested by user
    from models.listings import get_listings_by_host
    listings = get_listings_by_host(user_id)
    listing_count = len(listings)
    
    # Ensure listings have 'title' and 'image' keys for the template
    # The template expects 'title', 'city', 'price', 'image'
    # The listings model (via create_listing_from_args) uses 'space_title', 'location_city', 'price_per_night', 'photos'
    # We map them for compatibility
    for l in listings:
        l['title'] = l.get('space_title', l.get('title', 'Untitled'))
        l['city'] = l.get('location_city', l.get('city', ''))
        l['price'] = l.get('price_per_night', l.get('price', 0))
        
        # Handle images
        l['image'] = l.get('image', '')
        # If 'photos' exists use that (from create_listing_from_args)
        if 'photos' in l and l['photos']:
             l['image'] = l['photos'][0]
        
        # If image is a list, take first
        if isinstance(l['image'], list) and len(l['image']) > 0:
             l['image'] = l['image'][0]
             
        # Fix image path if it lists 'uploads/filename' vs just 'filename' for template
        if l['image'] and isinstance(l['image'], str) and l['image'].startswith('uploads/'):
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
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")

        from models.listings import create_listing_from_args
        
        try:
            price_val = float(price) if price else 0
        except ValueError:
            price_val = 0

        create_listing_from_args(
            host_id=session["user_id"],
            name=title,
            description=description,
            price_per_night=price_val,
            amenities=amenities,
            location_city=city,
            space_type="Apartment", # Default or add field to form
            has_coworking_space=False, # Default or add field to form
            photos=[image_filename] if image_filename else [],
            latitude=float(latitude) if latitude else 0.0,
            longitude=float(longitude) if longitude else 0.0
        )

        return redirect(url_for("host.dashboard"))

    return render_template("host/add_listing.html")

@host_bp.route("/bookings")
def view_received_bookings():
    if "user_id" not in session or session.get("role") != "host":
        return redirect(url_for("auth.login"))
    
    from config import bookings_collection
    bookings = list(bookings_collection.find({"host_id": session["user_id"]}).sort("created_at", -1))
    return render_template("host/bookings.html", bookings=bookings)


@host_bp.route("/edit_listing/<listing_id>", methods=["GET", "POST"])
def edit_listing(listing_id):
    if "user_id" not in session or session.get("role") != "host":
        return redirect(url_for("auth.login"))
        
    from models.listings import get_listing_by_id, update_listing
    
    listing = get_listing_by_id(listing_id)
    
    if not listing:
        return "Listing not found", 404
        
    if str(listing.get("host_id")) != session["user_id"]:
        return "Unauthorized", 403
        
    if request.method == "POST":
        title = request.form.get("title")
        price = request.form.get("price")
        city = request.form.get("city")
        location = request.form.get("location")
        description = request.form.get("description")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        amenities = request.form.getlist('amenities')
        
        try:
            price_val = float(price) if price else 0
        except ValueError:
            price_val = 0
            
        update_data = {
            "space_title": title,
            "title": title, # legacy support
            "price_per_night": price_val,
            "price": price_val, # legacy support
            "location_city": city,
            "city": city, # legacy support
            "location": location,
            "description": description,
            "amenities": amenities,
            "latitude": float(latitude) if latitude else 0.0,
            "longitude": float(longitude) if longitude else 0.0
        }
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                update_data["photos"] = [filename]
                update_data["image"] = filename # legacy support

        update_listing(listing_id, update_data)
        return redirect(url_for("host.dashboard"))
        
    return render_template("host/edit_listing.html", listing=listing)

@host_bp.route("/delete_listing/<listing_id>", methods=["POST"])
def delete_listing_route(listing_id):
    if "user_id" not in session or session.get("role") != "host":
        return redirect(url_for("auth.login"))
        
    from models.listings import get_listing_by_id, delete_listing
    
    listing = get_listing_by_id(listing_id)
    
    if not listing:
        return "Listing not found", 404
        
    if str(listing.get("host_id")) != session["user_id"]:
        return "Unauthorized", 403
        
    delete_listing(listing_id)
    return redirect(url_for("host.dashboard"))

@host_bp.route("/listing_reviews/<listing_id>")
def get_reviews_by_listing(listing_id):
    if "user_id" not in session or session.get("role") != "host":
        return redirect(url_for("auth.login"))
        
    from models.listings import get_listing_by_id
    from models.review import get_reviews_by_space
    
    listing = get_listing_by_id(listing_id)
    if not listing:
        return "Listing not found", 404
        
    if str(listing.get("host_id")) != session["user_id"]:
        return "Unauthorized", 403
        
    reviews = get_reviews_by_space(ObjectId(listing_id))
    
    # Normalize listing title
    listing['title'] = listing.get('space_title') or listing.get('title') or "Untitled"
    
    return render_template("host/listing_reviews.html", listing=listing, reviews=reviews)

