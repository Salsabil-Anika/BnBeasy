from flask import Blueprint, render_template, request, redirect, url_for, session
import random
from email_details import send_otp_email
from models.user import add_user, verify_user, set_verified

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    message = ""
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")
    
        if verify_user(email, password):
            message="User already exists"
            return render_template("register.html", status="fail", message=message),400

        else:
            otp = str(random.randint(100000, 999999))
            try:
                send_otp_email(email, otp)
                add_user(name, email, password, role, otp=otp)
                session["pending_email"] = email
                return redirect(url_for("auth.verify_otp"))
            except Exception as e:
                message = f"Error sending verification email: {str(e)}"
                return render_template("register.html", status="fail", message=message), 500
        
    return render_template("register.html", message=message)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = verify_user(email, password)

        if not user:
            return render_template("login.html", error="Invalid credentials")


        session["user_id"] = str(user["_id"])
        session["role"] = user["role"]
        # store a friendly identifier used in templates
        session["user"] = user.get("email") or user.get("name")

        if user["role"] == "host":
            return redirect(url_for("host.dashboard"))
        else:
            return redirect(url_for("traveller.home"))

    return render_template("login.html")


    

@auth_bp.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    email = session.get("pending_email")
    if not email:
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        otp_input = request.form.get("otp")
        from config import users_collection
        user = users_collection.find_one({"email": email})
        
        if user and user.get("otp") == otp_input:
            set_verified(email)
            session.pop("pending_email", None)
            return render_template("login.html", message="Email verified! Please login.")
        else:
            return render_template("verify_otp.html", error="Invalid OTP. Please try again.")

    return render_template("verify_otp.html")

@auth_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user", None)
    session.pop("role", None)
    return redirect(url_for("auth.login"))


    
