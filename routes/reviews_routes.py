# routes/reviews.py
from flask import render_template, request, session, redirect, url_for, flash, current_app
from config import listings_collection, users_collection
from bson.objectid import ObjectId
import os
from werkzeug.utils import secure_filename
from models.review import create_review

from . import reviews_bp

@reviews_bp.route('/submit/<space_id>', methods=['GET', 'POST'])
def submit_review(space_id):
    if 'user_id' not in session:
        flash("Please log in to submit a review", "danger")
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    
    space = listings_collection.find_one({"_id": ObjectId(space_id)})
    
    if not space:
        flash("Listing not found", "danger")
        return redirect(url_for('traveller.home'))

    if request.method == 'POST':
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        photo = request.files.get('photo')
        
        photo_filename = None
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            upload_folder = current_app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            photo.save(os.path.join(upload_folder, filename))
            photo_filename = filename

        display_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        if not display_name:
            display_name = user.get('name') or user.get('email') or 'Anonymous'

        review_data = {
            "user_id": ObjectId(user_id),
            "space_id": ObjectId(space_id), 
            "rating": int(rating),
            "comment": comment,
            "photo": photo_filename,
            "user_name": display_name
        }
        
        create_review(review_data)
        flash("Review submitted successfully!", "success")
        return redirect(url_for('traveller.view_listing', listing_id=space_id))

    if not space.get('space_title'):
        space['space_title'] = space.get('title')
        
    return render_template('reviews/submit_review.html', space=space, user=user)
