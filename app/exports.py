from flask import Blueprint, Response, request
from flask_login import login_required, current_user
from .models import KPIEntry
from reportlab.pdfgen import canvas
from io import BytesIO

export_bp = Blueprint("export", __name__, url_prefix="/export")


@export_bp.route("/pdf")
@login_required
def export_pdf():
    entries = KPIEntry.query.filter_by(user_id=current_user.id).all()

    buffer = BytesIO()
    c = canvas.Canvas(buffer)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, "KPI Performance Report")

    c.setFont("Helvetica", 10)
    y = 770
    c.drawString(50, y, "KPI Name")
    c.drawString(200, y, "Date")
    c.drawString(300, y, "Value")
    c.drawString(380, y, "Notes")
    y -= 20

    for e in entries:
        c.drawString(50, y, str(e.kpi_name))
        c.drawString(200, y, str(e.kpi_date))
        c.drawString(300, y, str(e.value))
        c.drawString(380, y, (e.notes or "")[:40])
        y -= 15

        if y < 50:
            c.showPage()
            y = 800

    c.save()
    buffer.seek(0)

    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=kpi_report.pdf"}
    )


@export_bp.route("/csv")
@login_required
def export_csv():
    # Optional filters from query string (same as dashboard)
    kpi_filter = (request.args.get("kpi_name") or "").strip()
    start = request.args.get("start")
    end = request.args.get("end")

    q = KPIEntry.query.filter_by(user_id=current_user.id)

    if kpi_filter:
        q = q.filter(KPIEntry.kpi_name == kpi_filter)
    if start:
        q = q.filter(KPIEntry.kpi_date >= start)
    if end:
        q = q.filter(KPIEntry.kpi_date <= end)

    entries = q.order_by(KPIEntry.kpi_date.asc()).all()

    # Build CSV text manually (simple + reliable)
    lines = ["kpi_name,date,value,notes"]

    for e in entries:
        name = str(e.kpi_name).replace(",", " ")
        date = e.kpi_date.isoformat()
        value = str(e.value)
        notes = (e.notes or "").replace(",", " ")
        lines.append(f"{name},{date},{value},{notes}")

    csv_text = "\n".join(lines)

    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=kpi_data.csv"}
    )

