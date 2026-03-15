from flask import Blueprint, render_template
from flask_login import login_required, current_user
from bson.objectid import ObjectId
from app import db

history_bp = Blueprint("history", __name__)


@history_bp.route("/history")
@login_required
def index():
    user_id = ObjectId(current_user.id)
    notifications = list(
        db.notifications.find({"user_id": user_id}).sort("sent_at", -1).limit(100)
    )
    for n in notifications:
        n["id"] = str(n["_id"])
        if n.get("sent_at"):
            n["sent_at_str"] = n["sent_at"].strftime("%b %d, %Y at %I:%M %p")
        else:
            n["sent_at_str"] = "Unknown"
    return render_template("history.html", notifications=notifications)
