from datetime import datetime
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from bson.objectid import ObjectId
from app import db
from app.services.dates import parse_event_date, next_occurrence, years_at, milestone, paused_state

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    user_id = ObjectId(current_user.id)
    today = datetime.utcnow().date()
    today_md = today.strftime("%m-%d")

    all_reminders = list(db.reminders.find({"user_id": user_id}).sort("event_date", 1))

    today_reminders = []
    upcoming_reminders = []
    past_reminders = []

    for r in all_reminders:
        event_date = r["event_date"]
        if isinstance(event_date, datetime):
            date_str = event_date.strftime("%Y-%m-%d")
        else:
            date_str = str(event_date)

        # Extract month-day for recurring match
        month_day = date_str[5:]  # "MM-DD"

        r["date_str"] = date_str
        r["id"] = str(r["_id"])
        r["paused"] = paused_state(r, today)
        parsed = parse_event_date(date_str)
        r["milestone"] = ""
        if parsed and r.get("year_known"):
            r["milestone"] = milestone(r.get("event_type"), years_at(parsed, next_occurrence(parsed, today)))

        if month_day == today_md:
            today_reminders.append(r)
        else:
            # Check if the event's next occurrence is upcoming
            try:
                event_md = datetime.strptime(month_day, "%m-%d").date().replace(year=today.year)
            except ValueError:
                event_md = datetime.strptime(month_day, "%m-%d").date().replace(year=today.year, day=28)

            if event_md > today:
                upcoming_reminders.append(r)
            else:
                past_reminders.append(r)

    # Sort upcoming by next occurrence
    upcoming_reminders.sort(key=lambda r: r["date_str"][5:])

    # Year strip: which months your dates fall in, and the next active one
    upcoming_active = [r for r in today_reminders + upcoming_reminders if not r["paused"]]
    next_id = upcoming_active[0]["id"] if upcoming_active else None
    calendar = [[] for _ in range(12)]
    for r in sorted(all_reminders, key=lambda r: r["date_str"][5:]):
        if len(r["date_str"]) >= 10 and r["date_str"][5:7].isdigit():
            calendar[int(r["date_str"][5:7]) - 1].append(r)

    return render_template(
        "dashboard.html",
        calendar=calendar,
        current_month=today.month,
        next_id=next_id,
        total=len(all_reminders),
        today_reminders=today_reminders,
        upcoming_reminders=upcoming_reminders,
        all_reminders=all_reminders,
    )
