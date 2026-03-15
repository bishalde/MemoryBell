from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from bson.objectid import ObjectId
from app import db
from config import Config

reminders_bp = Blueprint("reminders", __name__)


@reminders_bp.route("/reminders/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        current_count = db.reminders.count_documents({"user_id": ObjectId(current_user.id)})
        if current_count >= Config.MAX_REMINDERS_PER_USER:
            flash(f"You can only have {Config.MAX_REMINDERS_PER_USER} reminders. Please delete one to add a new one.", "error")
            return redirect(url_for("reminders.create"))

        event_name = request.form.get("event_name", "").strip()
        event_type = request.form.get("event_type", "birthday")
        event_date = request.form.get("event_date", "")
        contact_name = request.form.get("contact_name", "").strip()
        contact_phone = request.form.get("contact_phone", "").strip()
        notify_method = request.form.get("notify_method", "whatsapp")
        reminder_before = request.form.getlist("reminder_before") or ["same_day"]

        if not event_name or not event_date:
            flash("Event name and date are required.", "error")
            return redirect(url_for("reminders.create"))

        reminder_data = {
            "user_id": ObjectId(current_user.id),
            "event_name": event_name,
            "event_type": event_type,
            "event_date": event_date,
            "contact_name": contact_name,
            "contact_phone": contact_phone,
            "contact_country_code": request.form.get("contact_country_code", "+91"),
            "notify_method": notify_method,
            "reminder_before": reminder_before,
            "created_at": datetime.utcnow(),
        }

        db.reminders.insert_one(reminder_data)
        flash("Reminder created!", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("create_reminder.html")


@reminders_bp.route("/reminders/<reminder_id>/edit", methods=["GET", "POST"])
@login_required
def edit(reminder_id):
    reminder = db.reminders.find_one({
        "_id": ObjectId(reminder_id),
        "user_id": ObjectId(current_user.id),
    })

    if not reminder:
        flash("Reminder not found.", "error")
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        db.reminders.update_one(
            {"_id": ObjectId(reminder_id)},
            {"$set": {
                "event_name": request.form.get("event_name", "").strip(),
                "event_type": request.form.get("event_type", "birthday"),
                "event_date": request.form.get("event_date", ""),
                "contact_name": request.form.get("contact_name", "").strip(),
                "contact_phone": request.form.get("contact_phone", "").strip(),
                "contact_country_code": request.form.get("contact_country_code", "+91"),
                "notify_method": request.form.get("notify_method", "sms"),
                "reminder_before": request.form.getlist("reminder_before") or ["same_day"],
            }},
        )
        flash("Reminder updated!", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("edit_reminder.html", reminder=reminder)


@reminders_bp.route("/reminders/<reminder_id>/delete", methods=["POST"])
@login_required
def delete(reminder_id):
    db.reminders.delete_one({
        "_id": ObjectId(reminder_id),
        "user_id": ObjectId(current_user.id),
    })
    flash("Reminder deleted.", "success")
    return redirect(url_for("dashboard.index"))
