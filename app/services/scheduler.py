from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from xml.sax.saxutils import escape
from app import db
from app.services.twilio_service import send_whatsapp_reminder, send_call_reminder, send_sms_reminder


MAX_WORKERS = 20  # parallel Twilio API calls


def _log_notification(user_id, reminder_id, event_name, contact_name, channel, status, phone):
    db.notifications.insert_one({
        "user_id": user_id,
        "reminder_id": reminder_id,
        "event_name": event_name,
        "contact_name": contact_name,
        "channel": channel,
        "status": status,
        "phone": phone,
        "sent_at": datetime.now(timezone.utc),
    })


def _already_sent_today(reminder_id, channel):
    """Check if this reminder+channel combo was already sent today (dedup)."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return db.notifications.find_one({
        "reminder_id": reminder_id,
        "channel": channel,
        "status": "sent",
        "sent_at": {"$gte": today_start},
    }) is not None


REMINDER_OFFSETS = {
    "same_day": 0,
    "1_day_before": 1,
    "3_days_before": 3,
    "7_days_before": 7,
}

EVENT_TYPE_LABELS = {
    "birthday": "birthday",
    "anniversary": "anniversary",
    "custom": "event",
}


def _build_call_message(user_name, contact_name, event_name, event_type, event_date_str, offset_days):
    event_label = EVENT_TYPE_LABELS.get(event_type, "event")

    if offset_days == 0:
        time_phrase = "today"
        urgency = "This is a same-day reminder, so make sure to reach out!"
    elif offset_days == 1:
        time_phrase = "tomorrow"
        urgency = "You still have time to prepare something special."
    elif offset_days == 3:
        time_phrase = "in 3 days"
        urgency = "You have a few days to plan something thoughtful."
    elif offset_days == 7:
        time_phrase = "in one week"
        urgency = "You have plenty of time to get a gift or make plans."
    else:
        time_phrase = f"in {offset_days} days"
        urgency = ""

    if event_type == "birthday":
        suggestion = (
            "Maybe send them a heartfelt message, give them a call, "
            "or surprise them with a gift."
        )
    elif event_type == "anniversary":
        suggestion = (
            "Consider planning something romantic, writing a heartfelt note, "
            "or doing something memorable together."
        )
    else:
        suggestion = "Make sure to mark it on your calendar and prepare accordingly."

    name = escape(user_name.split(' ')[0])
    contact = escape(contact_name) if contact_name else "someone special"
    event = escape(event_name)

    return (
        f"Hi {name}! "
        f"This is a friendly reminder from Memory Bell. "
        f"{contact}'s {event_label} is {time_phrase}, on {event_date_str}. "
        f"The event is called: {event}. "
        f"{urgency} "
        f"{suggestion} "
        f"Don't let this special moment pass by!"
    )


def _build_whatsapp_message(user_name, contact_name, event_name, event_type, event_date_str, offset_days):
    event_label = EVENT_TYPE_LABELS.get(event_type, "event")

    if offset_days == 0:
        time_phrase = "TODAY"
    elif offset_days == 1:
        time_phrase = "TOMORROW"
    else:
        time_phrase = f"in {offset_days} days"

    contact = contact_name if contact_name else "Someone special"
    name = user_name.split(' ')[0]

    if event_type == "birthday":
        tip = "Send a wish, make a call, or surprise them with a gift!"
    elif event_type == "anniversary":
        tip = "Plan something special, write a note, or celebrate together!"
    else:
        tip = "Make sure you're prepared and don't miss it!"

    return (
        f"MemoryBell Reminder\n"
        f"{'=' * 28}\n\n"
        f"Hi {name}!\n\n"
        f"{contact}'s {event_label} is {time_phrase}!\n"
        f"Event: {event_name}\n"
        f"Date: {event_date_str}\n\n"
        f"Tip: {tip}\n\n"
        f"Don't let this special moment pass by.\n"
        f"- MemoryBell"
    )


def _build_sms_message(user_name, contact_name, event_name, event_type, event_date_str, offset_days):
    event_label = EVENT_TYPE_LABELS.get(event_type, "event")
    name = user_name.split(' ')[0]
    contact = contact_name if contact_name else "Someone special"

    if offset_days == 0:
        time_phrase = "today"
    elif offset_days == 1:
        time_phrase = "tomorrow"
    else:
        time_phrase = f"in {offset_days} days"

    return (
        f"MemoryBell: Hi {name}! "
        f"{contact}'s {event_label} ({event_name}) is {time_phrase} - {event_date_str}. "
        f"Don't forget to celebrate!"
    )


def _send_single(channel, contact_phone, message, uid, rid, event_name, contact_name):
    """Send a single notification. Returns (channel, success)."""
    try:
        if channel == "whatsapp":
            send_whatsapp_reminder(contact_phone, message)
        elif channel == "sms":
            send_sms_reminder(contact_phone, message)
        elif channel == "call":
            send_call_reminder(contact_phone, message)

        _log_notification(uid, rid, event_name, contact_name, channel, "sent", contact_phone)
        return (channel, True)
    except Exception as e:
        _log_notification(uid, rid, event_name, contact_name, channel, f"failed: {e}", contact_phone)
        print(f"Failed {channel} for reminder {rid}: {e}")
        return (channel, False)


def _parse_event_date(event_date):
    """Parse event_date from various formats to a date object."""
    if isinstance(event_date, str):
        return datetime.strptime(event_date, "%Y-%m-%d").date()
    elif isinstance(event_date, datetime):
        return event_date.date()
    return event_date


def _match_reminder_offset(event_date, today, reminder_before_list):
    """Check if a reminder should fire today for any of its selected offsets.

    For recurring events, matches on month-day (ignoring year).
    Returns (offset_key, offset_days) if matched, else None.
    """
    # This year's occurrence of the event
    try:
        this_year_event = event_date.replace(year=today.year)
    except ValueError:
        # Feb 29 in a non-leap year -> use Feb 28
        this_year_event = event_date.replace(year=today.year, day=28)

    for offset_key in reminder_before_list:
        offset_days = REMINDER_OFFSETS.get(offset_key, 0)
        trigger_date = this_year_event - timedelta(days=offset_days)
        if trigger_date == today:
            return offset_key, offset_days

    return None


def check_and_send_reminders():
    """Called by external cron job. Handles 1000s of reminders efficiently."""
    today = datetime.now(timezone.utc).date()
    sent_count = 0

    # Build list of month-day patterns that could trigger today
    # For each offset, compute which month-day we're looking for
    target_monthdays = set()
    for offset_key, offset_days in REMINDER_OFFSETS.items():
        target_date = today + timedelta(days=offset_days)
        target_monthdays.add(target_date.strftime("-%m-%d"))  # e.g. "-03-15"

    # Fetch ALL reminders and filter by month-day match
    # Use regex to match the month-day suffix in event_date strings
    regex_pattern = "|".join(md.replace("-", "\\-") + "$" for md in target_monthdays)
    reminders = list(db.reminders.find({
        "event_date": {"$regex": regex_pattern}
    }))

    if not reminders:
        return 0

    # Batch-fetch all relevant users in one query
    user_ids = list(set(r["user_id"] for r in reminders))
    users = {u["_id"]: u for u in db.users.find({"_id": {"$in": user_ids}})}

    # Build list of notification tasks
    tasks = []
    for reminder in reminders:
        user = users.get(reminder["user_id"])
        if not user:
            continue

        event_date = _parse_event_date(reminder["event_date"])

        # reminder_before can be a list or a string (legacy)
        reminder_before = reminder.get("reminder_before", ["same_day"])
        if isinstance(reminder_before, str):
            reminder_before = [reminder_before]

        # Check if any offset matches today
        match = _match_reminder_offset(event_date, today, reminder_before)
        if not match:
            continue

        offset_key, offset_days = match

        rid = reminder["_id"]
        uid = reminder["user_id"]
        event_name = reminder["event_name"]
        event_type = reminder.get("event_type", "custom")
        contact_name = reminder.get("contact_name", "")
        # Show this year's date for the event display
        try:
            this_year_event = event_date.replace(year=today.year)
        except ValueError:
            this_year_event = event_date.replace(year=today.year, day=28)
        event_date_display = this_year_event.strftime("%B %d, %Y")

        notify_method = reminder.get("notify_method", "sms")
        country_code = reminder.get("contact_country_code") or user.get("country_code", "+1")
        raw_phone = reminder.get("contact_phone", user.get("phone_number", ""))
        if raw_phone and not raw_phone.startswith("+"):
            contact_phone = country_code + raw_phone
        else:
            contact_phone = raw_phone

        if not contact_phone:
            continue

        # Determine which channels to send
        channels = []
        if notify_method in ("whatsapp", "all"):
            channels.append("whatsapp")
        if notify_method in ("sms", "both", "all"):
            channels.append("sms")
        if notify_method in ("call", "both", "all"):
            channels.append("call")

        for channel in channels:
            # Skip if already sent today (deduplication)
            if _already_sent_today(rid, channel):
                continue

            # Build the appropriate message
            if channel == "whatsapp":
                msg = _build_whatsapp_message(
                    user["name"], contact_name, event_name,
                    event_type, event_date_display, offset_days,
                )
            elif channel == "sms":
                msg = _build_sms_message(
                    user["name"], contact_name, event_name,
                    event_type, event_date_display, offset_days,
                )
            elif channel == "call":
                msg = _build_call_message(
                    user["name"], contact_name, event_name,
                    event_type, event_date_display, offset_days,
                )
            else:
                continue

            tasks.append((channel, contact_phone, msg, uid, rid, event_name, contact_name))

    if not tasks:
        return 0

    # Send all notifications in parallel using thread pool
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(tasks))) as executor:
        futures = [executor.submit(_send_single, *t) for t in tasks]
        for future in as_completed(futures):
            channel, success = future.result()
            if success:
                sent_count += 1

    return sent_count
