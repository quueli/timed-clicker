"""Tests for time_logic module."""

from datetime import datetime, time

import pytest

from app.time_logic import (
    TimeParseError,
    format_timedelta,
    get_timezone,
    parse_time_hms,
    resolve_target_datetime,
)

UTC = get_timezone("UTC")
MOSCOW = get_timezone("Europe/Moscow")


def test_parse_valid_time():
    assert parse_time_hms("14:30:00") == time(14, 30, 0)
    assert parse_time_hms("00:00:00") == time(0, 0, 0)
    assert parse_time_hms("23:59:59") == time(23, 59, 59)


def test_parse_invalid_format():
    with pytest.raises(TimeParseError):
        parse_time_hms("9:30:00")
    with pytest.raises(TimeParseError):
        parse_time_hms("25:00:00")
    with pytest.raises(TimeParseError):
        parse_time_hms("12:60:00")
    with pytest.raises(TimeParseError):
        parse_time_hms("ab:cd:ef")


def test_resolve_target_today():
    now = datetime(2026, 6, 23, 10, 0, 0, tzinfo=UTC)
    target = resolve_target_datetime(time(14, 30, 0), UTC, now=now)
    assert target.date() == now.date()
    assert target.hour == 14 and target.minute == 30


def test_resolve_target_next_day_when_past():
    now = datetime(2026, 6, 23, 18, 0, 0, tzinfo=UTC)
    target = resolve_target_datetime(time(14, 30, 0), UTC, now=now)
    assert target.date().day == 24
    assert target.hour == 14 and target.minute == 30


def test_resolve_target_midnight_tomorrow():
    now = datetime(2026, 6, 23, 23, 59, 59, tzinfo=UTC)
    target = resolve_target_datetime(time(0, 0, 0), UTC, now=now)
    assert target.date().day == 24
    assert target.hour == 0


def test_resolve_target_with_named_timezone():
    now = datetime(2026, 6, 23, 10, 0, 0, tzinfo=MOSCOW)
    target = resolve_target_datetime(time(14, 30, 0), MOSCOW, now=now)
    assert target.tzinfo.key == "Europe/Moscow"
    assert target.hour == 14 and target.minute == 30


def test_format_timedelta():
    assert format_timedelta(3661) == "01:01:01"
    assert format_timedelta(-5) == "00:00:00"


def test_get_timezone_defaults_to_utc(monkeypatch):
    monkeypatch.delenv("TIMED_CLICKER_TZ", raising=False)
    assert get_timezone().key == "UTC"


def test_get_timezone_reads_env(monkeypatch):
    monkeypatch.setenv("TIMED_CLICKER_TZ", "Europe/Moscow")
    assert get_timezone().key == "Europe/Moscow"
