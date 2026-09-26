import time
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from bson.objectid import ObjectId
from bson.errors import InvalidId
from app import db
from app.services.dates import (
    PAUSED_FOREVER, parse_event_date, next_occurrence, years_at, skip_until,
)
from app.services.scheduler import REMINDER_OFFSETS, _build_sms_message, _build_recipient_message, _full_number
from app.services.twilio_service import send_sms_reminder
from config import Config

reminders_bp = Blueprint("reminders", __name__)

NOTES_MAX = 200
RECIPIENT_MESSAGE_MAX = 300
TEST_SMS_PER_HOUR = 3


def _form_fields():
    """Reminder fields shared by create and edit."""
    return {
        "event_name": request.form.get("event_name", "").strip(),
        "event_type": request.form.get("event_type", "birthday"),
        "event_date": request.form.get("event_date", ""),
        "year_known": request.form.get("year_known") == "1",
        "contact_name": request.form.get("contact_name", "").strip(),
        "contact_phone": request.form.get("contact_phone", "").strip(),
        "contact_country_code": request.form.get("contact_country_code", "+91"),
        "notify_method": request.form.get("notify_method", "sms"),
        "reminder_before": request.form.getlist("reminder_before") or ["same_day"],
        "notes": request.form.get("notes", "").strip()[:NOTES_MAX],
        "recipient_message": request.form.get("recipient_message", "").strip()[:RECIPIENT_MESSAGE_MAX],
    }


def _own_reminder(reminder_id):
    """The current user's reminder, or None (also for malformed ids)."""
    try:
        oid = ObjectId(reminder_id)
    except (InvalidId, TypeError):
        return None
    return db.reminders.find_one({"_id": oid, "user_id": ObjectId(current_user.id)})


@reminders_bp.route("/reminders/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        current_count = db.reminders.count_documents({"user_id": ObjectId(current_user.id)})
        if current_count >= Config.MAX_REMINDERS_PER_USER:
            flash(f"You can only have {Config.MAX_REMINDERS_PER_USER} reminders. Please delete one to add a new one.", "error")
            return redirect(url_for("reminders.create"))

        fields = _form_fields()
        if not fields["event_name"] or not fields["event_date"]:
            flash("Event name and date are required.", "error")
            return redirect(url_for("reminders.create"))

        db.reminders.insert_one({
            "user_id": ObjectId(current_user.id),
            **fields,
            "created_at": datetime.utcnow(),
        })
        flash("Reminder created!", "success")
        return redirect(url_for("dashboard.index"))

    # "Duplicate" opens this page prefilled from an existing reminder; nothing is saved yet
    prefill = None
    source = _own_reminder(request.args.get("from")) if request.args.get("from") else None
    if source:
        prefill = {k: v for k, v in source.items() if k not in ("_id", "user_id", "created_at", "paused_until")}
        prefill["event_name"] = f"{source.get('event_name', '')} (copy)"

    return render_template("create_reminder.html", prefill=prefill)


@reminders_bp.route("/reminders/<reminder_id>/edit", methods=["GET", "POST"])
@login_required
def edit(reminder_id):
    reminder = _own_reminder(reminder_id)
    if not reminder:
        flash("Reminder not found.", "error")
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        db.reminders.update_one({"_id": reminder["_id"]}, {"$set": _form_fields()})
        flash("Reminder updated!", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("edit_reminder.html", reminder=reminder)


@reminders_bp.route("/reminders/<reminder_id>/delete", methods=["GET", "POST"])
@login_required
def delete(reminder_id):
    if request.method == "GET":
        return redirect(url_for("dashboard.index"))

    db.reminders.delete_one({
        "_id": ObjectId(reminder_id),
        "user_id": ObjectId(current_user.id),
    })
    flash("Reminder deleted.", "success")
    return redirect(url_for("dashboard.index"))


@reminders_bp.route("/reminders/<reminder_id>/pause", methods=["POST"])
@login_required
def pause(reminder_id):
    reminder = _own_reminder(reminder_id)
    event_date = parse_event_date(reminder["event_date"]) if reminder else None
    if not event_date:
        flash("Reminder not found.", "error")
        return redirect(url_for("dashboard.index"))

    if request.form.get("mode") == "skip":
        until = skip_until(event_date, datetime.utcnow().date())
        message = f"Skipping “{reminder['event_name']}” this year. It comes back after {until}."
    else:
        until = PAUSED_FOREVER
        message = f"Paused “{reminder['event_name']}”. Resume it any time."

    db.reminders.update_one({"_id": reminder["_id"]}, {"$set": {"paused_until": until}})
    flash(message, "success")
    return redirect(url_for("dashboard.index"))


@reminders_bp.route("/reminders/<reminder_id>/resume", methods=["POST"])
@login_required
def resume(reminder_id):
    reminder = _own_reminder(reminder_id)
    if not reminder:
        flash("Reminder not found.", "error")
        return redirect(url_for("dashboard.index"))

    db.reminders.update_one({"_id": reminder["_id"]}, {"$unset": {"paused_until": ""}})
    flash(f"Resumed “{reminder['event_name']}”.", "success")
    return redirect(url_for("dashboard.index"))


@reminders_bp.route("/reminders/test-sms", methods=["POST"])
@login_required
def test_sms():
    """Text a preview to the user's own number: their first reminder, or (target=them)
    the message the other person will get. Never texts the other person."""
    user = db.users.find_one({"_id": ObjectId(current_user.id)}) or {}
    phone = _full_number(user.get("country_code", "+1"), user.get("phone_number", ""))
    if not phone:
        return jsonify(ok=False, error="Add your phone number in Profile first."), 400

    now = time.time()
    recent = [t for t in session.get("test_sms", []) if now - t < 3600]
    if len(recent) >= TEST_SMS_PER_HOUR:
        return jsonify(ok=False, error=f"You can send {TEST_SMS_PER_HOUR} test texts an hour. Try again later."), 429

    fields = _form_fields()
    event_date = parse_event_date(fields["event_date"])
    if not fields["event_name"] or not event_date:
        return jsonify(ok=False, error="Add the occasion and date first."), 400

    contact_number = _full_number(fields["contact_country_code"], fields["contact_phone"])
    if request.form.get("target") == "them":
        if not fields["recipient_message"]:
            return jsonify(ok=False, error="Write the message to send them first."), 400
        who = fields["contact_name"] or "them"
        message = f"[Test: what {who} will get]\n" + _build_recipient_message(
            user.get("name", current_user.name), fields["recipient_message"])
    else:
        # Preview the earliest text this reminder will send (the largest offset picked)
        offset_days = max(REMINDER_OFFSETS.get(k, 0) for k in fields["reminder_before"])
        occurrence = next_occurrence(event_date, datetime.utcnow().date())
        wish_to = (fields["contact_name"] or "them") if fields["recipient_message"] and contact_number else ""
        message = "[Test] " + _build_sms_message(
            user.get("name", current_user.name), fields["contact_name"], fields["event_name"],
            fields["event_type"], occurrence.strftime("%B %d, %Y"), offset_days,
            years=years_at(event_date, occurrence) if fields["year_known"] else None,
            notes=fields["notes"], contact_number=contact_number, wish_to=wish_to,
        )

    try:
        send_sms_reminder(phone, message)
    except Exception as e:
        print(f"Test SMS failed for user {current_user.id}: {e}")
        return jsonify(ok=False, error="We couldn’t send the text. Check your phone number in Profile."), 502

    session["test_sms"] = recent + [now]
    return jsonify(ok=True, message=f"Test text sent to your number ending {phone[-4:]}.")
