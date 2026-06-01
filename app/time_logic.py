"""Timezone-aware time parsing and target datetime resolution."""

from __future__ import annotations

import os
import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

DEFAULT_TZ_NAME = "UTC"
TZ_ENV_VAR = "TIMED_CLICKER_TZ"
TIME_PATTERN = re.compile(r"^(\d{2}):(\d{2}):(\d{2})$")


class TimeParseError(ValueError):
    """Raised when HH:MM:SS input is invalid."""


def get_timezone(name: str | None = None) -> ZoneInfo:
    tz_name = name or os.environ.get(TZ_ENV_VAR) or DEFAULT_TZ_NAME
    return ZoneInfo(tz_name)


def parse_time_hms(text: str) -> time:
    stripped = text.strip()
    match = TIME_PATTERN.match(stripped)
    if not match:
        raise TimeParseError(
            "Invalid time format. Use HH:MM:SS, e.g. 14:30:00"
        )

    hours, minutes, seconds = (int(match.group(i)) for i in range(1, 4))
    if not (0 <= hours <= 23 and 0 <= minutes <= 59 and 0 <= seconds <= 59):
        raise TimeParseError(
            "Invalid time. Hours: 00-23, minutes and seconds: 00-59"
        )
    return time(hours, minutes, seconds)


def now_in_tz(tz: ZoneInfo) -> datetime:
    return datetime.now(tz)


def resolve_target_datetime(trigger_time: time, tz: ZoneInfo, now: datetime | None = None) -> datetime:
    current = now if now is not None else now_in_tz(tz)
    if current.tzinfo is None:
        current = current.replace(tzinfo=tz)
    else:
        current = current.astimezone(tz)

    candidate = datetime.combine(current.date(), trigger_time, tzinfo=tz)
    if candidate <= current:
        candidate = datetime.combine(
            current.date() + timedelta(days=1), trigger_time, tzinfo=tz
        )
    return candidate


def format_timedelta(total_seconds: float) -> str:
    if total_seconds < 0:
        total_seconds = 0
    whole = int(total_seconds)
    hours, remainder = divmod(whole, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_datetime_tz(dt: datetime, tz: ZoneInfo) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
