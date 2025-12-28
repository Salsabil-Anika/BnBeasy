# routes\space.py

from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from bson.objectid import ObjectId

# Import all necessary functions from the models
from models.space import (
    create_space as create_space_in_db, 
    get_space_by_id, 
    update_space, 
    filter_spaces,
    get_all_spaces,
    get_popular_spaces_in_location,
    delete_space
)
#from models.review import get_average_rating_for_space
from config import db

# Initialize the Blueprint
space_bp = Blueprint('space_bp', __name__)

# Define the folder for file uploads
upload_folder = 'static/uploads'

# Ensure the upload folder exists, creating it if necessary.
os.makedirs(upload_folder, exist_ok=True)

# --- Helper Functions for data normalization ---
def _normalize_incoming_id(val):
    """
    Accept common incoming id shapes and return a clean hex string id when possible.
    Handles ObjectId instances and strings like "ObjectId('...')".
    """
    if isinstance(val, ObjectId):
        return str(val)
    if not isinstance(val, str):
        return val
    v = val.strip()
    if v.startswith("ObjectId("):
        try:
            return v.split("'", 2)[1]
        except Exception:
            return v
    return v

def _sanitize_for_session(data):
    """
    Recursively sanitizes data to be JSON-serializable for the session.
    """
    if isinstance(data, list):
        return [_sanitize_for_session(item) for item in data]
    if isinstance(data, dict):
        # Use .copy() to avoid modifying the original dictionary in place
        clean_dict = {}
        for key, value in data.items():
            # Convert ObjectId to string for the '_id' field specifically
            if key == '_id' and isinstance(value, ObjectId):
                clean_dict[key] = str(value)
            else:
                clean_dict[key] = _sanitize_for_session(value)
        return clean_dict
    if isinstance(data, ObjectId):
        return str(data)
    if isinstance(data, datetime):
        return data.isoformat()
    return data

def _unwrap_and_normalize_space_obj(raw):
    """
    Accept space dicts in variants (wrapped under 'space' key or direct).
    Ensures:
      - '_id' is a string
      - 'photos' paths are normalized for url_for('static', filename=...)
      - 'space_title' exists
    """
    if not isinstance(raw, dict):
        return raw
    # Use .copy() to avoid modifying the original dictionary in place
    s = raw.get('space').copy() if 'space' in raw and isinstance(raw['space'], dict) else raw.copy()

    # Carry top-level metadata if the object was wrapped
    for k in ('average_rating', 'review_count', 'reviews'):
        if k in raw and k not in s:
            s[k] = raw[k]

    # Normalize the '_id' field to a string
    if s.get('_id') is not None:
        s['_id'] = str(s['_id'])

    # Normalize photo paths for consistency
    photos = s.get('photos') or []
    normalized = []
    for p in photos:
        if not p:
            continue
        p2 = p.replace("\\", "/")
        if p2.startswith("static/"):
            p2 = p2[len("static/"):]
        if os.path.isabs(p2) or (':' in p2 and '/' in p2):
            p2 = os.path.basename(p2)
            p2 = f"uploads/{p2}"
        if not p2.startswith("uploads/") and '/' not in p2:
            p2 = f"uploads/{p2}"
        normalized.append(p2)
    s['photos'] = normalized

    # Ensure a title field exists
    s.setdefault('space_title', s.get('space_title') or s.get('title') or s.get('name') or '')
    return s

# --- Route Definitions ---

@space_bp.route('/space/<space_id>')
def space_detail(space_id):
    """Displays the full detail page for a single space."""
    # Normalize common incoming id shapes (e.g., ObjectId('...'))
    space_id = _normalize_incoming_id(space_id)
    space = get_space_by_id(space_id)
    if not space:
        flash("Space not found.", "danger")
        return redirect(url_for('index'))
    
    # Ensure ObjectId is converted to string for template compatibility
    space['_id'] = str(space['_id'])
    
    return render_template('space_detail.html', space=space)


@space_bp.route('/spaces/create', methods=['GET', 'POST'])
def create_space():
    """
    Handles the creation of a new space.
    """
    if session.get('role') != 'host':
        flash("You must be a host to create a space.", "danger")
        return redirect(url_for('auth.dashboard'))

    if request.method == 'GET':
        return render_template("create_space_form.html")

    
    try:
        price = float(request.form.get("price_per_night"))
    except (ValueError, TypeError):
        flash("Invalid price format. Please enter a valid number.", "danger")
        return redirect(url_for('space_bp.create_space'))

    photos_urls = []
    if "photos" in request.files:
        for file in request.files.getlist("photos"): 
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                photos_urls.append(f"uploads/{filename}")

    space_data = {
        "host_id": session.get('user_id'),
        "host_name": session.get('first_name'),
        "space_title": request.form.get("space_title"),
        "location_city": request.form.get("location_city"),
        "description": request.form.get("description"),
        "price_per_night": price,
        "amenities": request.form.getlist("amenities"),
        "photos": photos_urls,
        "space_type": request.form.get("space_type"),
        "has_coworking_space": "has_coworking_space" in request.form,
        "wifi_speed_mbps": 50,
        "latitude": float(request.form.get("latitude")),
        "longitude": float(request.form.get("longitude")),
    }

    result = create_space_in_db(space_data)
    
    is_api_request = request.is_json or 'application/json' in request.headers.get('Accept', '')
    if is_api_request:
        return jsonify({"message": "Space created successfully", "id": str(result.inserted_id)}), 201
    else:
        flash("Space created successfully!", "success")
        return redirect(url_for('space_bp.get_my_spaces_route'))

