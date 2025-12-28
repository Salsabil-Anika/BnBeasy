from flask import render_template, session, redirect, url_for, request
from . import traveller_bp
from config import listings_collection, users_collection
from bson.objectid import ObjectId
from models.bookings import add_booking, get_user_bookings, cancel_booking
from email_details import send_email

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

@traveller_bp.route("/profile")
def profile():
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
    
    user = users_collection.find_one({"_id": ObjectId(session["user_id"])})
    return render_template("traveller/profile.html", user=user)

@traveller_bp.route("/listing/<listing_id>")
def view_listing(listing_id):
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
        
    try:
        listing = listings_collection.find_one({"_id": ObjectId(listing_id)})
        if not listing:
            # You might want to flash a message here
            return redirect(url_for("traveller.home"))
            
        return render_template("traveller/listing_detail.html", listing=listing)
    except:
        return redirect(url_for("traveller.home"))

@traveller_bp.route("/book/<listing_id>", methods=["POST"])
def book_listing(listing_id):
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))

    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    user_id = session["user_id"]
    
    try:
        booking_id = add_booking(user_id, listing_id, start_date, end_date)
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        listing = listings_collection.find_one({"_id": ObjectId(listing_id)})
        
        email_body = f"""
Hi {user['name']},

Your booking for '{listing['title']}' has been confirmed!
Dates: {start_date} to {end_date}

Enjoy your stay!
"""
        send_email(user["email"], "Booking Confirmation - BnBeasy", email_body)
        
        return redirect(url_for("traveller.my_bookings"))
    except Exception as e:
        return f"Booking failed: {str(e)}"

@traveller_bp.route("/my_bookings")
def my_bookings():
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
    
    user_id = session["user_id"]
    bookings = get_user_bookings(user_id)
    
    # Enrich bookings with listing data
    for b in bookings:
        b["listing"] = listings_collection.find_one({"_id": b["listing_id"]})
        
    return render_template("traveller/my_bookings.html", bookings=bookings)

@traveller_bp.route("/cancel_booking/<booking_id>", methods=["POST"])
def cancel_booking_route(booking_id):
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
    
    try:
        cancel_booking(booking_id)
        # You might want to send a cancellation email here too
        return redirect(url_for("traveller.my_bookings"))
    except Exception as e:
        return f"Cancellation failed: {str(e)}"
