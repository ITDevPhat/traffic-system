"""
Timezone utilities for Vietnam (UTC+7)
"""
from datetime import datetime, timezone, timedelta

# Vietnam timezone (UTC+7)
VIETNAM_TZ = timezone(timedelta(hours=7))


def now_vietnam() -> datetime:
    """Get current datetime in Vietnam timezone (UTC+7)"""
    return datetime.now(VIETNAM_TZ)


def utc_to_vietnam(dt: datetime) -> datetime:
    """Convert UTC datetime to Vietnam timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(VIETNAM_TZ)


def vietnam_now_naive() -> datetime:
    """Get current datetime in Vietnam timezone as naive datetime (no tzinfo)
    Use this for database fields that don't support timezone
    """
    return datetime.now(VIETNAM_TZ).replace(tzinfo=None)
