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
    from models.space import get_space_by_id
    try:
        my_reviews = get_reviews_by_user(user_mongo_id)
        # Hydrate reviews with space names
        for r in my_reviews:
            if 'space_id' in r:
                space = get_space_by_id(r['space_id'])
                r['space_name'] = space.get('space_title') or "Unknown Space" if space else "Unknown Space"
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


@traveller_bp.route('/bookings')
def my_bookings():
    if 'user_id' not in session or session.get('role') != 'traveller':
        flash('You must be logged in as a traveler to view bookings.', 'danger')
        return redirect(url_for('auth.login'))

    user_mongo_id = session['user_id']
    try:
        bookings = get_bookings_by_user(user_mongo_id)
        # Hydrate listings for template
        from models.space import get_space_by_id
        for b in bookings:
            if 'space_id' in b:
                space_doc = get_space_by_id(b['space_id'])
                if space_doc:
                     # Ensure photos are normalized
                    photos = space_doc.get('photos', [])
                    normalized_photos = []
                    for p in photos:
                        if p:
                            p2 = p.replace("\\", "/")
                            if p2.startswith("static/"):
                                p2 = p2[len("static/"):]
                            if os.path.isabs(p2) or (':' in p2 and '/' in p2):
                                p2 = os.path.basename(p2)
                                p2 = f"uploads/{p2}"
                            if not p2.startswith("uploads/") and '/' not in p2:
                                p2 = f"uploads/{p2}"
                            normalized_photos.append(p2)
                    space_doc['photos'] = normalized_photos
                    
                    # Add simple image field for template
                    if normalized_photos:
                        space_doc['image'] = normalized_photos[0]
                    
                    b['listing'] = space_doc
                    
                    # If flat fields are missing, populate them from space_doc
                    if not b.get('space_title'):
                        b['space_title'] = space_doc.get('space_title') or space_doc.get('title')
                    if not b.get('price_per_night'):
                         b['price_per_night'] = space_doc.get('price_per_night')
                    
                    # Calculate Total Price (Overall Bill)
                    try:
                        price = float(b.get('price_per_night', 0))
                        check_in = b.get('check_in_date')
                        check_out = b.get('check_out_date')
                        
                        if check_in and check_out:
                            # Parse dates (assuming 'YYYY-MM-DD' format)
                            d1 = datetime.strptime(check_in, '%Y-%m-%d')
                            d2 = datetime.strptime(check_out, '%Y-%m-%d')
                            delta = d2 - d1
                            nights = delta.days
                            if nights < 1: nights = 1
                            
                            b['total_price'] = nights * price
                            b['nights_count'] = nights
                        else:
                            b['total_price'] = price # Fallback
                    except Exception as calc_err:
                        print(f"Error calculating total price: {calc_err}")
                        b['total_price'] = 0
                else:
                    b['listing'] = {}
            else:
                b['listing'] = {}

    except Exception as e:
        print(f"Error fetching bookings: {e}")
        bookings = []
    # Sanitize bookings for template rendering and JSON (convert ObjectId and datetimes)
    def _sanitize_item(o):
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                out[k] = _sanitize_item(v)
            # ensure _id is a string for templates
            if '_id' in out and isinstance(out['_id'], ObjectId):
                out['_id'] = str(out['_id'])
            return out
        if isinstance(o, list):
            return [_sanitize_item(i) for i in o]
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return o

    safe_bookings = _sanitize_item(bookings)
    # Try to render a template if present; otherwise return JSON for API/debug
    try:
        return render_template('traveller/my_bookings.html', bookings=safe_bookings)
    except Exception:
        return jsonify({'bookings': safe_bookings})



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
    
    # For GET request, fetch current contacts and show form
    contacts_data = get_emergency_contacts(user_mongo_id)
    return render_template('traveller/emergency_contacts.html', contacts=contacts_data)

