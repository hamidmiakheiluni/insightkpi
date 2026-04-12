from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from collections import defaultdict
from .models import KPIEntry

dash_bp = Blueprint("dash", __name__)


def evaluate_status(value: float, target: float, direction: str, warning_buffer_pct: float) -> str:
    """
    Returns: 'green' | 'amber' | 'red' | 'unknown'
    """
    if target is None:
        return "unknown"

    tol = abs((warning_buffer_pct / 100.0) * target)
    direction = (direction or "higher").lower()

    if direction == "higher":
        if value >= target:
            return "green"
        elif value >= (target - tol):
            return "amber"
        else:
            return "red"

    # lower is better
    if value <= target:
        return "green"
    elif value <= (target + tol):
        return "amber"
    else:
        return "red"


def pct_change(current: float, previous: float):
    if previous in (None, 0):
        return None
    return ((current - previous) / previous) * 100.0


@dash_bp.route("/")
@login_required
def home():
    return render_template("home.html")


@dash_bp.route("/dashboard")
@login_required
def dashboard():
    kpi_filter = (request.args.get("kpi_name") or "").strip()
    start = request.args.get("start")
    end = request.args.get("end")
    view = (request.args.get("view") or "chart").strip().lower()

    q = KPIEntry.query.filter_by(user_id=current_user.id)

    if kpi_filter:
        q = q.filter(KPIEntry.kpi_name == kpi_filter)
    if start:
        q = q.filter(KPIEntry.kpi_date >= start)
    if end:
        q = q.filter(KPIEntry.kpi_date <= end)

    entries = q.order_by(KPIEntry.kpi_date.asc()).all()

    all_kpis = (
        KPIEntry.query.filter_by(user_id=current_user.id)
        .with_entities(KPIEntry.kpi_name)
        .distinct()
        .all()
    )
    kpi_names = [row[0] for row in all_kpis]

    daily = defaultdict(list)
    for e in entries:
        daily[e.kpi_date.isoformat()].append(float(e.value))

    labels = sorted(daily.keys())
    values = [round(sum(vals) / len(vals), 2) for _, vals in sorted(daily.items())]

    series = defaultdict(list)
    series_entries = defaultdict(list)

    for e in entries:
        series[e.kpi_name].append((e.kpi_date.isoformat(), float(e.value)))
        series_entries[e.kpi_name].append(e)

    card_stats = {}
    behind_target = []

    for name, points in series.items():
        vals = [v for _, v in points]
        latest_val = vals[-1]

        last_entry = series_entries[name][-1]
        target = last_entry.target_value
        direction = last_entry.direction or "higher"
        warning_buffer = last_entry.tolerance_pct if last_entry.tolerance_pct is not None else 5.0

        status = evaluate_status(latest_val, target, direction, warning_buffer)

        n = len(vals)
        half = max(1, n // 2)
        current_slice = vals[-half:]
        prev_slice = vals[-(2 * half):-half] if n >= 2 * half else []

        current_avg = sum(current_slice) / len(current_slice)
        prev_avg = (sum(prev_slice) / len(prev_slice)) if prev_slice else None
        change_pct = pct_change(current_avg, prev_avg) if prev_avg is not None else None

        prev_val = vals[-2] if n >= 2 else None
        delta = (latest_val - prev_val) if prev_val is not None else None
        delta_pct = pct_change(latest_val, prev_val) if prev_val is not None else None

        card_stats[name] = {
            "latest": latest_val,
            "prev": prev_val,
            "delta": delta,
            "delta_pct": delta_pct,
            "avg": sum(vals) / len(vals),
            "min": min(vals),
            "max": max(vals),
            "count": len(vals),
            "target": target,
            "direction": direction,
            "tolerance_pct": warning_buffer,
            "status": status,
            "trend_pct": change_pct,
        }

        if status in ("amber", "red"):
            behind_target.append({
                "name": name,
                "status": status,
                "latest": latest_val,
                "target": target,
                "trend_pct": change_pct,
            })

    behind_target.sort(key=lambda x: 0 if x["status"] == "red" else 1)
    series_limited = dict(list(series.items())[:6])

    return render_template(
        "dashboard.html",
        entries=entries,
        labels=labels,
        values=values,
        kpi_names=kpi_names,
        selected_kpi=kpi_filter,
        start=start or "",
        end=end or "",
        view=view,
        card_stats=card_stats,
        series=series_limited,
        behind_target=behind_target,
    )


@dash_bp.route("/help")
@login_required
def help_page():
    return render_template("help.html")