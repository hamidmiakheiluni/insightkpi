# This file handles exporting KPI data in different formats
# Users can download their data as a CSV file or a PDF report
# UPDATED: Now supports exporting charts from the frontend (Chart.js)

from flask import Blueprint, Response, request
from flask_login import login_required, current_user
from .models import KPIEntry
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
import base64

# Create the export blueprint with /export as the URL prefix
export_bp = Blueprint("export", __name__, url_prefix="/export")


# ---------------------------------------------------
# EXPORT PDF
# ---------------------------------------------------
# Generates a PDF report including:
# - KPI table data
# - Chart image (captured from frontend)
# ---------------------------------------------------
@export_bp.route("/pdf", methods=["POST"])
@login_required
def export_pdf():

    # 🔥 Get chart image from frontend (sent as base64)
    chart_data = request.form.get("chart_image")

    # Get all KPI entries for the logged in user
    entries = KPIEntry.query.filter_by(user_id=current_user.id).all()

    # Create an in-memory buffer to write the PDF into
    buffer = BytesIO()

    # Create PDF canvas
    c = canvas.Canvas(buffer)

    # -------------------------------
    # TITLE
    # -------------------------------
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, "KPI Performance Report")

    # -------------------------------
    # TABLE HEADERS
    # -------------------------------
    c.setFont("Helvetica", 10)
    y = 770

    c.drawString(50, y, "KPI Name")
    c.drawString(200, y, "Date")
    c.drawString(300, y, "Value")
    c.drawString(380, y, "Notes")

    y -= 20

    # -------------------------------
    # TABLE DATA
    # -------------------------------
    for e in entries:
        c.drawString(50, y, str(e.kpi_name))
        c.drawString(200, y, str(e.kpi_date))
        c.drawString(300, y, str(e.value))
        c.drawString(380, y, (e.notes or "")[:40])

        y -= 15

        # If page is full, create a new one
        if y < 200:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = 800

    # -------------------------------
    # ADD CHART IMAGE (IF EXISTS)
    # -------------------------------
    if chart_data:
        try:
            # Remove the data:image/png;base64, part
            image_data = chart_data.split(",")[1]

            # Decode base64 to bytes
            image_bytes = base64.b64decode(image_data)

            # Convert to ReportLab readable image
            image = ImageReader(BytesIO(image_bytes))

            # Create new page for chart
            c.showPage()

            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, 800, "KPI Chart")

            # Draw the chart image
            # Position: x=50, y=300
            # Size: width=500, height=300
            c.drawImage(image, 50, 300, width=500, height=300)

        except Exception as e:
            print("Error embedding chart into PDF:", e)

    # -------------------------------
    # FINALISE PDF
    # -------------------------------
    c.save()

    # Move buffer pointer to start
    buffer.seek(0)

    # Return PDF as downloadable response
    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=kpi_report.pdf"
        }
    )


# ---------------------------------------------------
# EXPORT CSV
# ---------------------------------------------------
# Exports KPI data as a CSV file
# Supports filtering (same as dashboard)
# ---------------------------------------------------
@export_bp.route("/csv")
@login_required
def export_csv():

    # Optional filters from query string
    kpi_filter = (request.args.get("kpi_name") or "").strip()
    start = request.args.get("start")
    end = request.args.get("end")

    # Base query
    q = KPIEntry.query.filter_by(user_id=current_user.id)

    # Apply filters if provided
    if kpi_filter:
        q = q.filter(KPIEntry.kpi_name == kpi_filter)

    if start:
        q = q.filter(KPIEntry.kpi_date >= start)

    if end:
        q = q.filter(KPIEntry.kpi_date <= end)

    # Order results by date
    entries = q.order_by(KPIEntry.kpi_date.asc()).all()

    # -------------------------------
    # BUILD CSV CONTENT
    # -------------------------------
    lines = ["kpi_name,date,value,notes"]

    for e in entries:
        name = str(e.kpi_name).replace(",", " ")
        date = e.kpi_date.isoformat()
        value = str(e.value)
        notes = (e.notes or "").replace(",", " ")

        lines.append(f"{name},{date},{value},{notes}")

    csv_text = "\n".join(lines)

    # Return CSV as downloadable response
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=kpi_data.csv"
        }
    )