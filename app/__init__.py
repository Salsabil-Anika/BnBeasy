from flask import Flask, render_template

def create_app():
    app = Flask(__name__)

    # Import and register blueprints
    from .routes.auth_routes import auth_bp
    from .routes.listing_routes import listing_bp
    from .routes.review_routes import review_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(listing_bp, url_prefix="/listing")
    app.register_blueprint(review_bp, url_prefix="/review")


    @app.get("/")
    def home():
        return render_template("index.html")
    
    return app
