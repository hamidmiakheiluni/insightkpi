from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from .models import db, KPIEntry

kpi_bp = Blueprint("kpi", __name__, url_prefix="/kpi")

def _get_entry_or_404(kpi_id: int) -> KPIEntry:
    entry = KPIEntry.query.filter_by(id=kpi_id, user_id=current_user.id).first()
    if not entry:
        abort(404)
    return entry

@kpi_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_kpi():
    if request.method == "POST":
        name = (request.form.get("kpi_name") or "").strip()
        date_str = (request.form.get("kpi_date") or "").strip()
        value_raw = (request.form.get("value") or "").strip()
        notes = (request.form.get("notes") or "").strip()

        target_raw = (request.form.get("target_value") or "").strip()
        direction = "higher"  # default
        warning_buffer_pct = 5.0  # default

        if not name or not date_str or not value_raw:
            flash("Please fill in KPI name, date, and value.", "danger")
            return render_template("kpi_form.html", mode="add", entry=None)

        try:
            value = float(value_raw)
        except ValueError:
            flash("Value must be a number.", "danger")
            return render_template("kpi_form.html", mode="add", entry=None)

        target_value = float(target_raw) if target_raw else None

        try:
            warning_buffer_pct = float(warning_buffer_raw)
        except ValueError:
            warning_buffer_pct = 5.0

        direction = direction if direction in ("higher", "lower") else "higher"

        entry = KPIEntry(
            user_id=current_user.id,
            kpi_name=name,
            kpi_date=datetime.strptime(date_str, "%Y-%m-%d").date(),
            value=value,
            notes=notes,
            target_value=target_value,
            direction=direction,
            tolerance_pct=warning_buffer_pct,
        )

        db.session.add(entry)
        db.session.commit()
        flash("KPI entry added.", "success")
        return redirect(url_for("dash.dashboard"))

    return render_template("kpi_form.html", mode="add", entry=None)

@kpi_bp.route("/<int:kpi_id>")
@login_required
def view_kpi(kpi_id: int):
    entry = _get_entry_or_404(kpi_id)
    return render_template("kpi_detail.html", entry=entry)

@kpi_bp.route("/<int:kpi_id>/edit", methods=["GET", "POST"])
@login_required
def edit_kpi(kpi_id: int):
    entry = _get_entry_or_404(kpi_id)

    if request.method == "POST":
        name = (request.form.get("kpi_name") or "").strip()
        date_str = (request.form.get("kpi_date") or "").strip()
        value_raw = (request.form.get("value") or "").strip()
        notes = (request.form.get("notes") or "").strip()

        target_raw = (request.form.get("target_value") or "").strip()
        direction = (request.form.get("direction") or "higher").strip().lower()
        warning_buffer_raw = (request.form.get("tolerance_pct") or "5").strip()

        if not name or not date_str or not value_raw:
            flash("Please fill in KPI name, date, and value.", "danger")
            return render_template("kpi_form.html", mode="edit", entry=entry)

        try:
            value = float(value_raw)
        except ValueError:
            flash("Value must be a number.", "danger")
            return render_template("kpi_form.html", mode="edit", entry=entry)

        target_value = float(target_raw) if target_raw else None

        try:
            warning_buffer_pct = float(warning_buffer_raw)
        except ValueError:
            warning_buffer_pct = entry.tolerance_pct if entry.tolerance_pct is not None else 5.0

        direction = direction if direction in ("higher", "lower") else "higher"

        entry.kpi_name = name
        entry.kpi_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        entry.value = value
        entry.notes = notes
        entry.target_value = target_value
        entry.direction = direction
        entry.tolerance_pct = warning_buffer_pct

        db.session.commit()
        flash("KPI entry updated.", "success")
        return redirect(url_for("kpi.view_kpi", kpi_id=entry.id))

    return render_template("kpi_form.html", mode="edit", entry=entry)

@kpi_bp.route("/<int:kpi_id>/delete", methods=["POST"])
@login_required
def delete_kpi(kpi_id: int):
    entry = _get_entry_or_404(kpi_id)
    db.session.delete(entry)
    db.session.commit()
    flash("KPI entry deleted.", "success")
    return redirect(url_for("dash.dashboard"))
