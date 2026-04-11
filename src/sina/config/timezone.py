"""
Timezone utilities for SINA application.
All datetime operations use America/Mexico_City timezone.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Mexico City timezone
MEXICO_TZ = ZoneInfo("America/Mexico_City")


def get_mexico_now() -> datetime:
    """
    Returns current datetime in America/Mexico_City timezone.
    """
    return datetime.now(MEXICO_TZ)


def get_mexico_today() -> datetime:
    """
    Returns current date (midnight) in America/Mexico_City timezone.
    """
    now = get_mexico_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def to_mexico_tz(dt: datetime) -> datetime:
    """
    Convert a datetime to America/Mexico_City timezone.
    If datetime is naive, assumes UTC and converts.
    """
    if dt.tzinfo is None:
        # Assume UTC if naive
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MEXICO_TZ)


def format_mexico_date(dt: datetime | None) -> str:
    """
    Format datetime to Mexican Spanish date string.
    Returns '—' if None.
    """
    if dt is None:
        return "—"
    
    dt_mx = to_mexico_tz(dt)
    opciones = {"day": "numeric", "month": "short", "year": "numeric"}
    return dt_mx.strftime("%d %b %Y")
