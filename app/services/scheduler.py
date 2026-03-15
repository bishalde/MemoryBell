from datetime import datetime, timedelta
from app import db
from app.services.twilio_service import send_whatsapp_reminder, send_call_reminder


REMINDER_OFFSETS = {
    "same_day": 0,
    "1_day_before": 1,
    "3_days_before": 3,
    "7_days_before": 7,
}


def check_and_send_reminders():
    """Called by external cron job via /api/cron/check-reminders endpoint."""
    today = datetime.utcnow().date()
    sent_count = 0

    reminders = db.reminders.find()
    for reminder in reminders:
        event_date = reminder["event_date"]
        if isinstance(event_date, str):
            event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
        elif isinstance(event_date, datetime):
            event_date = event_date.date()

        offset_key = reminder.get("reminder_before", "same_day")
        offset_days = REMINDER_OFFSETS.get(offset_key, 0)

        reminder_date = event_date - timedelta(days=offset_days)

        if reminder_date == today:
            user = db.users.find_one({"_id": reminder["user_id"]})
            if not user:
                continue

            event_name = reminder["event_name"]
            contact_name = reminder.get("contact_name", "")
            days_text = "Today" if offset_days == 0 else f"In {offset_days} day(s)"

            message = (
                f"MemoryBell Reminder\n\n"
                f"Hi {user['name']}!\n\n"
                f"{days_text} is {contact_name}'s {event_name}!\n"
                f"Don't forget to celebrate!"
            )

            call_message = (
                f"Hello! This is a reminder from MemoryBell. "
                f"{days_text} is {contact_name}'s {event_name}. "
                f"Don't forget to celebrate!"
            )

            notify_method = reminder.get("notify_method", "whatsapp")
            contact_phone = reminder.get("contact_phone", user.get("whatsapp_number", ""))

            try:
                if notify_method in ("whatsapp", "both"):
                    send_whatsapp_reminder(contact_phone, message)
                if notify_method in ("call", "both"):
                    send_call_reminder(contact_phone, call_message)
                sent_count += 1
            except Exception as e:
                print(f"Failed to send reminder {reminder['_id']}: {e}")

    return sent_count
