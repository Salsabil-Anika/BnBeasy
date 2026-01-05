import os
from datetime import datetime
from flask import current_app, request, redirect, url_for, flash, session, render_template, jsonify
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId

# Import from package
from . import traveller_bp

# Import models
from models.traveler_profile import (
    update_traveler_profile_info,
    get_user_profile,
    get_emergency_contacts,
    update_emergency_contacts
)

# File upload settings
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@traveller_bp.route("/profile/traveler")
def view_traveler_profile():
    if 'user_id' not in session or session.get('role') != 'traveller':
        flash('You must be logged in as a traveler to view this page.', 'danger')
        return redirect(url_for('auth.login'))

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
    
    from models.booking import get_bookings_by_user
    try:
        bookings = get_bookings_by_user(user_mongo_id)
    except Exception:
        bookings = []

    from models.review import get_reviews_by_user
    from models.listings import get_listing_by_id
    try:
        my_reviews = get_reviews_by_user(user_mongo_id)
        for r in my_reviews:
            if 'space_id' in r:
                listing = get_listing_by_id(r['space_id'])
                r['space_name'] = listing.get('space_title') or "Unknown Space" if listing else "Unknown Space"
    except Exception:
        my_reviews = []

    def _sanitize_item(o):
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                out[k] = _sanitize_item(v)
            if '_id' in out:
                if isinstance(out['_id'], ObjectId):
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
    safe_reviews = _sanitize_item(my_reviews)

    return render_template(
        'traveller/traveler_profile.html',
        profile=profile_data,
        reviews=safe_reviews,
        contacts=emergency_contacts_data,
        bookings=safe_bookings
    )

@traveller_bp.route("/profile/update", methods=['POST'])
def update_profile():
    if 'user_id' not in session or session.get('role') != 'traveller':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    
    is_ajax = 'application/json' in request.headers.get('Accept', '')
    user_mongo_id = session['user_id']
    new_profile_pic_path = None

    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            new_profile_pic_path = f"/static/uploads/{filename}"

    try:
        update_traveler_profile_info(user_mongo_id, request.form.to_dict(), new_profile_pic_path)
        flash('Profile successfully updated!', 'success')
        if is_ajax: return jsonify({'success': True})
        return redirect(url_for('traveller.view_traveler_profile'))
    except Exception as e:
        flash(f'An error occurred: {e}', 'danger')
        if is_ajax: return jsonify({'success': False, 'message': str(e)}), 500
        return redirect(url_for('traveller.view_traveler_profile'))

@traveller_bp.route("/profile/emergency_contacts", methods=['GET', 'POST'])
def emergency_contacts():
    if 'user_id' not in session or session.get('role') != 'traveller':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    
    user_mongo_id = session['user_id']
    if request.method == 'POST':
        contacts = []
        names = request.form.getlist('contact_name')
        phones = request.form.getlist('contact_phone')
        relations = request.form.getlist('contact_relation')
        for n, p, r in zip(names, phones, relations):
            if n and p: contacts.append({'name': n, 'phone': p, 'relation': r})
        update_emergency_contacts(user_mongo_id, contacts)
        flash('Emergency contacts updated!', 'success')
        return redirect(url_for('traveller.view_traveler_profile'))
