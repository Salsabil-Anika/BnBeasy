from flask import render_template, request, session, redirect, url_for
from . import traveller_bp
from config import listings_collection, users_collection, bookings_collection
from bson.objectid import ObjectId
from email_details import send_booking_confirmation

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
        # Normalize fields for template
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

from datetime import datetime, timedelta

@traveller_bp.route("/listing/<listing_id>")
def view_listing(listing_id):
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
    
    listing = listings_collection.find_one({"_id": ObjectId(listing_id)})
    if not listing:
        return "Listing not found", 404

    # Normalize listing for template (Consistent with home route)
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

    # Calculate availability for the next 7 days
    today = datetime.now().date()
    availability = []
    
    for i in range(7):
        date = today + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        
        # Check if booked
        is_booked = bookings_collection.find_one({
            "listing_id": ObjectId(listing_id),
            "status": "confirmed",
            "$or": [
                {"check_in": {"$lte": date_str}, "check_out": {"$gt": date_str}}
            ]
        })
        
        availability.append({
            "date": date.strftime("%a, %b %d"),
            "status": "Booked" if is_booked else "Available",
            "is_available": not is_booked
        })

    # Fetch reviews
    from models.review import get_reviews_by_space
    reviews = get_reviews_by_space(ObjectId(listing_id))
        
    return render_template("traveller/listing_details.html", listing=listing, availability=availability, now=today.strftime("%Y-%m-%d"), reviews=reviews)

@traveller_bp.route("/book/<listing_id>", methods=["POST"])
def book_listing(listing_id):
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
        
    listing = listings_collection.find_one({"_id": ObjectId(listing_id)})
    if not listing:
        return "Listing not found", 404
        
    email = request.form.get("email")
    check_in = request.form.get("check_in")
    check_out = request.form.get("check_out")
    note = request.form.get("note")
    
    ### availability Check for overlapping bookings
    existing_booking = bookings_collection.find_one({
        "listing_id": ObjectId(listing_id),
        "status": "confirmed",
        "$or": [    
            {"check_in": {"$lte": check_in}, "check_out": {"$gt": check_in}},
            {"check_in": {"$lt": check_out}, "check_out": {"$gte": check_out}},
            {"check_in": {"$gte": check_in}, "check_out": {"$lte": check_out}}
        ]
    })
    
    if existing_booking:
        return "These dates are already booked. Please choose different dates.", 400
    
    from datetime import datetime
    try:
        d1 = datetime.strptime(check_in, "%Y-%m-%d")
        d2 = datetime.strptime(check_out, "%Y-%m-%d")
        days = (d2 - d1).days
        if days <= 0:
            return "Check-out must be after check-in", 400
            
    
        price_per_night = listing.get("price", listing.get("price_per_night", 0))
        total_price = days * price_per_night
    except ValueError:
        return "Invalid date format", 400

    booking = {
        "user_id": ObjectId(session["user_id"]),
        "listing_id": ObjectId(listing_id),
        "host_id": listing["host_id"],
        "listing_title": listing.get("title", listing.get("space_title", "Untitled")),
        "email": email,
        "check_in": check_in,
        "check_out": check_out,
        "note": note,
        "total_price": total_price,
        "status": "confirmed",
        "created_at": datetime.utcnow()
    }
    
    bookings_collection.insert_one(booking)
    
    # Send confirmation email
    try:
        send_booking_confirmation(email, booking)
    except Exception as e:
        print(f"Failed to send email: {e}")

    return redirect(url_for("traveller.my_bookings"))



@traveller_bp.route("/profile")
def profile():
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
    
    user = users_collection.find_one({"_id": ObjectId(session["user_id"])})
    return render_template("traveller/profile.html", user=user)
