from flask import Blueprint, jsonify, request, current_app
from app.services.scheduler import check_and_send_reminders

cron_bp = Blueprint("cron", __name__)


@cron_bp.route("/api/cron/check-reminders", methods=["GET"])
def trigger_reminders():
    """Endpoint for cron-job.org to hit. Requires ?secret= parameter."""
    secret = request.args.get("secret", "")
    expected = current_app.config.get("CRON_SECRET", "")
    if not expected or secret != expected:
        return jsonify({"status": "error", "message": "unauthorized"}), 401

    sent = check_and_send_reminders()
    return jsonify({"status": "ok", "reminders_sent": sent})
