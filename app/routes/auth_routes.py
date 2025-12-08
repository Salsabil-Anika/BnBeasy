from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, UserMixin
from .. import bcrypt, login_manager
from ..config import users_collection
from bson.objectid import ObjectId



auth_bp = Blueprint("auth", __name__)

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data["_id"])
        self.username = user_data["username"]
        self.password = user_data["password"]

@login_manager.user_loader
def load_user(user_id):
    user_data = users_collection.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']  # Traveller or Host

        user = users_collection.find_one({"email": email, "role": role})

        if user and bcrypt.check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['role'] = role

            if role == 'traveller':
                return redirect(url_for('traveller.dashboard'))
            else:
                return redirect(url_for('host.profile'))
        else:
            flash("Invalid credentials or role selected")
            return redirect(url_for('auth.login'))

    return render_template('login.html')

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        # Check if email already exists
        if users_collection.find_one({"username": username}):
            flash("Username already exists")
            return redirect(url_for("auth.register"))
        if users_collection.find_one({"email": email}):
            flash("Email already registered")
            return redirect(url_for("auth.register"))

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        users_collection.insert_one({
            "username": username,
            "email": email,
            "password": hashed_pw,
            "role": role
        })

        flash("Account created! You can now log in.")
        return redirect(url_for("auth.login"))

    return render_template("login.html")


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
