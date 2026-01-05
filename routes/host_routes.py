from flask import render_template, request, session, redirect, url_for, current_app
from models.user import users_collection
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import os

# Import blueprint
from . import host_bp

@host_bp.route("/profile", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session or session.get("role") != "host":
        return redirect(url_for("auth.login"))

    user = users_collection.find_one({"_id": ObjectId(session["user_id"])})

    if request.method == "POST":
        name = request.form.get("name")
        bio = request.form.get("bio")
        location = request.form.get("location")
        
        update_data = {"name": name, "bio": bio, "location": location}

        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename != '':
                filename = secure_filename(f"profile_{session['user_id']}_{file.filename}")
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                update_data["profile_image"] = filename

        users_collection.update_one(
            {"_id": ObjectId(session["user_id"])},
            {"$set": update_data}
        )

        return redirect(url_for("host.dashboard"))

    return render_template("host/profile.html", user=user)
