# This file handles exporting KPI data in different formats
# Users can download their data as a CSV file or a PDF report

from flask import Blueprint, Response, request
from flask_login import login_required, current_user
from .models import KPIEntry
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Image
from reportlab.lib.pagesizes import letter
from io import BytesIO
import base64

# Create the export blueprint with /export as the URL prefix
export_bp = Blueprint("export", __name__, url_prefix="/export")


# EXPORT PDF
# Generates a simple PDF table of all the user's KPI entries
@export_bp.route("/pdf")
@login_required
def export_pdf():
    # Get all KPI entries for the logged in user
    entries = KPIEntry.query.filter_by(user_id=current_user.id).all()

    # Create an in-memory buffer to write the PDF into
    buffer = BytesIO()
    c = canvas.Canvas(buffer)

    # Write the title at the top of the page
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, "KPI Performance Report")

    # Start writing entries below the title
    c.setFont("Helvetica", 10)
    y = 770

    for e in entries:
        c.drawString(50, y, f"{e.kpi_name} - {e.value}")
        y -= 15

        # If we are near the bottom of the page, start a new page
        if y < 50:
            c.showPage()
            y = 800

    # Finish and save the PDF
    c.save()
    buffer.seek(0)

    # Send the PDF file as a download
    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=kpi_report.pdf"}
    )


# EXPORT CSV
# Generates a simple CSV file of all the user's KPI entries
@export_bp.route("/csv")
@login_required
def export_csv():
    # Get all KPI entries for the logged in user
    entries = KPIEntry.query.filter_by(user_id=current_user.id).all()

    # Start with the header row
    lines = ["kpi_name,date,value"]

    # Add one row per KPI entry
    for e in entries:
        lines.append(f"{e.kpi_name},{e.kpi_date},{e.value}")

    # Join all rows into one text block
    csv_text = "\n".join(lines)

    # Send the CSV file as a download
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=kpi_data.csv"}
    )


# EXPORT CHART PDF
# Takes a chart image sent from the browser and saves it as a PDF
@export_bp.route("/chart-pdf", methods=["POST"])
@login_required
def export_chart_pdf():
    # Get the base64 image data sent from the browser
    image_data = request.form.get("image_data")

    if not image_data:
        return "No image data", 400

    # Remove the data URL prefix to get just the base64 part
    image_data = image_data.split(",")[1]
    # Decode the base64 string back into raw image bytes
    image_bytes = base64.b64decode(image_data)

    # Create an in-memory buffer to write the PDF into
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    # Create an image object from the chart bytes and set its size
    img = Image(BytesIO(image_bytes))
    img.drawHeight = 300
    img.drawWidth = 500

    # Build the PDF with just the chart image
    doc.build([img])

    buffer.seek(0)

    # Send the PDF file as a download
    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=chart_report.pdf"}
    )


# EXPORT SUMMARY PDF
# Generates a short PDF showing only the first 10 KPI entries
@export_bp.route("/summary-pdf")
@login_required
def export_summary_pdf():
    # Get all KPI entries for the logged in user
    entries = KPIEntry.query.filter_by(user_id=current_user.id).all()

    # Create an in-memory buffer to write the PDF into
    buffer = BytesIO()
    c = canvas.Canvas(buffer)

    # Write the title at the top of the page
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, "KPI Summary Report")

    y = 750

    # Only show the first 10 entries to keep it as a summary
    for e in entries[:10]:
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"{e.kpi_name} - {e.value}")
        y -= 20

    # Finish and save the PDF
    c.save()
    buffer.seek(0)

    # Send the PDF file as a download
    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=summary_report.pdf"}
    )