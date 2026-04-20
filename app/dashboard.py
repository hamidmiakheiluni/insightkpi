from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from collections import defaultdict
from .models import KPIEntry

# Create a blueprint for dashboard routes
dash_bp = Blueprint("dash", __name__)


# ================= STATUS LOGIC =================
# This function decides whether a KPI is green, amber or red
def evaluate_status(value, target, direction, tolerance_pct):
    if target is None:
        return None

    tol = (tolerance_pct or 0) / 100 * target

    if direction == "higher":
        if value >= target:
            return "green"
        elif value >= (target - tol):
            return "amber"
        else:
            return "red"
    else:
        if value <= target:
            return "green"
        elif value <= (target + tol):
            return "amber"
        else:
            return "red"


# ================= TREND =================
def pct_change(current, previous):
    if previous is None or previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 2)


# ================= INSIGHT =================
def get_insight(change):
    if change is None:
        return "No trend yet"
    if change > 5:
        return "Strong upward trend"
    elif change > 0:
        return "Improving steadily"
    elif change < -5:
        return "Declining significantly"
    else:
        return "Stable performance"


# ================= HOME =================
@dash_bp.route("/")
@login_required
def home():
    entries = KPIEntry.query.filter_by(user_id=current_user.id).all()
    total_kpis = len(set(e.kpi_name for e in entries))

    green_count = 0
    red_count = 0

    grouped = defaultdict(list)
    for e in entries:
        grouped[e.kpi_name].append(e)

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


# ================= DASHBOARD =================
@dash_bp.route("/dashboard")
@login_required
def dashboard():

    # View (chart / cards / multiples)
    view = request.args.get("view", "chart")

    # Chart type (line / bar)
    chart_type = request.args.get("chart_type", "line")

    selected_kpi = request.args.get("kpi_name")
    kpi1 = request.args.get("kpi1")
    kpi2 = request.args.get("kpi2")
    start = request.args.get("start")
    end = request.args.get("end")
    compare_type = request.args.get("compare_type", "bar")

    query = KPIEntry.query.filter_by(user_id=current_user.id)

    if selected_kpi:
        query = query.filter(KPIEntry.kpi_name.ilike(f"%{selected_kpi}%"))

    if start:
        query = query.filter(KPIEntry.kpi_date >= start)

    if end:
        query = query.filter(KPIEntry.kpi_date <= end)

    entries = query.order_by(KPIEntry.kpi_date.asc()).all()

    # ================= CHART DATA =================
    chart_data = {}
    labels = []
    values = []

    for e in entries:
        if kpi1 or kpi2:
            if e.kpi_name not in [kpi1, kpi2]:
                continue

        name = e.kpi_name

        if name not in chart_data:
            chart_data[name] = {"labels": [], "values": []}

        date_str = e.kpi_date.strftime("%Y-%m-%d") if e.kpi_date else ""

        chart_data[name]["labels"].append(date_str)
        chart_data[name]["values"].append(float(e.value or 0))

    # 🔥 IMPROVED: safer average calculation (no crashes)
    date_group = defaultdict(list)
    for e in entries:
        if e.kpi_date:
            key = e.kpi_date.strftime("%Y-%m-%d")
            date_group[key].append(float(e.value or 0))

    for d in sorted(date_group.keys()):
        vals = date_group[d]
        if vals:
            labels.append(d)
            avg = sum(vals) / len(vals)
            values.append(round(avg, 2))

    # ================= GROUP KPIs =================
    grouped = defaultdict(list)
    for e in entries:
        grouped[e.kpi_name].append(e)

    card_stats = {}

    for name, items in grouped.items():
        items = sorted(items, key=lambda x: x.kpi_date)
        vals = [float(i.value or 0) for i in items if i.value is not None]

        if not vals:
            continue

        latest = vals[-1]
        avg = sum(vals) / len(vals)
        prev = vals[-2] if len(vals) > 1 else None
        change = pct_change(latest, prev)

        last_entry = items[-1]

        status = evaluate_status(
            latest,
            last_entry.target_value,
            last_entry.direction,
            last_entry.tolerance_pct
        )

        insight = get_insight(change)

        card_stats[name] = {
            "latest": latest,
            "avg": round(avg, 2),
            "min": min(vals),
            "max": max(vals),
            "change": change,
            "status": status,
            "insight": insight
        }

    # ================= MULTIPLE SERIES =================
    # 🔥 IMPROVED: ensures clean data for frontend charts
    series = {}
    for name, items in grouped.items():
        cleaned = []

        for i in sorted(items, key=lambda x: x.kpi_date):
            if i.kpi_date:
                cleaned.append(
                    (i.kpi_date.strftime("%Y-%m-%d"), float(i.value or 0))
                )

        if cleaned:
            series[name] = cleaned

    # ================= COMPARISON =================
    comparison_summary = None

    if kpi1 and kpi2:
        if kpi1 in card_stats and kpi2 in card_stats:

            val1 = card_stats[kpi1]["latest"]
            val2 = card_stats[kpi2]["latest"]

            diff = round(val1 - val2, 2)
            pct = round((diff / val2) * 100, 2) if val2 != 0 else None

            if diff > 0:
                comparison_summary = f"{kpi1} is higher than {kpi2} by {abs(diff)} ({pct}% difference)"
            elif diff < 0:
                comparison_summary = f"{kpi2} is higher than {kpi1} by {abs(diff)} ({abs(pct)}% difference)"
            else:
                comparison_summary = f"{kpi1} and {kpi2} are equal"

    kpi_names = list(grouped.keys())

    return render_template(
        "dashboard.html",
        card_stats=card_stats,
        chart_data=chart_data,
        entries=entries,
        kpi_names=kpi_names,
        selected_kpi=selected_kpi,
        kpi1=kpi1,
        kpi2=kpi2,
        start=start,
        end=end,
        compare_type=compare_type,
        comparison_summary=comparison_summary,

        # frontend data
        labels=labels,
        values=values,
        series=series,
        view=view,
        chart_type=chart_type
    )


# ================= HELP PAGE =================
@dash_bp.route("/help")
@login_required
def help_page():
    return render_template("help.html")