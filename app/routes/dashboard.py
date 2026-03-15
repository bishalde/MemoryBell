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
    today = datetime.utcnow().strftime("%Y-%m-%d")

    all_reminders = list(db.reminders.find({"user_id": user_id}).sort("event_date", 1))

    today_reminders = []
    upcoming_reminders = []

    for r in all_reminders:
        event_date = r["event_date"]
        if isinstance(event_date, datetime):
            date_str = event_date.strftime("%Y-%m-%d")
        else:
            date_str = str(event_date)

        r["date_str"] = date_str
        r["id"] = str(r["_id"])

        if date_str == today:
            today_reminders.append(r)
        elif date_str >= today:
            upcoming_reminders.append(r)

    return render_template(
        "dashboard.html",
        total=len(all_reminders),
        today_reminders=today_reminders,
        upcoming_reminders=upcoming_reminders,
        all_reminders=all_reminders,
    )
