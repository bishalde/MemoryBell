"""Delivery status for sent notifications: Twilio's real result, in plain English."""
from datetime import datetime, timedelta, timezone
from app import db
from app.services.twilio_service import get_twilio_client

# Twilio message statuses that won't change again
FINAL_STATUSES = {"delivered", "undelivered", "failed", "read"}
FAILED_STATUSES = {"undelivered", "failed"}

# Common Twilio error codes -> (reason, what to do, where to fix it)
# "fix" is "number" (the number on the reminder / profile), "twilio" or None
ERROR_REASONS = {
    30002: ("Your Twilio account is suspended", "Check the account status in the Twilio console.", "twilio"),
    30003: ("Their phone was unreachable", "The phone may be off or out of coverage. Try resending later.", None),
    30004: ("The number has blocked these texts", "They may have blocked the sender or replied STOP.", None),
    30005: ("That number doesn’t exist", "Check the number is right.", "number"),
    30006: ("Not a mobile number", "Landlines can’t receive texts. Use a mobile number.", "number"),
    30007: ("Blocked by the mobile network", "Networks filter texts from unregistered senders, common for Indian numbers.", "twilio"),
    30008: ("The mobile network didn’t say why", "Try resending. If it keeps failing, check the Twilio logs.", None),
    21211: ("That number isn’t valid", "Check the number and country code.", "number"),
    21408: ("Texting this country isn’t turned on", "Enable it in Twilio under Messaging, Settings, Geo permissions.", "twilio"),
    21610: ("They replied STOP", "This number has unsubscribed from texts from your Twilio number.", None),
    21614: ("Not a mobile number", "Use a number that can receive texts.", "number"),
    20003: ("Twilio refused the request", "Check the Twilio balance and API keys.", "twilio"),
}


def describe(n):
    """State and wording for one notification document.

    Returns dict(state, label, reason, hint, fix) where state is one of
    delivered / pending / failed / sent (sent = accepted before we tracked delivery).
    """
    status = n.get("status", "")
    delivery = n.get("delivery_status")
    code = n.get("error_code")
    if code is not None:
        try:
            code = int(code)
        except (TypeError, ValueError):
            code = None

    if status.startswith("failed") or delivery in FAILED_STATUSES:
        reason, hint, fix = ERROR_REASONS.get(code, (None, None, None))
        if not reason:
            reason = "Twilio couldn’t send it" if status.startswith("failed") else "It wasn’t delivered"
            hint = "Try resending. If it keeps failing, check the Twilio logs."
        return dict(state="failed", label="Failed", reason=reason, hint=hint, fix=fix, code=code)
    if delivery in ("delivered", "read"):
        return dict(state="delivered", label="Delivered", reason=None, hint=None, fix=None, code=None)
    if n.get("sid") and delivery not in FINAL_STATUSES:
        return dict(state="pending", label="Pending", reason="Waiting for the delivery report",
                    hint=None, fix=None, code=None)
    return dict(state="sent", label="Sent", reason="Sent before delivery tracking was added",
                hint=None, fix=None, code=None)


def apply_status(sid, status, error_code=None):
    """Store Twilio's latest status for a message. Returns True if a notification matched."""
    update = {"delivery_status": status, "status_updated_at": datetime.now(timezone.utc)}
    if error_code not in (None, "", "0", 0):
        update["error_code"] = int(error_code)
    return db.notifications.update_one({"sid": sid}, {"$set": update}).matched_count > 0


def refresh_statuses(user_id, days=14, limit=50):
    """Ask Twilio for the latest status of this user's recent, unfinished messages."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    pending = list(db.notifications.find({
        "user_id": user_id,
        "sid": {"$regex": "^(SM|MM)"},
        "delivery_status": {"$nin": list(FINAL_STATUSES)},
        "sent_at": {"$gte": since},
    }).limit(limit))
    if not pending:
        return 0

    client = get_twilio_client()
    updated = 0
    for n in pending:
        try:
            m = client.messages(n["sid"]).fetch()
        except Exception as e:
            print(f"Status refresh failed for {n['sid']}: {e}")
            continue
        if m.status != n.get("delivery_status"):
            apply_status(n["sid"], m.status, m.error_code)
            updated += 1
    return updated
