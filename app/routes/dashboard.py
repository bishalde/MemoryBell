from datetime import datetime
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from bson.objectid import ObjectId
from app import db

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

    return render_template(
        "dashboard.html",
        total=len(all_reminders),
        today_reminders=today_reminders,
        upcoming_reminders=upcoming_reminders,
        all_reminders=all_reminders,
    )
