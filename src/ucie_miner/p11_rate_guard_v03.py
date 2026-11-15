"""Bounded GitHub 403/429 public-source rate pause, no network or credentials.

This module only examines explicit HTTPError cause chains and sanitized
headers. It never stores URLs, headers, bodies, tokens, PR titles or code.
Use exclusively from P11's existing opted-in, isolated SQLite transaction.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
import sqlite3
import urllib.error

TABLE = "p11_public_rate_guard_v03"
RATE_REASONS = frozenset((
    "HTTP_429_RETRY_AFTER", "HTTP_403_RETRY_AFTER",
    "HTTP_429_PRIMARY_RESET", "HTTP_403_PRIMARY_RESET",
    "HTTP_429_EXPONENTIAL_FALLBACK",
    "HTTP_403_OWNER_REVIEW", "RATE_HEADER_OWNER_REVIEW",
))
MAX_STRIKES = 8
MAX_HINT_SECONDS = 7 * 24 * 3600
MAX_FALLBACK_SECONDS = 24 * 3600


def _http_error(error: BaseException) -> urllib.error.HTTPError | None:
    seen = set()
    current = error
    for _ in range(6):
        if id(current) in seen:
            break
        seen.add(id(current))
        if isinstance(current, urllib.error.HTTPError):
            return current if current.code in (403, 429) else None
        current = getattr(current, "__cause__", None)
        if not isinstance(current, BaseException):
            break
    return None


def _header(error: urllib.error.HTTPError, name: str) -> str | None:
    headers = error.headers
    if headers is None:
        return None
    try:
        value = headers.get(name)
        if value is None:
            value = next((v for k, v in headers.items()
                          if str(k).lower() == name.lower()), None)
    except (TypeError, ValueError, AttributeError):
        return None
    if type(value) is not str or len(value) > 64:
        return None
    return value.strip()


def _positive_int(text: str | None) -> int | None:
    if text is None or re.fullmatch(r"[0-9]{1,12}", text) is None:
        return None
    return int(text)


def _stamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("aware UTC required")
    if value.utcoffset() != timedelta(0):
        raise ValueError("UTC only")
    return value.isoformat(timespec="microseconds")


def _parse(text: str) -> datetime:
    if type(text) is not str or len(text) > 55:
        raise ValueError("invalid rate pause datetime")
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    _stamp(value)
    return value


def existing(db: sqlite3.Connection) -> sqlite3.Row | None:
    if db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE,)).fetchone() is None:
        return None
    return db.execute(
        "SELECT source_index,attempt_utc,reason,not_before_utc,strikes "
        "FROM " + TABLE + " WHERE slot=1").fetchone()


def view(db: sqlite3.Connection, *, source_index: int,
         now: datetime) -> dict:
    _stamp(now)
    if type(source_index) is not int or not 0 <= source_index < 5:
        raise ValueError("unapproved P11 source index")
    row = existing(db)
    if row is None:
        return {"active": False, "reason": None,
                "not_before_utc": None, "owner_review_required": False}
    if (row["source_index"] != source_index
            or row["reason"] not in RATE_REASONS
            or row["strikes"] < 1 or row["strikes"] > MAX_STRIKES):
        return {"active": True, "reason": "RATE_GUARD_DRIFT_OWNER_REVIEW",
                "not_before_utc": None, "owner_review_required": True}
    until = row["not_before_utc"]
    if until is None:
        return {"active": True, "reason": row["reason"],
                "not_before_utc": None, "owner_review_required": True}
    parsed = _parse(until)
    return {"active": now < parsed, "reason": row["reason"],
            "not_before_utc": until, "owner_review_required": False}


def calculate(error: BaseException, *, now: datetime,
              prior: sqlite3.Row | None) -> dict | None:
    _stamp(now)
    http = _http_error(error)
    if http is None:
        return None
    strikes = 1
    if prior is not None:
        previous = prior["strikes"]
        if type(previous) is int and 1 <= previous <= MAX_STRIKES:
            strikes = min(MAX_STRIKES, previous + 1)
    code = int(http.code)
    retry = _header(http, "retry-after")
    remain = _header(http, "x-ratelimit-remaining")
    reset = _header(http, "x-ratelimit-reset")
    not_before = None
    invalid_hint = False
    retry_due = None
    reset_due = None
    if retry is not None:
        delay = _positive_int(retry)
        if delay is None or delay > MAX_HINT_SECONDS:
            invalid_hint = True
        else:
            retry_due = now + timedelta(seconds=max(60, delay + 60))
    if remain == "0":
        unix = _positive_int(reset)
        if unix is None:
            invalid_hint = True
        else:
            try:
                target = datetime.fromtimestamp(unix, timezone.utc)
            except (OverflowError, OSError, ValueError):
                target = now + timedelta(days=8)
            delay = (target - now).total_seconds()
            if delay > MAX_HINT_SECONDS:
                invalid_hint = True
            else:
                reset_due = max(now + timedelta(minutes=1),
                                target + timedelta(minutes=1))
    if invalid_hint:
        # Do not shorten one valid server limit because another header
        # is invalid or demands an owner review.
        reason = "RATE_HEADER_OWNER_REVIEW"
    elif retry_due is not None or reset_due is not None:
        # Retry-After AND exhausted primary quota both apply when present:
        # respect the later of the two deadlines, never the earlier.
        valid = [value for value in (retry_due, reset_due)
                 if value is not None]
        not_before = max(valid)
        reason = (f"HTTP_{code}_RETRY_AFTER" if retry_due is not None
                  else f"HTTP_{code}_PRIMARY_RESET")
    elif code == 403:
        # A bare 403 might be authorization denial, not a rate limit.
        reason = "HTTP_403_OWNER_REVIEW"
    else:
        reason = "HTTP_429_EXPONENTIAL_FALLBACK"
        seconds = min(MAX_FALLBACK_SECONDS, 3600 * 2 ** (strikes - 1))
        not_before = now + timedelta(seconds=seconds)
    return {
        "reason": reason,
        "not_before_utc": _stamp(not_before) if not_before else None,
        "strikes": strikes,
    }


def persist(db: sqlite3.Connection, *, source_index: int,
            attempt_utc: str, advice: dict) -> None:
    if (type(source_index) is not int or not 0 <= source_index < 5
            or type(attempt_utc) is not str or len(attempt_utc) > 55
            or advice["reason"] not in RATE_REASONS
            or type(advice["strikes"]) is not int
            or not 1 <= advice["strikes"] <= MAX_STRIKES):
        raise ValueError("invalid closed rate advice")
    _parse(attempt_utc)
    if advice["not_before_utc"] is not None:
        _parse(advice["not_before_utc"])
    db.execute(
        "CREATE TABLE IF NOT EXISTS " + TABLE + "("
        "slot INTEGER PRIMARY KEY CHECK(slot=1),"
        "source_index INTEGER NOT NULL CHECK(source_index BETWEEN 0 AND 4),"
        "attempt_utc TEXT NOT NULL, "
        "reason TEXT NOT NULL CHECK(reason IN ("
        "'HTTP_429_RETRY_AFTER','HTTP_403_RETRY_AFTER',"
        "'HTTP_429_PRIMARY_RESET','HTTP_403_PRIMARY_RESET',"
        "'HTTP_429_EXPONENTIAL_FALLBACK','HTTP_403_OWNER_REVIEW',"
        "'RATE_HEADER_OWNER_REVIEW')),"
        "not_before_utc TEXT, "
        "strikes INTEGER NOT NULL CHECK(strikes BETWEEN 1 AND 8))"
    )
    db.execute(
        "INSERT INTO " + TABLE +
        "(slot,source_index,attempt_utc,reason,not_before_utc,strikes) "
        "VALUES(1,?,?,?,?,?) ON CONFLICT(slot) DO UPDATE SET "
        "source_index=excluded.source_index,"
        "attempt_utc=excluded.attempt_utc,"
        "reason=excluded.reason,"
        "not_before_utc=excluded.not_before_utc,"
        "strikes=excluded.strikes",
        (source_index, attempt_utc, advice["reason"],
         advice["not_before_utc"], advice["strikes"]))


def clear_on_success(db: sqlite3.Connection) -> None:
    if existing(db) is not None:
        db.execute("DELETE FROM " + TABLE + " WHERE slot=1")
