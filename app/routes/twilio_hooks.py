from flask import Blueprint, request, abort
from twilio.request_validator import RequestValidator
from config import Config
from app.services.delivery import apply_status

twilio_hooks_bp = Blueprint("twilio_hooks", __name__)


@twilio_hooks_bp.route("/api/twilio/status", methods=["POST"])
def message_status():
    """Twilio calls this as a message moves through queued -> sent -> delivered/undelivered."""
    # Validate against the public URL Twilio was given; request.url can differ behind a proxy
    url = f"{Config.PUBLIC_BASE_URL}/api/twilio/status" if Config.PUBLIC_BASE_URL else request.url
    validator = RequestValidator(Config.TWILIO_AUTH_TOKEN or "")
    if not validator.validate(url, request.form.to_dict(), request.headers.get("X-Twilio-Signature", "")):
        abort(403)

    sid = request.form.get("MessageSid", "")
    status = request.form.get("MessageStatus", "")
    if sid and status:
        apply_status(sid, status, request.form.get("ErrorCode"))
    return ("", 204)
