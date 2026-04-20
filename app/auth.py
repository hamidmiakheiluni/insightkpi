# This file handles user authentication:
# - Register
# - Login
# - Logout
# - Profile (change password)
# - Two-Factor Authentication (2FA)

import pyotp
import qrcode
import io
import base64

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from .models import db, User, log_activity

# Create blueprint for authentication routes
auth_bp = Blueprint("auth", __name__)


# =========================
# REGISTER
# =========================
# Allows a new user to create an account
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        # Get user input from form
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        # Basic validation
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("auth.register"))

        # Check if username/email already exists
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "warning")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("auth.register"))

        # First user becomes admin
        first_admin = User.query.filter_by(is_admin=True).first()

        user = User(
            username=username,
            email=email,
            is_admin=(first_admin is None)
        )

        # Store hashed password
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Log activity
        log_activity(user.id, "Account created", f"User {username} registered")

        flash("Account created. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# =========================
# LOGIN
# =========================
# Logs user in and checks credentials
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(email=email).first()

        # Validate credentials
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("auth.login"))

        # If 2FA enabled → go to verification
        if user.totp_enabled:
            session["2fa_user_id"] = user.id
            return redirect(url_for("auth.verify_2fa"))

        # Otherwise log in normally
        login_user(user)
        log_activity(user.id, "Login", "User logged in")

        return redirect(url_for("dash.home"))

    return render_template("login.html")


# =========================
# VERIFY 2FA
# =========================
# Verifies 6-digit code from authenticator app
@auth_bp.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa():
    user_id = session.get("2fa_user_id")

    if not user_id:
        return redirect(url_for("auth.login"))

    user = User.query.get(user_id)

    # If user missing or no secret → reset flow
    if not user or not user.totp_secret:
        session.pop("2fa_user_id", None)
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()

        # Generate TOTP using stored secret
        totp = pyotp.TOTP(user.totp_secret)

        # Verify code (valid_window allows small time delay)
        if totp.verify(code, valid_window=2):
            session.pop("2fa_user_id", None)
            login_user(user)

            log_activity(user.id, "Login (2FA)", "User passed 2FA")

            return redirect(url_for("dash.home"))

        flash("Invalid code. Try again.", "danger")

    return render_template("verify_2fa.html")


# =========================
# PROFILE
# =========================
# Allows user to change password
@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":

        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")

        # Check current password
        if not current_user.check_password(current_password):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("auth.profile"))

        # Update password
        current_user.set_password(new_password)
        db.session.commit()

        log_activity(current_user.id, "Password changed", "User updated password")

        flash("Password updated successfully.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("profile.html")


# =========================
# SETUP 2FA
# =========================
# Generates QR code for authenticator app
@auth_bp.route("/setup-2fa")
@login_required
def setup_2fa():

    # Only generate once per session
    if "temp_2fa_secret" not in session:
        session["temp_2fa_secret"] = pyotp.random_base32()

    secret = session["temp_2fa_secret"]

    # Create QR code URI
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name="InsightKPI"
    )

    # Generate QR image
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    return render_template("setup_2fa.html", qr_b64=qr_b64, secret=secret)


# =========================
# CONFIRM 2FA
# =========================
# Confirms correct code before enabling 2FA
@auth_bp.route("/confirm-2fa", methods=["POST"])
@login_required
def confirm_2fa():
    code = request.form.get("code", "").strip()
    secret = session.get("temp_2fa_secret")

    if not secret:
        flash("Session expired. Try again.", "danger")
        return redirect(url_for("auth.setup_2fa"))

    totp = pyotp.TOTP(secret)

    if totp.verify(code, valid_window=2):

        # Save secret to database
        current_user.totp_secret = secret
        current_user.totp_enabled = True
        db.session.commit()

        session.pop("temp_2fa_secret", None)

        log_activity(current_user.id, "2FA enabled", "User enabled 2FA")

        flash("2FA enabled successfully.", "success")
        return redirect(url_for("auth.profile"))

    flash("Invalid code. Try again.", "danger")
    return redirect(url_for("auth.setup_2fa"))


# =========================
# DISABLE 2FA
# =========================
@auth_bp.route("/disable-2fa", methods=["POST"])
@login_required
def disable_2fa():
    password = request.form.get("password")

    # Confirm password before disabling
    if not current_user.check_password(password):
        flash("Incorrect password.", "danger")
        return redirect(url_for("auth.profile"))

    current_user.totp_secret = None
    current_user.totp_enabled = False
    db.session.commit()

    log_activity(current_user.id, "2FA disabled", "User disabled 2FA")

    flash("2FA disabled.", "success")
    return redirect(url_for("auth.profile"))


# =========================
# LOGOUT
# =========================
@auth_bp.route("/logout")
@login_required
def logout():
    log_activity(current_user.id, "Logout", "User logged out")
    logout_user()
    return redirect(url_for("auth.login"))