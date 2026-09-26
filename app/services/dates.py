"""Date helpers shared by the dashboard, the scheduler and the reminder routes."""
from datetime import date, datetime, timedelta

# Stored in paused_until for "pause until I turn it back on"
PAUSED_FOREVER = "9999-12-31"


def parse_event_date(event_date):
    """Parse event_date from various formats to a date object (None if invalid)."""
    if isinstance(event_date, datetime):
        return event_date.date()
    if isinstance(event_date, date):
        return event_date
    try:
        return datetime.strptime(str(event_date)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def occurrence_in(event_date, year):
    """The event's date in a given year. Feb 29 falls on Feb 28 in non-leap years."""
    try:
        return event_date.replace(year=year)
    except ValueError:
        return event_date.replace(year=year, day=28)


def next_occurrence(event_date, today):
    """The next time the event comes around, counting today."""
    this_year = occurrence_in(event_date, today.year)
    return this_year if this_year >= today else occurrence_in(event_date, today.year + 1)


def years_at(event_date, occurrence):
    """How many years the event marks on a given occurrence (None if not positive)."""
    years = occurrence.year - event_date.year
    return years if years > 0 else None


def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def milestone(event_type, years):
    """Short phrase like "turns 60" or "25th anniversary" (empty if unknown)."""
    if not years:
        return ""
    if event_type == "birthday":
        return f"turns {years}"
    if event_type == "anniversary":
        return f"{ordinal(years)} anniversary"
    return f"{years} {'year' if years == 1 else 'years'}"


def paused_state(reminder, today):
    """'off' when paused indefinitely, 'skip' when skipping until a date, else None."""
    until = reminder.get("paused_until")
    if not until or str(until) <= today.isoformat():
        return None
    return "off" if str(until) == PAUSED_FOREVER else "skip"


def skip_until(event_date, today):
    """paused_until value that skips the next occurrence, then resumes."""
    return (next_occurrence(event_date, today) + timedelta(days=1)).isoformat()
