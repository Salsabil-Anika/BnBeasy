from flask import render_template, request, redirect, url_for, session, flash
from models.user import add_user, verify_user, get_user_by_email
from email_details import send_otp_email
import random

from . import auth_bp

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")
    
        if get_user_by_email(email):
            return render_template("auth/register.html", status="fail", message="User already exists"), 400

        # Generate OTP
        otp = str(random.randint(100000, 999999))
        
        # Store registration data and OTP in session first
        session['reg_data'] = {
            'name': name,
            'email': email,
            'password': password,
            'role': role,
            'otp': otp
        }
        print(f"Stored reg_data in session for {email}. OTP: {otp}")
        
        # Send OTP email
        try:
            print("Calling send_otp_email...")
            send_otp_email(email, otp)
            print("Redirecting to verify_otp...")
            return redirect(url_for("auth.verify_otp"))
        except Exception as e:
            print(f"Exception during email send: {e}")
            # If email fails, clear session to prevent stale data
            session.pop('reg_data', None)
            message = f"Error sending verification email: {str(e)}"
            return render_template("auth/register.html", status="fail", message=message), 500
        
    return render_template("auth/register.html")

@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if 'reg_data' not in session:
        return redirect(url_for("auth.register"))
    
    if request.method == "POST":
        entered_otp = request.form.get("otp")
        reg_data = session['reg_data']
        
        if entered_otp == reg_data['otp']:
            # OTP is correct, add user to database
            add_user(reg_data['name'], reg_data['email'], reg_data['password'], reg_data['role'])
            session.pop('reg_data', None)
            return render_template("auth/login.html", status="success", message="Email verified! User registered successfully. Please login.")
        else:
            return render_template("auth/verify_otp.html", status="fail", message="Invalid OTP. Please try again.")
            
    return render_template("auth/verify_otp.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = verify_user(email, password)

        if not user:
            return render_template("auth/login.html", error="Invalid credentials")


        session["user_id"] = str(user["_id"])
        session["role"] = user["role"]
        # store a friendly identifier used in templates
        session["user"] = user.get("email") or user.get("name")
        
        # Store name parts for profile/review display
        full_name = user.get("name", "")
        parts = full_name.split(" ", 1)
        session["first_name"] = parts[0] if parts else ""
        session["last_name"] = parts[1] if len(parts) > 1 else ""
        session["name"] = full_name

        if user["role"] == "host":
            return redirect(url_for("host.dashboard"))
        else:
            return redirect(url_for("traveller.home"))

    return render_template("auth/login.html")

@auth_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user", None)
    session.pop("role", None)
    return redirect(url_for("auth.login"))
