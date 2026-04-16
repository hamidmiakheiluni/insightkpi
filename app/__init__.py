# This file creates and configures the Flask app
# It connects all the blueprints, sets up the database, and handles login

import os
from flask import Flask
from flask_login import LoginManager
from sqlalchemy import inspect, text

from .models import db, User

# Set up the login manager which handles user sessions
login_manager = LoginManager()
# If a user tries to visit a page they need to be logged in for,
# send them to the login page
login_manager.login_view = "auth.login"
# Do not show a default flash message when redirecting to login
login_manager.login_message = None


# This function checks the database structure and adds any missing columns
# It is used to safely update the database without losing existing data
def _ensure_schema(app):
    with app.app_context():
        # Check what tables already exist in the database
        inspector = inspect(db.engine)

        if "users" in inspector.get_table_names():
            # Get the list of column names in the users table
            columns = [col["name"] for col in inspector.get_columns("users")]

            # Add the is_admin column if it does not exist yet
            if "is_admin" not in columns:
                db.session.execute(
                    text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
                )

            # Add email_verified column if it does not exist
            # This is kept for backwards compatibility even if email verification is not used
            if "email_verified" not in columns:
                db.session.execute(
                    text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0")
                )

            # Add email_verified_at column if it does not exist
            if "email_verified_at" not in columns:
                db.session.execute(
                    text("ALTER TABLE users ADD COLUMN email_verified_at DATETIME")
                )

            # Save the changes
            db.session.commit()


# This function builds and returns the Flask app
def create_app():
    app = Flask(__name__)

    # SECRET_KEY is used to sign session cookies and keep them secure
    # In production this should be set as an environment variable
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    # Tell Flask where to find the SQLite database file
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///kpi.db"
    # Turn off a Flask SQLAlchemy feature we do not need
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Connect the database and login manager to this app
    db.init_app(app)
    login_manager.init_app(app)

    # This tells Flask Login how to load a user from their ID stored in the session
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Import and register all the blueprints
    # Each blueprint handles a different section of the app
    from .auth import auth_bp
    from .dashboard import dash_bp
    from .kpi import kpi_bp
    from .exports import export_bp
    from .admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dash_bp)
    app.register_blueprint(kpi_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(admin_bp)

    # Create all database tables if they do not exist yet
    # Then run the schema check to add any missing columns
    with app.app_context():
        db.create_all()
        _ensure_schema(app)

    return app