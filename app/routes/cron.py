from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request, current_app
from app import db, csrf
from app.services.scheduler import check_and_send_reminders

cron_bp = Blueprint("cron", __name__)


def _verify_cron_secret():
    """Check secret from header first, then query param as fallback."""
    expected = current_app.config.get("CRON_SECRET", "")
    if not expected:
        return False
    secret = request.headers.get("X-Cron-Secret", "") or request.args.get("secret", "")
    return secret == expected


def _was_triggered_recently(minutes=30):
    """Check if cron was already triggered successfully in the last N minutes."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return db.cron_logs.find_one({
        "triggered_at": {"$gte": cutoff},
        "status": "ok",
    }) is not None


@cron_bp.route("/api/cron/check-reminders", methods=["GET", "POST"])
@csrf.exempt
def trigger_reminders():
    """Endpoint for cron-job.org to hit. Accepts secret via X-Cron-Secret header or ?secret= param."""
    if not _verify_cron_secret():
        return jsonify({"status": "error", "message": "unauthorized"}), 401

    if _was_triggered_recently():
        return jsonify({"status": "skipped", "message": "already triggered recently"}), 200

    sent = check_and_send_reminders()

    db.cron_logs.insert_one({
        "triggered_at": datetime.now(timezone.utc),
        "reminders_sent": sent,
        "status": "ok",
        "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
    })

    return jsonify({"status": "ok", "reminders_sent": sent})
