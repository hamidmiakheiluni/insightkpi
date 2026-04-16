# This file handles everything to do with user accounts
# Register, login, logout, profile, and 2FA setup

import pyotp
import qrcode
import io
import base64

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from .models import db, User, log_activity

# Create the auth blueprint so Flask knows these are auth related routes
auth_bp = Blueprint("auth", __name__)


# REGISTER
# This route lets a new user create an account
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Grab the values the user typed into the form
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        # Make sure all fields are filled in
        if not username or not email or not password:
            flash("Username, email, and password are required.", "danger")
            return redirect(url_for("auth.register"))

        # Check the username is not already taken
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "warning")
            return redirect(url_for("auth.register"))

        # Check the email is not already registered
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("auth.register"))

        # The very first user to register automatically becomes admin
        first_admin = User.query.filter_by(is_admin=True).first()

        # Create the new user object
        user = User(
            username=username,
            email=email,
            is_admin=(first_admin is None)
        )
        # Hash the password before saving it
        user.set_password(password)

        # Save the new user to the database
        db.session.add(user)
        db.session.commit()

        # Record this action in the activity log
        log_activity(user.id, "Account created",
                     f"New user registered with username '{username}'")

        flash("Account created. Please log in.", "success")
        return redirect(url_for("auth.login"))

    # Show the register page
    return render_template("register.html")


# LOGIN STEP 1 - Check the password
# If 2FA is on, the user will be sent to a second step after this
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Get email and password from the form
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        # Look up the user by email
        user = User.query.filter_by(email=email).first()

        # If no user found or password is wrong, show an error
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("auth.login"))

        # If this user has 2FA turned on, save their ID in the session
        # and send them to the code verification page
        if user.totp_enabled:
            session["2fa_user_id"] = user.id
            return redirect(url_for("auth.verify_2fa"))

        # No 2FA so log them straight in
        login_user(user)
        log_activity(user.id, "Logged in", "User signed into the system")
        return redirect(url_for("dash.home"))

    # Show the login page
    return render_template("login.html")


# LOGIN STEP 2 - Check the 6 digit code from the authenticator app
# This only runs if the user has 2FA turned on
@auth_bp.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa():
    # Get the user ID we saved in the session during step 1
    user_id = session.get("2fa_user_id")

    # If there is no user ID in the session, send them back to login
    if not user_id:
        return redirect(url_for("auth.login"))

    # Look up the user in the database
    user = User.query.get(user_id)
    if not user:
        session.pop("2fa_user_id", None)
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        # Get the 6 digit code the user typed in
        code = request.form.get("code", "").strip()

        # Create a TOTP object using the user's secret key
        totp = pyotp.TOTP(user.totp_secret)

        # Check if the code is correct
        if totp.verify(code):
            # Code is correct so clear the session and log them in
            session.pop("2fa_user_id", None)
            login_user(user)
            log_activity(user.id, "Logged in (2FA)", "User passed 2FA verification")
            return redirect(url_for("dash.home"))
        else:
            # Code is wrong, show an error
            flash("Invalid code. Please try again.", "danger")
            return redirect(url_for("auth.verify_2fa"))

    # Show the 2FA code entry page
    return render_template("verify_2fa.html")


# LOGOUT
# Logs the user out and sends them to the login page
@auth_bp.route("/logout")
@login_required
def logout():
    log_activity(current_user.id, "Logged out", "User signed out of the system")
    logout_user()
    return redirect(url_for("auth.login"))


# PROFILE
# Shows the profile page and handles password changes
@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        # Get the passwords from the form
        current_password = request.form.get("current_password")
        new_password     = request.form.get("new_password")

        # Check the current password is correct before allowing a change
        if not current_user.check_password(current_password):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("auth.profile"))

        # New password cannot be blank
        if not new_password:
            flash("New password cannot be empty.", "danger")
            return redirect(url_for("auth.profile"))

        # Save the new hashed password
        current_user.set_password(new_password)
        db.session.commit()

        log_activity(current_user.id, "Password changed",
                     "User updated account password")

        flash("Password updated successfully.", "success")
        return redirect(url_for("auth.profile"))

    # Show the profile page
    return render_template("profile.html")


# 2FA SETUP STEP 1 - Generate and show the QR code
# The user scans this with their authenticator app
@auth_bp.route("/setup-2fa")
@login_required
def setup_2fa():
    # Generate a random secret key for this user
    # We only save it once they confirm with a valid code
    secret = pyotp.random_base32()

    # Store the secret temporarily in the session
    session["totp_pending_secret"] = secret

    # Create a TOTP object and generate a link the QR code will encode
    totp = pyotp.TOTP(secret)
    uri  = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="InsightKPI"
    )

    # Turn the link into a QR code image and convert it to base64
    # so it can be embedded directly in the HTML page
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    # Show the setup page with the QR code and secret
    return render_template("setup_2fa.html", qr_b64=qr_b64, secret=secret)


# 2FA SETUP STEP 2 - Confirm the code and activate 2FA
# The user enters the code from their app to prove it worked
@auth_bp.route("/confirm-2fa", methods=["POST"])
@login_required
def confirm_2fa():
    # Get the code the user typed in
    code   = request.form.get("code", "").strip()

    # Get the secret we stored in the session during step 1
    secret = session.get("totp_pending_secret")

    # If the session expired the secret will be gone
    if not secret:
        flash("Session expired. Please try enabling 2FA again.", "danger")
        return redirect(url_for("auth.setup_2fa"))

    # Check if the code matches the secret
    totp = pyotp.TOTP(secret)
    if totp.verify(code):
        # Code is correct so save the secret and turn on 2FA for this user
        current_user.totp_secret  = secret
        current_user.totp_enabled = True
        db.session.commit()

        # Clear the temporary secret from the session
        session.pop("totp_pending_secret", None)

        log_activity(current_user.id, "2FA enabled", "User activated two-factor authentication")
        flash("Two-factor authentication enabled successfully!", "success")
    else:
        # Code was wrong, send them back to try again
        flash("Invalid code. Please scan the QR code again and retry.", "danger")
        return redirect(url_for("auth.setup_2fa"))

    return redirect(url_for("auth.profile"))


# 2FA DISABLE
# Lets the user turn off 2FA after confirming their password
@auth_bp.route("/disable-2fa", methods=["POST"])
@login_required
def disable_2fa():
    # Get the password the user typed in
    password = request.form.get("password", "").strip()

    # Check the password is correct before disabling 2FA
    if not current_user.check_password(password):
        flash("Incorrect password. 2FA was not disabled.", "danger")
        return redirect(url_for("auth.profile"))

    # Clear the secret and turn off 2FA
    current_user.totp_secret  = None
    current_user.totp_enabled = False
    db.session.commit()

    log_activity(current_user.id, "2FA disabled", "User deactivated two-factor authentication")
    flash("Two-factor authentication has been disabled.", "warning")
    return redirect(url_for("auth.profile"))