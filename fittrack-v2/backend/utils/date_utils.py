"""
Date helpers for FitTrack Pro.

The server runs UTC but users are in different timezones.
Strategy: frontend sends its local date as ?tz_offset=330 (minutes ahead of UTC).
Server uses that to compute the user's "today" correctly.
Falls back to UTC if no offset provided.
"""
from datetime import datetime, timedelta, timezone
from flask import request


def get_user_today() -> "datetime.date":
    """
    Return today's date in the user's local timezone.
    Frontend passes ?tz_offset=<minutes> (e.g. 330 for IST UTC+5:30).
    """
    try:
        tz_offset = int(request.args.get('tz_offset', 0))
    except (TypeError, ValueError):
        tz_offset = 0

    user_now = datetime.utcnow() + timedelta(minutes=tz_offset)
    return user_now.date()


def get_user_week_start(today=None) -> "datetime.date":
    """Monday of the current local week."""
    if today is None:
        today = get_user_today()
    return today - timedelta(days=today.weekday())
