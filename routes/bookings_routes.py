from flask import render_template, request, session, redirect, url_for, flash
from config import listings_collection, users_collection, bookings_collection
from bson.objectid import ObjectId
from email_details import send_booking_confirmation
from datetime import datetime

# Import blueprints
from . import host_bp, traveller_bp

# --- Traveller Booking Routes ---

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
    
    try:
        send_booking_confirmation(email, booking)
    except Exception as e:
        print(f"Failed to send email: {e}")

    return redirect(url_for("traveller.my_bookings"))

@traveller_bp.route('/bookings')
def my_bookings():
    if 'user_id' not in session or session.get('role') != 'traveller':
        flash('You must be logged in as a traveler.', 'danger')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    try:
        from models.booking import get_bookings_by_user
        bookings = get_bookings_by_user(user_id)
        from models.listings import get_listing_by_id

        for b in bookings:
            listing_id = b.get('listing_id')
            if not listing_id:
                b['listing'] = {}
                continue
            listing = get_listing_by_id(listing_id)
            if not listing:
                b['listing'] = {}
                continue
            b['listing'] = listing
            b['space_title'] = b.get('title') or listing.get('title')
            b['price_per_night'] = b.get('price_per_night') or listing.get('price_per_night')
            b['image'] = listing.get('image')  

            try:
                price = float(b['price_per_night'])
                d1 = datetime.strptime(b['check_in_date'] if 'check_in_date' in b else b['check_in'], '%Y-%m-%d')
                d2 = datetime.strptime(b['check_out_date'] if 'check_out_date' in b else b['check_out'], '%Y-%m-%d')
                nights = max((d2 - d1).days, 1)
                b['nights_count'] = nights
                b['total_price'] = nights * price
            except:
                b['total_price'] = 0
    except Exception as e:
        print("Booking error:", e)
        bookings = []

    return render_template('traveller/my_bookings.html', bookings=bookings)

@traveller_bp.route('/bookings/cancel/<booking_id>', methods=['POST'])
def cancel_booking_route(booking_id):
    if 'user_id' not in session or session.get('role') != 'traveller':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('auth.login'))

    from models.booking import get_booking_by_id, cancel_booking
    b = get_booking_by_id(booking_id)
    if not b:
        flash('Booking not found.', 'danger')
        return redirect(url_for('traveller.my_bookings'))

    b_user = b.get('user_id')
    if isinstance(b_user, ObjectId):
        b_user = str(b_user)

    if str(b_user) != str(session.get('user_id')):
        flash('You are not authorized to cancel this booking.', 'danger')
        return redirect(url_for('traveller.my_bookings'))

    success = cancel_booking(booking_id)
    if success:
        flash('Booking cancelled successfully.', 'success')
    else:
        flash('Could not cancel booking. Please try again.', 'danger')

    return redirect(url_for('traveller.my_bookings'))

# --- Host Booking Routes ---

@host_bp.route("/bookings")
def view_received_bookings():
    if "user_id" not in session or session.get("role") != "host":
        return redirect(url_for("auth.login"))
    
    bookings = list(bookings_collection.find({"host_id": session["user_id"]}).sort("created_at", -1))
    return render_template("host/bookings.html", bookings=bookings)
