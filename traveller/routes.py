from flask import render_template, request
from . import traveller_bp
from config import listings_collection, users_collection
from bson.objectid import ObjectId

@traveller_bp.route('/home')
def home():
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
    
    query = {}
    
    city = request.args.get("city")
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
        
    price = request.args.get("price")
    if price:
        try:
            query["price"] = {"$lte": int(price)}
        except ValueError:
            pass
            
    amenities = request.args.getlist("amenities")
    if amenities:
        query["amenities"] = {"$all": amenities}
    
    listings = list(listings_collection.find(query))
    return render_template("traveller/home.html", listings=listings)

@traveller_bp.route("/profile")
def profile():
    if "user_id" not in session or session.get("role") != "traveller":
        return redirect(url_for("auth.login"))
    
    user = users_collection.find_one({"_id": ObjectId(session["user_id"])})
    return render_template("traveller/profile.html", user=user)
