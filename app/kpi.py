from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from .models import db, KPIEntry, log_activity

# Create KPI blueprint (all routes start with /kpi)
kpi_bp = Blueprint("kpi", __name__, url_prefix="/kpi")


# Helper function to safely get a KPI belonging to the logged-in user
def _get_entry_or_404(kpi_id: int) -> KPIEntry:
    entry = KPIEntry.query.filter_by(id=kpi_id, user_id=current_user.id).first()
    if not entry:
        abort(404)  # Prevents access to other users’ data
    return entry


# =========================
# ADD KPI
# =========================
@kpi_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_kpi():
    if request.method == "POST":

        # Get data from form
        name = (request.form.get("kpi_name") or "").strip()
        date_str = (request.form.get("kpi_date") or "").strip()
        value_raw = (request.form.get("value") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        target_raw = (request.form.get("target_value") or "").strip()

        # Get extra logic fields from form
        direction = request.form.get("direction") or "higher"
        tolerance_raw = request.form.get("tolerance_pct") or "5"

        # Basic validation
        if not name or not date_str or not value_raw:
            flash("Please fill in KPI name, date, and value.", "danger")
            return render_template("kpi_form.html", mode="add", entry=None)

        # Convert value to float
        try:
            value = float(value_raw)
        except ValueError:
            flash("Value must be a number.", "danger")
            return render_template("kpi_form.html", mode="add", entry=None)

        # Convert target if provided
        try:
            target_value = float(target_raw) if target_raw else None
        except ValueError:
            flash("Target must be a number.", "danger")
            return render_template("kpi_form.html", mode="add", entry=None)

        # Convert tolerance %
        try:
            tolerance = float(tolerance_raw)
        except ValueError:
            tolerance = 5.0

        # Convert date string to actual date
        try:
            kpi_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Please enter a valid date.", "danger")
            return render_template("kpi_form.html", mode="add", entry=None)

        # Create KPI object
        entry = KPIEntry(
            user_id=current_user.id,
            kpi_name=name,
            kpi_date=kpi_date,
            value=value,
            notes=notes,
            target_value=target_value,
            direction=direction,
            tolerance_pct=tolerance,
        )

        # Save to database
        db.session.add(entry)
        db.session.commit()

        # Log activity
        log_activity(current_user.id, "KPI added", f"Added KPI '{name}'")

        flash("KPI added successfully.", "success")
        return redirect(url_for("dash.dashboard"))

    return render_template("kpi_form.html", mode="add", entry=None)


# =========================
# VIEW KPI
# =========================
@kpi_bp.route("/<int:kpi_id>")
@login_required
def view_kpi(kpi_id: int):
    entry = _get_entry_or_404(kpi_id)

    log_activity(current_user.id, "KPI viewed", f"Viewed KPI '{entry.kpi_name}'")

    return render_template("kpi_detail.html", entry=entry)


# =========================
# EDIT KPI
# =========================
@kpi_bp.route("/<int:kpi_id>/edit", methods=["GET", "POST"])
@login_required
def edit_kpi(kpi_id: int):
    entry = _get_entry_or_404(kpi_id)

    if request.method == "POST":

        # Get updated values
        name = (request.form.get("kpi_name") or "").strip()
        date_str = (request.form.get("kpi_date") or "").strip()
        value_raw = (request.form.get("value") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        target_raw = (request.form.get("target_value") or "").strip()

        direction = request.form.get("direction") or "higher"
        tolerance_raw = request.form.get("tolerance_pct") or "5"

        if not name or not date_str or not value_raw:
            flash("Please fill in KPI name, date, and value.", "danger")
            return render_template("kpi_form.html", mode="edit", entry=entry)

        try:
            value = float(value_raw)
        except ValueError:
            flash("Value must be a number.", "danger")
            return render_template("kpi_form.html", mode="edit", entry=entry)

        try:
            target_value = float(target_raw) if target_raw else None
        except ValueError:
            flash("Target must be a number.", "danger")
            return render_template("kpi_form.html", mode="edit", entry=entry)

        try:
            tolerance = float(tolerance_raw)
        except ValueError:
            tolerance = entry.tolerance_pct or 5.0

        try:
            kpi_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Please enter a valid date.", "danger")
            return render_template("kpi_form.html", mode="edit", entry=entry)

        # Update object
        entry.kpi_name = name
        entry.kpi_date = kpi_date
        entry.value = value
        entry.notes = notes
        entry.target_value = target_value
        entry.direction = direction
        entry.tolerance_pct = tolerance

        db.session.commit()

        log_activity(current_user.id, "KPI edited", f"Edited KPI '{name}'")

        flash("KPI updated successfully.", "success")
        return redirect(url_for("dash.dashboard"))

    return render_template("kpi_form.html", mode="edit", entry=entry)


# =========================
# DELETE KPI
# =========================
@kpi_bp.route("/<int:kpi_id>/delete", methods=["GET", "POST"])
@login_required
def delete_kpi(kpi_id: int):
    entry = _get_entry_or_404(kpi_id)
    name = entry.kpi_name

    db.session.delete(entry)
    db.session.commit()

    log_activity(current_user.id, "KPI deleted", f"Deleted KPI '{name}'")

    flash("KPI deleted.", "success")
    return redirect(url_for("dash.dashboard"))