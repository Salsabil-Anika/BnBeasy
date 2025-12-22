from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

# Initialize extensions
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = "auth.login"  # redirect here if not logged in

def create_app():
    app = Flask(__name__)
    app.secret_key = "your_secret_key"

    # Initialize extensions with app
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Import and register blueprints
    from .routes.auth_routes import auth_bp
    from .routes.travellerRoute import traveller_bp
    from .routes.hostRoute import host_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(traveller_bp)
    app.register_blueprint(host_bp)

    return app
