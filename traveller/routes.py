from flask import render_template, session, redirect, url_for, request
from . import traveller_bp
from config import listings_collection, users_collection, bookings_collection
from bson.objectid import ObjectId
from email_details import send_booking_confirmation

@traveller_bp.route("/home")
def home():
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
    
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

@traveller_bp.route("/listing/<listing_id>")
def view_listing(listing_id):
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
    
    listing = listings_collection.find_one({"_id": ObjectId(listing_id)})
    if not listing:
        return "Listing not found", 404
        
    return render_template("traveller/listing_details.html", listing=listing)

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
    
    # Simple total price calculation (assuming daily price)
    from datetime import datetime
    try:
        d1 = datetime.strptime(check_in, "%Y-%m-%d")
        d2 = datetime.strptime(check_out, "%Y-%m-%d")
        days = (d2 - d1).days
        if days <= 0:
            return "Check-out must be after check-in", 400
        total_price = days * listing["price"]
    except ValueError:
        return "Invalid date format", 400

    booking = {
        "user_id": ObjectId(session["user_id"]),
        "listing_id": ObjectId(listing_id),
        "host_id": listing["host_id"],
        "listing_title": listing["title"],
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

@traveller_bp.route("/bookings")
def my_bookings():
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
    
    bookings = list(bookings_collection.find({"user_id": ObjectId(session["user_id"])}).sort("created_at", -1))
    return render_template("traveller/bookings.html", bookings=bookings)

@traveller_bp.route("/profile")
def profile():
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
    
    user = users_collection.find_one({"_id": ObjectId(session["user_id"])})
    return render_template("traveller/profile.html", user=user)
