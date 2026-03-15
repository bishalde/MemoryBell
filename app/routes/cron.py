from flask import Blueprint, jsonify, request
from config import Config
from app.services.scheduler import check_and_send_reminders

cron_bp = Blueprint("cron", __name__)


@cron_bp.route("/api/cron/check-reminders", methods=["GET"])
def trigger_reminders():
    """Endpoint for cron-job.org to hit. Add a secret token for security."""
    token = request.args.get("token", "")
    if token != Config.SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    sent = check_and_send_reminders()
    return jsonify({"status": "ok", "reminders_sent": sent})
