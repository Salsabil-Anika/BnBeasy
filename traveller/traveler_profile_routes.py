import os
import re
from datetime import datetime
from flask import Blueprint, current_app, request, redirect, url_for, flash, session, render_template, jsonify
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId

# Import models using absolute imports
from models.traveler_profile import (
    update_traveler_profile_info,
    get_user_profile,
    get_emergency_contacts,
    update_emergency_contacts
)
from models.booking import get_bookings_by_user, get_booking_by_id, cancel_booking



traveler_profiles_bp = Blueprint('traveler_profiles', __name__, url_prefix='/traveller', template_folder='../templates', static_folder='../static')

# File upload settings
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Helper function to check file extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@traveler_profiles_bp.route("/profile/traveler")
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

    # Render template with all data including bookings
    return render_template(
        'traveller/traveler_profile.html',
        profile=profile_data,
        favorites=None,  # favorites=favorite_spaces,
        reviews=None,  # reviews=my_reviews,
        contacts=emergency_contacts_data,
        bookings=safe_bookings
    )


@traveler_profiles_bp.route('/bookings')
def booking_history():
    if 'user_id' not in session or session.get('role') != 'traveller':
        flash('You must be logged in as a traveler to view bookings.', 'danger')
        return redirect(url_for('auth.login'))

    user_mongo_id = session['user_id']
    try:
        bookings = get_bookings_by_user(user_mongo_id)
    except Exception:
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
        return render_template('traveller/booking_history.html', bookings=safe_bookings)
    except Exception:
        return jsonify({'bookings': safe_bookings})



@traveler_profiles_bp.route('/bookings/cancel/<booking_id>', methods=['POST'])
def cancel_booking_route(booking_id):
    if 'user_id' not in session or session.get('role') != 'traveller':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('auth.login'))

    # Verify booking exists and belongs to current user
    b = get_booking_by_id(booking_id)
    if not b:
        flash('Booking not found.', 'danger')
        return redirect(url_for('traveler_profiles.booking_history'))

    # Compare stored user id (may be ObjectId or string)
    b_user = b.get('user_id')
    if isinstance(b_user, ObjectId):
        b_user = str(b_user)

    if str(b_user) != str(session.get('user_id')):
        flash('You are not authorized to cancel this booking.', 'danger')
        return redirect(url_for('traveler_profiles.booking_history'))

    success = cancel_booking(booking_id)
    if success:
        flash('Booking cancelled successfully.', 'success')
    else:
        flash('Could not cancel booking. Please try again.', 'danger')

    return redirect(url_for('traveler_profiles.booking_history'))
# Profile update kore
@traveler_profiles_bp.route("/profile/update", methods=['POST'])
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
        return redirect(url_for('traveler_profiles.view_traveler_profile'))
    except Exception as e:
        flash(f'An error occurred while updating: {e}', 'danger')
        if is_ajax:
            return jsonify({'success': False, 'message': str(e)}), 500
        return redirect(url_for('traveler_profiles.view_traveler_profile'))

@traveler_profiles_bp.route("/profile/emergency_contacts", methods=['GET', 'POST'])
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
        return redirect(url_for('traveler_profiles.view_traveler_profile'))
    
    # For GET request, fetch current contacts and show form
    contacts_data = get_emergency_contacts(user_mongo_id)
    return render_template('traveller/emergency_contacts.html', contacts=contacts_data)

