# This file handles the home page and the main dashboard page
# It also contains the logic for calculating KPI status colours

from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from collections import defaultdict
from .models import KPIEntry

# Create the dashboard blueprint
dash_bp = Blueprint("dash", __name__)


# STATUS LOGIC
# This function works out whether a KPI is green, amber, or red
# based on its value, target, direction, and tolerance
def evaluate_status(value, target, direction, tolerance_pct):
    # If no target is set we cannot calculate a status
    if target is None:
        return "unknown"

    # Calculate the tolerance as an actual number based on the percentage
    tol = (tolerance_pct or 0) / 100 * target

    # For KPIs where higher is better
    if direction == "higher":
        if value >= target:
            return "green"
        elif value >= (target - tol):
            # Within the tolerance buffer so amber
            return "amber"
        else:
            return "red"
    else:
        # For KPIs where lower is better
        if value <= target:
            return "green"
        elif value <= (target + tol):
            # Within the tolerance buffer so amber
            return "amber"
        else:
            return "red"


# This function calculates the percentage change between two values
def pct_change(current, previous):
    # Cannot calculate if there is no previous value
    if previous is None or previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 2)


# HOME PAGE
# Shows a quick summary of the user's KPIs
@dash_bp.route("/")
@login_required
def home():
    # Get all KPI entries for the logged in user
    entries = KPIEntry.query.filter_by(user_id=current_user.id).all()

    # Count how many unique KPI names the user has
    total_kpis = len(set(e.kpi_name for e in entries))

    green_count = 0
    red_count = 0

    # Group entries by KPI name so we can find the latest one for each
    grouped = defaultdict(list)
    for e in entries:
        grouped[e.kpi_name].append(e)

    # For each KPI check the status of the most recent entry
    for name, items in grouped.items():
        latest = sorted(items, key=lambda x: x.kpi_date)[-1]

        status = evaluate_status(
            latest.value,
            latest.target_value,
            latest.direction,
            latest.tolerance_pct
        )

        if status == "green":
            green_count += 1
        elif status == "red":
            red_count += 1

    return render_template(
        "home.html",
        total_kpis=total_kpis,
        green_count=green_count,
        red_count=red_count
    )


# DASHBOARD PAGE
# Shows all KPI data with charts, filters, and comparison tools
@dash_bp.route("/dashboard")
@login_required
def dashboard():

    # GET FILTERS
    # Read any filter values from the URL
    selected_kpi = request.args.get("kpi_name")
    kpi1 = request.args.get("kpi1")
    kpi2 = request.args.get("kpi2")
    start = request.args.get("start")
    end = request.args.get("end")

    # The type of chart to show, defaults to line
    compare_type = request.args.get("compare_type", "line")

    # Start building the database query for this user's KPIs
    query = KPIEntry.query.filter_by(user_id=current_user.id)

    # Apply the KPI name filter if one was selected
    if selected_kpi:
        query = query.filter(KPIEntry.kpi_name.ilike(f"%{selected_kpi}%"))

    # Apply the start date filter if one was set
    if start:
        query = query.filter(KPIEntry.kpi_date >= start)

    # Apply the end date filter if one was set
    if end:
        query = query.filter(KPIEntry.kpi_date <= end)

    # Run the query and sort results by date oldest first
    entries = query.order_by(KPIEntry.kpi_date.asc()).all()

    # CHART DATA
    # Build the data structure that Chart.js needs to draw the graphs
    chart_data = {}

    for e in entries:
        # If the user is comparing two KPIs, skip any that are not selected
        if kpi1 or kpi2:
            if e.kpi_name not in [kpi1, kpi2]:
                continue

        name = e.kpi_name

        # Create an entry in chart_data for this KPI if it does not exist yet
        if name not in chart_data:
            chart_data[name] = {
                "labels": [],
                "values": []
            }

        # Add the date as a label and the value to the chart data
        chart_data[name]["labels"].append(
            e.kpi_date.strftime("%Y-%m-%d") if e.kpi_date else ""
        )
        chart_data[name]["values"].append(float(e.value or 0))

    # GROUP KPIs
    # Group entries by name so we can calculate stats for each KPI
    grouped = defaultdict(list)
    for e in entries:
        grouped[e.kpi_name].append(e)

    card_stats = {}
    behind_target = []

    for name, items in grouped.items():
        # Sort by date so the most recent is last
        items = sorted(items, key=lambda x: x.kpi_date)

        vals = [float(i.value or 0) for i in items]
        latest = vals[-1]
        avg = sum(vals) / len(vals)

        # Get the previous value to calculate the trend
        prev = vals[-2] if len(vals) > 1 else None
        change = pct_change(latest, prev)

        last_entry = items[-1]

        # Work out the green amber red status for this KPI
        status = evaluate_status(
            latest,
            last_entry.target_value,
            last_entry.direction,
            last_entry.tolerance_pct
        )

        # Store the stats for this KPI to pass to the template
        card_stats[name] = {
            "latest": latest,
            "avg": avg,
            "trend_pct": change,
            "status": status
        }

        # Add to the behind target list if red or amber
        if status in ["red", "amber"]:
            behind_target.append({
                "name": name,
                "latest": latest,
                "status": status
            })

    # BEST AND WORST KPI
    # Find which KPI has the best and worst trend percentage
    worst_kpi = None
    best_kpi = None

    # Only consider KPIs that have a trend value to compare
    valid_trends = {k: v for k, v in card_stats.items() if v["trend_pct"] is not None}

    if valid_trends:
        worst_kpi = min(valid_trends.items(), key=lambda x: x[1]["trend_pct"])[0]
        best_kpi = max(valid_trends.items(), key=lambda x: x[1]["trend_pct"])[0]

    # Count how many KPIs are in the red
    bad_count = len([k for k in card_stats.values() if k["status"] == "red"])
    kpi_names = list(grouped.keys())

    # Send all the data to the dashboard template
    return render_template(
        "dashboard.html",
        card_stats=card_stats,
        behind_target=behind_target,
        worst_kpi=worst_kpi,
        best_kpi=best_kpi,
        bad_count=bad_count,
        chart_data=chart_data,
        entries=entries,
        kpi_names=kpi_names,
        selected_kpi=selected_kpi,
        kpi1=kpi1,
        kpi2=kpi2,
        start=start,
        end=end,
        compare_type=compare_type
    )


# HELP PAGE
# Just shows the static help page
@dash_bp.route("/help")
@login_required
def help_page():
    return render_template("help.html")