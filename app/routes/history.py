import time
from collections import Counter
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from bson.objectid import ObjectId
from bson.errors import InvalidId
from app import db
from app.services.dates import parse_event_date, paused_state, next_send
from app.services.delivery import describe, refresh_statuses
from app.services.scheduler import REMINDER_OFFSETS, _send_single

history_bp = Blueprint("history", __name__)

PAGE_SIZE = 50
MAX_LIMIT = 500
RESENDS_PER_HOUR = 3


def _next_text(user_id, today):
    """(date, reminder) for the next reminder text we'll send, or None."""
    best = None
    for r in db.reminders.find({"user_id": user_id}):
        event_date = parse_event_date(r.get("event_date"))
        if not event_date or paused_state(r, today):
            continue
        rb = r.get("reminder_before", ["same_day"])
        send_on = next_send(event_date, rb if isinstance(rb, list) else [rb], REMINDER_OFFSETS, today)
        if send_on and (best is None or send_on < best[0]):
            best = (send_on, r)
    return best


@history_bp.route("/history")
@login_required
def index():
    user_id = ObjectId(current_user.id)
    now = datetime.now(timezone.utc)
    try:
        limit = min(max(int(request.args.get("limit", PAGE_SIZE)), PAGE_SIZE), MAX_LIMIT)
    except ValueError:
        limit = PAGE_SIZE

    total = db.notifications.count_documents({"user_id": user_id})
    notifications = list(db.notifications.find({"user_id": user_id}).sort("sent_at", -1).limit(limit))
    for n in notifications:
        n["id"] = str(n["_id"])
        n["info"] = describe(n)
        sent_at = n.get("sent_at")
        n["sent_at_str"] = sent_at.strftime("%b %d, %Y at %I:%M %p") if sent_at else "Unknown"
        n["month"] = sent_at.strftime("%B %Y") if sent_at else "Unknown date"
        n["reminder_id_str"] = str(n["reminder_id"]) if n.get("reminder_id") else ""

    # Month sections, newest first (notifications are already sorted)
    groups = []
    for n in notifications:
        if not groups or groups[-1][0] != n["month"]:
            groups.append((n["month"], []))
        groups[-1][1].append(n)

    # This year's numbers, across everything (not just the loaded page)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    this_year = list(db.notifications.find(
        {"user_id": user_id, "sent_at": {"$gte": year_start}},
        {"status": 1, "delivery_status": 1, "error_code": 1, "sid": 1, "sent_at": 1},
    ))
    states = Counter(describe(n)["state"] for n in this_year)

    # Recent failures, with the most common reason, for the banner
    recent_failed = [n for n in this_year if describe(n)["state"] == "failed" and (now - n["sent_at"].replace(tzinfo=timezone.utc)).days <= 30]
    top_reason = Counter(describe(n)["reason"] for n in recent_failed).most_common(1)

    return render_template(
        "history.html",
        notifications=notifications,
        groups=groups,
        total=total,
        limit=limit,
        next_limit=min(limit + PAGE_SIZE, MAX_LIMIT),
        stats=dict(sent=len(this_year), delivered=states["delivered"], failed=states["failed"],
                   pending=states["pending"], year=now.year),
        next_text=_next_text(user_id, now.date()),
        recent_failed=len(recent_failed),
        top_reason=top_reason[0][0] if top_reason else None,
        can_resend_ids={n["id"] for n in notifications if n["info"]["state"] == "failed" and n.get("body") and n.get("phone")},
    )


@history_bp.route("/history/refresh", methods=["POST"])
@login_required
def refresh():
    try:
        updated = refresh_statuses(ObjectId(current_user.id))
    except Exception as e:
        print(f"Status refresh failed for user {current_user.id}: {e}")
        flash("Couldn’t reach Twilio to check delivery. Try again in a minute.", "error")
        return redirect(url_for("history.index"))
    flash(f"Updated {updated} delivery {'status' if updated == 1 else 'statuses'}." if updated else "Delivery statuses are up to date.", "success")
    return redirect(url_for("history.index"))


@history_bp.route("/history/<notification_id>/resend", methods=["POST"])
@login_required
def resend(notification_id):
    try:
        n = db.notifications.find_one({"_id": ObjectId(notification_id), "user_id": ObjectId(current_user.id)})
    except (InvalidId, TypeError):
        n = None
    if not n or describe(n)["state"] != "failed" or not n.get("body") or not n.get("phone") or n.get("channel") == "call":
        flash("This text can’t be resent.", "error")
        return redirect(url_for("history.index"))

    now = time.time()
    recent = [t for t in session.get("resends", []) if now - t < 3600]
    if len(recent) >= RESENDS_PER_HOUR:
        flash(f"You can resend {RESENDS_PER_HOUR} texts an hour. Try again later.", "error")
        return redirect(url_for("history.index"))
    session["resends"] = recent + [now]

    _, ok = _send_single(n["channel"], n["phone"], n["body"], n["user_id"], n.get("reminder_id"),
                         n.get("event_name", ""), n.get("contact_name", ""))
    flash("Resent. It’s at the top of the list." if ok else "Resending failed too. See the reason on the new entry.",
          "success" if ok else "error")
    return redirect(url_for("history.index"))