@space_bp.route('/spaces/<space_id>/book', methods=['POST'])
def book_space(space_id):
    """Handles the logic for a traveler to book a space."""
    if 'role' not in session or session['role'] != 'traveller':
        flash("Only travelers can book spaces. Please log in.", "warning")
        return redirect(url_for('auth.login'))

    space = get_space_by_id(space_id)
    if not space:
        flash("Sorry, this space could not be found.", "danger")
        return redirect(url_for('index'))

    check_in_date = request.form.get('check_in_date')
    check_out_date = request.form.get('check_out_date')
    guests = request.form.get('guests', 1)

    if not check_in_date or not check_out_date:
        flash("Please select both a check-in and check-out date.", "danger")
        return redirect(url_for('space_bp.space_detail', space_id=space_id))

    booking_record = {
        "user_id": session.get('user_id'),
        "space_id": str(space['_id']),
        "host_id": space.get('host_id'),
        "space_title": space.get('space_title'),
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "price_per_night": space.get('price_per_night'),
        "guests": int(guests) if guests else 1,
        "status": "Confirmed",
        "booked_at": datetime.utcnow()
    }

    try:
        # use bookings model to create booking
        from models.booking import create_booking
        booking_id = create_booking(booking_record)

        flash(f"Successfully booked {space.get('space_title', '')}!", "success")

        suggestions = get_popular_spaces_in_location(space.get('location_city', ''), exclude_id=space_id)
        session['suggested_spaces'] = _sanitize_for_session(suggestions)
        session['new_suggestions'] = True

        return redirect(url_for('traveler_profiles.booking_history'))
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('space_bp.space_detail', space_id=space_id))


@space_bp.route("/spaces/my-listings")
def get_my_spaces_route():
    """
    Displays a filtered list of spaces owned by the currently logged-in host.
    """
    if session.get('role') != 'host':
        flash("You must be a host to view your listings.", "danger")
        return redirect(url_for('auth.dashboard'))
    
    host_id = session.get('user_id')
    
    filters = {
        'min_price': request.args.get('min_price', ''),
        'max_price': request.args.get('max_price', ''),
        'location': request.args.get('location', ''),
        'coworking': request.args.get('coworking', ''),
        'space_type': request.args.get('space_type', ''),
        'amenities': request.args.getlist('amenities'),
        'sort_by': request.args.get('sort_by', '')
    }
    
    filters['host_id'] = host_id
    
    my_spaces = filter_spaces(filters)
    
    all_amenities = ["High-Speed WiFi", "AC", "Kitchen", "Parking"]
    
    return render_template(
        "spaces.html", 
        spaces=my_spaces, 
        filters=filters, 
        all_amenities=all_amenities, 
        is_my_spaces_page=True
    )

@space_bp.route('/spaces/edit/<space_id>', methods=['GET', 'POST'])
def edit_space(space_id):
    """
    Handles editing of an existing space.
    """
    if session.get('role') != 'host':
        flash("You must be a host to edit a space.", "danger")
        return redirect(url_for('auth.dashboard'))

    space = get_space_by_id(space_id)
    if not space or str(space.get('host_id')) != str(session.get('user_id')):
        flash("You are not authorized to edit this space or it does not exist.", "danger")
        return redirect(url_for('space_bp.get_my_spaces_route'))

    if request.method == 'POST':
        updated_data = {
            "space_title": request.form.get("space_title"),
            "description": request.form.get("description"),
            "price_per_night": int(request.form.get("price_per_night")),
            "amenities": request.form.getlist("amenities"),
            "space_type": request.form.get("space_type"),
            "has_coworking_space": "has_coworking_space" in request.form,
            "latitude": float(request.form.get("latitude")),
            "longitude": float(request.form.get("longitude")),
        }
        
        update_space(space_id, updated_data)
        flash("Your space has been updated successfully!", "success")
        return redirect(url_for('space_bp.get_my_spaces_route'))

    return render_template("edit_space.html", space=space)

@space_bp.route("/api/spaces", methods=["GET"])
def api_get_all_spaces():
    """
    A simple API endpoint to fetch all spaces.
    """
    spaces_cursor = get_all_spaces()
    spaces_list = [_unwrap_and_normalize_space_obj(space) for space in spaces_cursor]
    return jsonify(spaces_list)

@space_bp.route('/spaces/delete/<space_id>', methods=['POST'])
def delete_space_route(space_id):
    """
    Deletes a space owned by the currently logged-in host.
    """
    if session.get('role') != 'host':
        flash("You must be a host to delete a space.", "danger")
        return redirect(url_for('auth.dashboard'))

    space = get_space_by_id(space_id)
    if not space or str(space.get('host_id')) != str(session.get('user_id')):
        flash("You are not authorized to delete this space or it does not exist.", "danger")
        return redirect(url_for('space_bp.get_my_spaces_route'))

   
    delete_space(space_id)

    flash("Space deleted successfully!", "success")
    return redirect(url_for('space_bp.get_my_spaces_route'))

