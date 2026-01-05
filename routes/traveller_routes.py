from flask import render_template, session, redirect, url_for
from config import users_collection
from bson.objectid import ObjectId

# Import blueprint
from . import traveller_bp

@traveller_bp.route("/profile")
def profile():
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
    
    user = users_collection.find_one({"_id": ObjectId(session["user_id"])})
    return render_template("traveller/profile.html", user=user)
