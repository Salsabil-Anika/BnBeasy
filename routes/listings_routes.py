from flask import render_template, request, session, redirect, url_for, current_app
from config import listings_collection, users_collection
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os

# Import blueprints from the central routes package
from . import host_bp, traveller_bp

# --- Traveller Listing Routes ---

@traveller_bp.route('/home')
def home():
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
    query = {}
    and_conditions = []
    
    name_query = request.args.get("name")
    if name_query:
        and_conditions.append({
            "$or": [
                {"space_title": {"$regex": name_query, "$options": "i"}},
                {"title": {"$regex": name_query, "$options": "i"}}
            ]
        })
        
    city = request.args.get("city")
    if city:
        and_conditions.append({
            "$or": [
                {"city": {"$regex": city, "$options": "i"}},
                {"location_city": {"$regex": city, "$options": "i"}},
                {"location": {"$regex": city, "$options": "i"}}
            ]
        })
        
    price = request.args.get("price")
    if price:
        try:
             p_val = int(price)
             and_conditions.append({
                "$or": [
                    {"price": {"$lte": p_val}},
                    {"price_per_night": {"$lte": p_val}}
                ]
            })
        except ValueError:
            pass

    amenities = request.args.getlist("amenities")
    if amenities:
        and_conditions.append({"amenities": {"$all": amenities}})
        
    if and_conditions:
        query["$and"] = and_conditions
            
    raw_listings = list(listings_collection.find(query))
    normalized_listings = []
    
    for l in raw_listings:
        l['title'] = l.get('space_title') or l.get('title') or "Untitled"
        l['city'] = l.get('location_city') or l.get('city') or "Unknown Location"
        l['price'] = l.get('price_per_night') or l.get('price') or 0
        
        photos = l.get('photos') or []
        current_image = l.get('image')
        if photos and len(photos) > 0:
            current_image = photos[0]
        if current_image:
            if isinstance(current_image, list):
                 current_image = current_image[0]
            if isinstance(current_image, str):
                current_image = current_image.replace('uploads/', '').replace('static/', '')
        l['image'] = current_image
        normalized_listings.append(l)

    return render_template("traveller/home.html", listings=normalized_listings)

@traveller_bp.route("/listing/<listing_id>")
def view_listing(listing_id):
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
    
    listing = listings_collection.find_one({"_id": ObjectId(listing_id)})
    if not listing:
        return "Listing not found", 404

    listing['title'] = listing.get('space_title') or listing.get('title') or "Untitled"
    listing['city'] = listing.get('location_city') or listing.get('city') or "Unknown Location"
    listing['price'] = listing.get('price_per_night') or listing.get('price') or 0
    
    photos = listing.get('photos') or []
    current_image = listing.get('image')
    if photos and len(photos) > 0:
        current_image = photos[0]
    if current_image:
        if isinstance(current_image, list):
            current_image = current_image[0]
        if isinstance(current_image, str):
            current_image = current_image.replace('uploads/', '').replace('static/', '')
    listing['image'] = current_image

    from config import bookings_collection
    today = datetime.now().date()
    availability = []
    for i in range(7):
        date = today + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        is_booked = bookings_collection.find_one({
            "listing_id": ObjectId(listing_id),
            "status": "confirmed",
            "$or": [{"check_in": {"$lte": date_str}, "check_out": {"$gt": date_str}}]
        })
        availability.append({
            "date": date.strftime("%a, %b %d"),
            "status": "Booked" if is_booked else "Available",
            "is_available": not is_booked
        })

    from models.review import get_reviews_by_space
    reviews = get_reviews_by_space(ObjectId(listing_id))
    return render_template("traveller/listing_details.html", listing=listing, availability=availability, now=today.strftime("%Y-%m-%d"), reviews=reviews)

# --- Host Listing Routes ---

@host_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session or session.get("role") != "host":
        return redirect(url_for("auth.login"))
    
    user_id = session["user_id"]
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    
    from models.listings import get_listings_by_host
    listings = get_listings_by_host(user_id)
    listing_count = len(listings)
    
    for l in listings:
        l['title'] = l.get('space_title', l.get('title', 'Untitled'))
        l['city'] = l.get('location_city', l.get('city', ''))
        l['price'] = l.get('price_per_night', l.get('price', 0))
        l['image'] = l.get('image', '')
        if 'photos' in l and l['photos']:
             l['image'] = l['photos'][0]
        if isinstance(l['image'], list) and len(l['image']) > 0:
             l['image'] = l['image'][0]
        if l['image'] and isinstance(l['image'], str) and l['image'].startswith('uploads/'):
            l['image'] = l['image'].replace('uploads/', '')

    return render_template("host/dashboard.html", user=user, listing_count=listing_count, listings=listings)

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
            space_type="Apartment", 
            has_coworking_space=False, 
            photos=[image_filename] if image_filename else [],
            latitude=float(latitude) if latitude else 0.0,
            longitude=float(longitude) if longitude else 0.0
        )
        return redirect(url_for("host.dashboard"))

    return render_template("host/add_listing.html")

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
            "title": title, 
            "price_per_night": price_val,
            "price": price_val, 
            "location_city": city,
            "city": city, 
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
                update_data["image"] = filename 

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
    listing['title'] = listing.get('space_title') or listing.get('title') or "Untitled"
    return render_template("host/listing_reviews.html", listing=listing, reviews=reviews)
