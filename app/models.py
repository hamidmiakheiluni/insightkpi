# This file defines the database tables used in the app
# Each class represents one table in the database

from datetime import date, datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Create the database object that the whole app will use
db = SQLAlchemy()


# The User table stores everyone who has an account
class User(UserMixin, db.Model):
    __tablename__ = "users"

    # Each user gets a unique ID number
    id = db.Column(db.Integer, primary_key=True)
    # Username must be unique, no two users can share one
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    # Email must also be unique
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    # We never store the real password, only a hashed version for security
    password_hash = db.Column(db.String(255), nullable=False)
    # True if this user is an admin, False for regular users
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    # These two columns support two-factor authentication
    # totp_secret is the secret key used to generate 6 digit codes
    totp_secret = db.Column(db.String(32), nullable=True)
    # totp_enabled is True if the user has turned on 2FA
    totp_enabled = db.Column(db.Boolean, nullable=False, default=False)

    # This turns the plain password into a secure hash before saving
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    # This checks if the password the user typed matches the saved hash
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


# The KPIEntry table stores every KPI data point a user adds
class KPIEntry(db.Model):
    __tablename__ = "kpi_entries"

    # Each entry gets a unique ID
    id = db.Column(db.Integer, primary_key=True)
    # Links this entry to the user who created it
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # The name of the KPI for example Sales or Revenue
    kpi_name = db.Column(db.String(120), nullable=False, index=True)
    # The date this KPI value was recorded
    kpi_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    # The actual number value of the KPI
    value = db.Column(db.Float, nullable=False)
    # Optional notes the user can add for context
    notes = db.Column(db.String(500), nullable=True)

    # Optional target value to compare the KPI against
    target_value = db.Column(db.Float, nullable=True)
    # Whether higher or lower values are better for this KPI
    direction = db.Column(db.String(10), nullable=False, default="higher")
    # How close to the target is still acceptable before turning amber
    tolerance_pct = db.Column(db.Float, nullable=False, default=5.0)


# The ActivityLog table records everything users do in the app
class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    # Each log entry gets a unique ID
    id = db.Column(db.Integer, primary_key=True)
    # Links the log entry to the user who did the action
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    # A short label for what happened for example Logged in or KPI added
    action = db.Column(db.String(120), nullable=False)
    # More detail about the action
    details = db.Column(db.String(500), nullable=True)
    # The exact time the action happened
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    # This lets us access the user object directly from a log entry
    user = db.relationship("User", backref="activity_logs")


# This helper function saves a new activity log entry to the database
def log_activity(user_id: int, action: str, details: str | None = None):
    entry = ActivityLog(
        user_id=user_id,
        action=action,
        details=details or ""
    )
    db.session.add(entry)
    db.session.commit()