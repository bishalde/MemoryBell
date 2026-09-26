import csv
import io
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user, logout_user
from bson.objectid import ObjectId
from app import db, bcrypt

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/profile", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        update_data = {
            "name": request.form.get("name", "").strip(),
            "country_code": request.form.get("country_code", "+1").strip(),
            "phone_number": request.form.get("phone_number", "").strip(),
            "whatsapp_number": request.form.get("whatsapp_number", "").strip(),
            "timezone": request.form.get("timezone", "UTC"),
        }

        db.users.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$set": update_data},
        )
        flash("Profile updated!", "success")
        return redirect(url_for("profile.index"))

    user_data = db.users.find_one({"_id": ObjectId(current_user.id)})
    user_id = ObjectId(current_user.id)
    total_reminders = db.reminders.count_documents({"user_id": user_id})
    total_notifications = db.notifications.count_documents({"user_id": user_id, "status": "sent"})
    return render_template("profile.html", user=user_data, total_reminders=total_reminders, total_notifications=total_notifications)


@profile_bp.route("/profile/change-password", methods=["POST"])
@login_required
def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")

    user_data = db.users.find_one({"_id": ObjectId(current_user.id)})

    if not bcrypt.check_password_hash(user_data["password_hash"], current_password):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("profile.index"))

    if len(new_password) < 6:
        flash("New password must be at least 6 characters.", "error")
        return redirect(url_for("profile.index"))

    new_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"password_hash": new_hash}},
    )
    flash("Password changed!", "success")
    return redirect(url_for("profile.index"))


@profile_bp.route("/profile/delete", methods=["POST"])
@login_required
def delete_account():
    user_id = ObjectId(current_user.id)
    db.reminders.delete_many({"user_id": user_id})
    db.notifications.delete_many({"user_id": user_id})
    db.users.delete_one({"_id": user_id})
    logout_user()
    flash("Account deleted.", "success")
    return redirect(url_for("auth.login"))


EXPORT_REMINDER_FIELDS = [
    "event_name", "event_type", "event_date", "year_known", "contact_name",
    "contact_country_code", "contact_phone", "notify_method", "reminder_before",
    "notes", "paused_until", "created_at",
]


def _plain(doc, drop=("_id", "user_id", "password_hash")):
    """A JSON-safe copy of a Mongo document without internal fields."""
    return {k: v for k, v in doc.items() if k not in drop}


@profile_bp.route("/profile/export")
@login_required
def export():
    user_id = ObjectId(current_user.id)
    reminders = list(db.reminders.find({"user_id": user_id}).sort("event_date", 1))
    stamp = datetime.utcnow().strftime("%Y-%m-%d")

    if request.args.get("format") == "csv":
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=EXPORT_REMINDER_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in reminders:
            row = {k: r.get(k, "") for k in EXPORT_REMINDER_FIELDS}
            rb = row["reminder_before"]
            row["reminder_before"] = " ".join(rb) if isinstance(rb, list) else rb
            writer.writerow(row)
        return Response(out.getvalue(), mimetype="text/csv", headers={
            "Content-Disposition": f"attachment; filename=memorybell-reminders-{stamp}.csv",
        })

    user = db.users.find_one({"_id": user_id}) or {}
    notifications = db.notifications.find({"user_id": user_id}, {"reminder_id": 0}).sort("sent_at", -1)
    data = {
        "exported_at": datetime.utcnow(),
        "profile": _plain(user),
        "reminders": [_plain(r) for r in reminders],
        "notifications": [_plain(n) for n in notifications],
    }
    return Response(json.dumps(data, indent=2, default=str, ensure_ascii=False), mimetype="application/json", headers={
        "Content-Disposition": f"attachment; filename=memorybell-export-{stamp}.json",
    })
