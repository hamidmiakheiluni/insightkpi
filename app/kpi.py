# This file handles adding, viewing, editing, and deleting KPI entries
# All routes here require the user to be logged in

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from .models import db, KPIEntry, log_activity

# Create the KPI blueprint with /kpi as the URL prefix
kpi_bp = Blueprint("kpi", __name__, url_prefix="/kpi")


# This helper function looks up a KPI entry by ID
# It also checks the entry belongs to the logged in user
# If not found it shows a 404 error
def _get_entry_or_404(kpi_id: int) -> KPIEntry:
    entry = KPIEntry.query.filter_by(id=kpi_id, user_id=current_user.id).first()
    if not entry:
        abort(404)
    return entry


# ADD KPI
# Shows the form to add a new KPI and saves it when submitted
@kpi_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_kpi():
    if request.method == "POST":
        # Get all the values from the form
        name = (request.form.get("kpi_name") or "").strip()
        date_str = (request.form.get("kpi_date") or "").strip()
        value_raw = (request.form.get("value") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        target_raw = (request.form.get("target_value") or "").strip()

        # Default direction and tolerance values
        direction = "higher"
        warning_buffer_pct = 5.0

        # Name, date, and value are all required
        if not name or not date_str or not value_raw:
            flash("Please fill in KPI name, date, and value.", "danger")
            return render_template("kpi_form.html", mode="add", entry=None)

        # Make sure value is a valid number
        try:
            value = float(value_raw)
        except ValueError:
            flash("Value must be a number.", "danger")
            return render_template("kpi_form.html", mode="add", entry=None)

        # Target is optional but must be a number if provided
        try:
            target_value = float(target_raw) if target_raw else None
        except ValueError:
            flash("Target must be a number.", "danger")
            return render_template("kpi_form.html", mode="add", entry=None)

        # Make sure the date is in the correct format
        try:
            kpi_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Please enter a valid date.", "danger")
            return render_template("kpi_form.html", mode="add", entry=None)

        # Create the new KPI entry object
        entry = KPIEntry(
            user_id=current_user.id,
            kpi_name=name,
            kpi_date=kpi_date,
            value=value,
            notes=notes,
            target_value=target_value,
            direction=direction,
            tolerance_pct=warning_buffer_pct,
        )

        # Save the entry to the database
        db.session.add(entry)
        db.session.commit()

        # Record the action in the activity log
        log_activity(
            current_user.id,
            "KPI added",
            f"Added KPI '{name}' with value {value}"
        )

        flash("KPI entry added.", "success")
        return redirect(url_for("dash.dashboard"))

    # Show the empty add KPI form
    return render_template("kpi_form.html", mode="add", entry=None)


# VIEW KPI
# Shows the full details of a single KPI entry
@kpi_bp.route("/<int:kpi_id>")
@login_required
def view_kpi(kpi_id: int):
    # Find the entry or show 404 if it does not belong to this user
    entry = _get_entry_or_404(kpi_id)

    # Record that the user viewed this KPI
    log_activity(
        current_user.id,
        "KPI viewed",
        f"Viewed KPI '{entry.kpi_name}'"
    )

    return render_template("kpi_detail.html", entry=entry)


# EDIT KPI
# Shows a pre-filled form and saves the updated values when submitted
@kpi_bp.route("/<int:kpi_id>/edit", methods=["GET", "POST"])
@login_required
def edit_kpi(kpi_id: int):
    # Find the entry or show 404 if it does not belong to this user
    entry = _get_entry_or_404(kpi_id)

    if request.method == "POST":
        # Get all the updated values from the form
        name = (request.form.get("kpi_name") or "").strip()
        date_str = (request.form.get("kpi_date") or "").strip()
        value_raw = (request.form.get("value") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        target_raw = (request.form.get("target_value") or "").strip()

        # Keep the existing tolerance, default to 5 if not set
        direction = "higher"
        warning_buffer_pct = entry.tolerance_pct if entry.tolerance_pct is not None else 5.0

        # Name, date, and value are required
        if not name or not date_str or not value_raw:
            flash("Please fill in KPI name, date, and value.", "danger")
            return render_template("kpi_form.html", mode="edit", entry=entry)

        # Make sure value is a valid number
        try:
            value = float(value_raw)
        except ValueError:
            flash("Value must be a number.", "danger")
            return render_template("kpi_form.html", mode="edit", entry=entry)

        # Target is optional but must be a number if provided
        try:
            target_value = float(target_raw) if target_raw else None
        except ValueError:
            flash("Target must be a number.", "danger")
            return render_template("kpi_form.html", mode="edit", entry=entry)

        # Make sure the date is in the correct format
        try:
            kpi_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Please enter a valid date.", "danger")
            return render_template("kpi_form.html", mode="edit", entry=entry)

        # Update the entry with the new values
        entry.kpi_name = name
        entry.kpi_date = kpi_date
        entry.value = value
        entry.notes = notes
        entry.target_value = target_value
        entry.direction = direction
        entry.tolerance_pct = warning_buffer_pct

        # Save the changes to the database
        db.session.commit()

        # Record the action in the activity log
        log_activity(
            current_user.id,
            "KPI edited",
            f"Edited KPI '{name}'"
        )

        flash("KPI entry updated.", "success")
        return redirect(url_for("dash.dashboard"))

    # Show the edit form with the existing values pre-filled
    return render_template("kpi_form.html", mode="edit", entry=entry)


# DELETE KPI
# Permanently removes a KPI entry from the database
@kpi_bp.route("/<int:kpi_id>/delete", methods=["GET", "POST"])
@login_required
def delete_kpi(kpi_id: int):
    # Find the entry or show 404 if it does not belong to this user
    entry = _get_entry_or_404(kpi_id)
    kpi_name = entry.kpi_name

    # Delete the entry from the database
    db.session.delete(entry)
    db.session.commit()

    # Record the action in the activity log
    log_activity(
        current_user.id,
        "KPI deleted",
        f"Deleted KPI '{kpi_name}'"
    )

    flash("KPI entry deleted.", "success")
    return redirect(url_for("dash.dashboard"))