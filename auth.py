from flask import Blueprint, render_template, request, redirect, url_for, session
from models.user import add_user, verify_user

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
            add_user(name, email, password, role)
            return render_template("register.html", status="success", message="User registered"), 200
        
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


        if user["role"] == "host":
            return redirect(url_for("host.dashboard"))
        else:
            return redirect(url_for("traveller.home"))

    return render_template("login.html")


    

@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("auth.login"))


    
