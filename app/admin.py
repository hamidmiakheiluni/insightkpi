# This file handles everything on the admin side of the app
# Only users with is_admin set to True can access these pages

from functools import wraps
from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import db, User, KPIEntry, ActivityLog, log_activity

# Create the admin blueprint with /admin as the URL prefix
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# This is a custom decorator that blocks non admin users
# It wraps around any route that only admins should access
def admin_required(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        # If the logged in user is not an admin, show a 403 forbidden error
        if not current_user.is_admin:
            abort(403)
        return func(*args, **kwargs)
    return wrapper


# ADMIN DASHBOARD
# Shows a summary of all users, all KPI entries, and recent activity
@admin_bp.route("/")
@admin_required
def admin_dashboard():
    # Get all users ordered by ID
    users = User.query.order_by(User.id.asc()).all()
    # Get all KPI entries ordered by most recent date first
    kpis = KPIEntry.query.order_by(KPIEntry.kpi_date.desc()).all()
    # Get the 100 most recent activity log entries
    activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(100).all()

    # Count totals to display in the summary cards at the top
    total_users = len(users)
    total_kpis = len(kpis)
    total_admins = len([u for u in users if u.is_admin])

    return render_template(
        "admin.html",
        users=users,
        kpis=kpis,
        activities=activities,
        total_users=total_users,
        total_kpis=total_kpis,
        total_admins=total_admins
    )


# EDIT USER
# Allows an admin to change a user's username, email, or password
@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    # Find the user or show a 404 error if they do not exist
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        # Get the new values from the form
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("new_password", "").strip()

        # Username and email are required fields
        if not username or not email:
            flash("Username and email are required.", "danger")
            return redirect(url_for("admin.edit_user", user_id=user.id))

        # Check no other user already has this username
        existing_username = User.query.filter(User.username == username, User.id != user.id).first()
        if existing_username:
            flash("That username is already in use.", "danger")
            return redirect(url_for("admin.edit_user", user_id=user.id))

        # Check no other user already has this email
        existing_email = User.query.filter(User.email == email, User.id != user.id).first()
        if existing_email:
            flash("That email is already in use.", "danger")
            return redirect(url_for("admin.edit_user", user_id=user.id))

        # Update the user's details
        user.username = username
        user.email = email

        # Only update the password if a new one was provided
        if new_password:
            user.set_password(new_password)

        # Save changes to the database
        db.session.commit()

        # Record what the admin did
        log_activity(
            current_user.id,
            "Admin edited user",
            f"Updated user #{user.id} ({user.username})"
        )

        flash("User updated successfully.", "success")
        return redirect(url_for("admin.admin_dashboard"))

    # Show the edit user form
    return render_template("admin_edit_user.html", user=user)


# DELETE USER
# Allows an admin to permanently delete a user and all their data
@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    # Find the user or show a 404 error if they do not exist
    user = User.query.get_or_404(user_id)

    # Prevent the admin from deleting their own account
    if user.id == current_user.id:
        flash("You cannot delete your own admin account.", "danger")
        return redirect(url_for("admin.admin_dashboard"))

    # Delete all KPI entries belonging to this user
    KPIEntry.query.filter_by(user_id=user.id).delete()
    # Delete all activity logs belonging to this user
    ActivityLog.query.filter_by(user_id=user.id).delete()

    # Save the name and ID before deleting so we can log it
    deleted_username = user.username
    deleted_id = user.id

    # Delete the user from the database
    db.session.delete(user)
    db.session.commit()

    # Record what the admin did
    log_activity(
        current_user.id,
        "Admin deleted user",
        f"Deleted user #{deleted_id} ({deleted_username})"
    )

    flash("User deleted successfully.", "success")
    return redirect(url_for("admin.admin_dashboard"))