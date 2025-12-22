import os
import re
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


# Create Blueprint for traveler profiles
traveler_profiles_bp = Blueprint('traveler_profiles', __name__, template_folder='../templates', static_folder='../static')

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

    # Render template with all data
    return render_template(
        'traveller/traveler_profile.html',
        profile=profile_data,
        favorites=None,  # favorites=favorite_spaces,
        reviews=None,  # reviews=my_reviews,
        contacts=emergency_contacts_data
    )

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

