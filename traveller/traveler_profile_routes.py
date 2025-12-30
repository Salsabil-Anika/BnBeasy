import os
import re
from datetime import datetime
from flask import Blueprint, current_app, request, redirect, url_for, flash, session, render_template, jsonify
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from . import traveller_bp

# Import models using absolute imports
from models.traveler_profile import (
    update_traveler_profile_info,
    get_user_profile,
    get_emergency_contacts,
    update_emergency_contacts
)
from models.booking import get_bookings_by_user, get_booking_by_id, cancel_booking


# File upload settings
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Helper function to check file extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@traveller_bp.route("/profile/traveler")
def view_traveler_profile():
    if 'user_id' not in session or session.get('role') != 'traveller':
        flash('You must be logged in as a traveler to view this page.', 'danger')
        return redirect(url_for('auth.login'))

    # Use the _id from session for reliable lookups
    user_mongo_id = session['user_id']
    try:
        profile_data = get_user_profile(user_mongo_id)
    except Exception:
        flash('Could not find your profile data.', 'danger')
        return redirect(url_for('auth.logout'))

    if not profile_data:
        flash('Could not find your profile data.', 'danger')
        return redirect(url_for('auth.logout'))
    


    emergency_contacts_data = get_emergency_contacts(user_mongo_id)
    # Fetch user's bookings so they can view/cancel from the profile dashboard
    try:
        bookings = get_bookings_by_user(user_mongo_id)
    except Exception:
        bookings = []

    # Fetch user's reviews
    from models.review import get_reviews_by_user
    from models.listings import get_listing_by_id
    try:
        my_reviews = get_reviews_by_user(user_mongo_id)
        # Hydrate reviews with listing names
        for r in my_reviews:
            if 'space_id' in r:
                listing = get_listing_by_id(r['space_id'])
                r['space_name'] = listing.get('space_title') or "Unknown Space" if listing else "Unknown Space"
    except Exception:
        my_reviews = []

    # Reuse a small sanitizer to convert ObjectIds/datetimes into strings for templates
    def _sanitize_item(o):
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                out[k] = _sanitize_item(v)
            if '_id' in out:
                try:
                    from bson.objectid import ObjectId
                    if isinstance(out['_id'], ObjectId):
                        out['_id'] = str(out['_id'])
                except Exception:
                    pass
            return out
        if isinstance(o, list):
            return [_sanitize_item(i) for i in o]
        try:
            from bson.objectid import ObjectId
            if isinstance(o, ObjectId):
                return str(o)
        except Exception:
            pass
        if isinstance(o, datetime):
            return o.isoformat()
        return o

    safe_bookings = _sanitize_item(bookings)
    safe_reviews = _sanitize_item(my_reviews)

    # Render template with all data including bookings
    return render_template(
        'traveller/traveler_profile.html',
        profile=profile_data,
        favorites=None,  # favorites=favorite_spaces,
        reviews=safe_reviews,
        contacts=emergency_contacts_data,
        bookings=safe_bookings
    )

@traveller_bp.route('/profile/review/delete/<review_id>', methods=['POST'])
def delete_review_route(review_id):
    if 'user_id' not in session or session.get('role') != 'traveller':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('auth.login'))

    from models.review import delete_review, reviews_collection
    # Security check: ensure the review belongs to the user
    review = reviews_collection.find_one({"_id": ObjectId(review_id)})
    if not review or str(review.get('user_id')) != str(session['user_id']):
        flash('Unauthorized or review not found.', 'danger')
        return redirect(url_for('traveller.view_traveler_profile'))

    delete_review(review_id)
    flash("Review deleted successfully.", "success")
    return redirect(url_for('traveller.view_traveler_profile'))



# Profile update kore
@traveller_bp.route("/profile/update", methods=['POST'])
def update_profile():
    """Handle profile update form submission."""
    if 'user_id' not in session or session.get('role') != 'traveller':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Check if this is an AJAX request
    is_ajax = 'application/json' in request.headers.get('Accept', '')

    user_mongo_id = session['user_id']
    new_profile_pic_path = None

    # Handle profile picture upload
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Use current_app to get the app instance and construct proper path
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            save_path = os.path.join(upload_folder, filename)
            file.save(save_path)
            new_profile_pic_path = f"/static/uploads/{filename}"

    form_data = request.form.to_dict()

    try:
        # Call model function to update database
        update_traveler_profile_info(user_mongo_id, form_data, new_profile_pic_path)
        flash('Profile successfully updated!', 'success')
        if is_ajax:
            return jsonify({'success': True})
        return redirect(url_for('traveller.view_traveler_profile'))
    except Exception as e:
        flash(f'An error occurred while updating: {e}', 'danger')
        if is_ajax:
            return jsonify({'success': False, 'message': str(e)}), 500
        return redirect(url_for('traveller.view_traveler_profile'))

@traveller_bp.route("/profile/emergency_contacts", methods=['GET', 'POST'])
def emergency_contacts():
    """Emergency contact add/update page and logic."""
    if 'user_id' not in session or session.get('role') != 'traveller':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    
    user_mongo_id = session['user_id']
    
    if request.method == 'POST':
        contacts = []
        # Get name, phone, relation for each contact from form
        names = request.form.getlist('contact_name')
        phones = request.form.getlist('contact_phone')
        relations = request.form.getlist('contact_relation')
        for n, p, r in zip(names, phones, relations):
            if n and p: # If name and phone number are provided
                contacts.append({'name': n, 'phone': p, 'relation': r})
        # Update in database
        update_emergency_contacts(user_mongo_id, contacts)
        flash('Emergency contacts updated!', 'success')
        return redirect(url_for('traveller.view_traveler_profile'))
        
##bookings 
@traveller_bp.route('/bookings')
def my_bookings():
    # Auth check
    if 'user_id' not in session or session.get('role') != 'traveller':
        flash('You must be logged in as a traveler.', 'danger')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    try:
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
                d1 = datetime.strptime(b['check_in_date'], '%Y-%m-%d')
                d2 = datetime.strptime(b['check_out_date'], '%Y-%m-%d')
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

    # Verify booking exists and belongs to current user
    b = get_booking_by_id(booking_id)
    if not b:
        flash('Booking not found.', 'danger')
        return redirect(url_for('traveller.my_bookings'))

    # Compare stored user id (may be ObjectId or string)
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
    
    # For GET request, fetch current contacts and show form
    contacts_data = get_emergency_contacts(user_mongo_id)
    return render_template('traveller/emergency_contacts.html', contacts=contacts_data)

