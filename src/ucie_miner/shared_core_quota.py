"""Fail-closed GitHub CORE rate budget for the explicitly enabled UCIE BASE pilot.

No transport, automatic owner approval, retry, source expansion or scheduler mutation.
The default collector does not import or instantiate this module. All state is
one UCIE-owned, transactional SQLite file separate from public_miner.sqlite3.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import os
import re
import secrets
import sqlite3
import time
from typing import Mapping, Callable

SCHEMA = "UCIE_BASE_SHARED_CORE_QUOTA_V01"
NAME = "shared_core_budget.sqlite3"
BASE_URL = (
    "https://api.github.com/repos/python/cpython/pulls?"
    "state=closed&sort=updated&direction=desc&per_page=20"
)
SAFETY_FLOOR = 8
MAX_OBSERVATION_AGE = 300
RESET_SETTLE = 60
RESET_PROBE_WINDOW = 3600
MAX_RESET_AHEAD = 7200
FIELDS = (
    "X-RateLimit-Limit", "X-RateLimit-Remaining",
    "X-RateLimit-Reset", "X-RateLimit-Resource",
)


class CoreQuotaHold(ValueError):
    """First-party bounded denial; never include untrusted response text."""


def _approved(url: str) -> bool:
    if type(url) is not str or len(url) > 250 or not url.isascii():
        return False
    if url == BASE_URL:
        return True
    return re.fullmatch(
        r"https://api\.github\.com/repos/python/cpython/pulls/"
        r"[1-9][0-9]{0,8}/files\?per_page=30", url,
    ) is not None


def _parse_headers(headers: Mapping[str, str] | None, now: int) -> tuple[int, int]:
    if headers is None or len(headers) > 20:
        raise CoreQuotaHold("CORE_RATE_HEADERS_MISSING")
    vals = []
    for key in FIELDS[:3]:
        value = headers.get(key)
        if type(value) is not str or not 1 <= len(value) <= 15:
            raise CoreQuotaHold("CORE_RATE_HEADERS_INVALID")
        if not value.isascii() or not value.isdecimal():
            raise CoreQuotaHold("CORE_RATE_HEADERS_INVALID")
        vals.append(int(value))
    limit, remaining, reset = vals
    if (headers.get(FIELDS[3]) != "core"
            or not 1 <= limit <= 5000
            or not 0 <= remaining <= limit
            or not now < reset <= now + MAX_RESET_AHEAD):
        raise CoreQuotaHold("CORE_RATE_HEADERS_UNTRUSTED")
    return remaining, reset


class SharedCoreQuota:
    """One cross-process BASE budget with one first-GET owner bootstrap.

    Creating a ledger requires an explicitly reviewed invocation. An INFLIGHT
    crash or 403/429 stays blocked. Only a previously proven 200/CORE reset
    may enable ONE later BASE reset-window observation; never an extra probe.
    """

    def __init__(self, repo_root: Path, *, clock: Callable[[], int] | None = None):
        if not isinstance(repo_root, Path) or repo_root.is_symlink():
            raise CoreQuotaHold("UCIE_ROOT_INVALID")
        self.root = repo_root
        self.path = repo_root / "runtime" / NAME
        self.clock = clock if clock is not None else lambda: int(time.time())

    def _now(self) -> int:
        value = self.clock()
        if type(value) is not int or value < 1_600_000_000:
            raise CoreQuotaHold("CORE_CLOCK_INVALID")
        return value

    def _validated_path(self) -> Path:
        runtime = self.path.parent
        if (self.root.is_symlink() or not self.root.is_dir()
                or runtime.is_symlink() or not runtime.is_dir()
                or self.path.is_symlink()
                or (self.path.exists() and not self.path.is_file())):
            raise CoreQuotaHold("UCIE_RUNTIME_PATH_UNSAFE")
        return self.path

    @contextmanager
    def _connect(self, *, allow_create: bool = False):
        path = self._validated_path()
        created = False
        if not path.exists():
            if not allow_create:
                raise CoreQuotaHold("CORE_LEDGER_MISSING_NO_GET")
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
                created = True
            except FileExistsError as exc:
                # Parallel owner boots may not both start a first GET.
                raise CoreQuotaHold("CORE_BOOTSTRAP_RACE_NO_GET") from exc
        if path.stat().st_size > 1_000_000:
            raise CoreQuotaHold("CORE_LEDGER_OVERSIZE_NO_GET")
        try:
            conn = sqlite3.connect(path.as_uri() + "?mode=rw",
                                   uri=True, timeout=1.0,
                                   isolation_level=None)
            try:
                conn.row_factory = sqlite3.Row
                if created:
                    conn.execute("""CREATE TABLE quota(
                        slot INTEGER PRIMARY KEY CHECK(slot=1),
                        schema_id TEXT NOT NULL,
                        phase TEXT NOT NULL,
                        remaining INTEGER, reset_epoch INTEGER,
                        observed_epoch INTEGER, token TEXT,
                        request_kind TEXT, reason TEXT NOT NULL
                    )""")
                    conn.execute(
                        "INSERT INTO quota VALUES(1,?,?,?,?,?,?,?,?)",
                        (SCHEMA, "NEW", None, None, None, None, None,
                         "NO_OBSERVATION"),
                    )
                columns = [
                    row[1] for row in conn.execute("PRAGMA table_info(quota)")
                ]
                if columns != [
                    "slot", "schema_id", "phase", "remaining",
                    "reset_epoch", "observed_epoch", "token",
                    "request_kind", "reason",
                ]:
                    raise CoreQuotaHold("CORE_LEDGER_SCHEMA_DRIFT")
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute("SELECT * FROM quota WHERE slot=1").fetchone()
                if row is None or row["schema_id"] != SCHEMA:
                    raise CoreQuotaHold("CORE_LEDGER_IDENTITY_DRIFT")
                yield conn, row
                conn.execute("COMMIT")
            except BaseException:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise CoreQuotaHold("CORE_LEDGER_UNAVAILABLE_NO_GET") from exc

    def inspect(self) -> dict:
        if not self._validated_path().is_file():
            return {"schema": SCHEMA, "phase": "ABSENT",
                    "remaining_estimate": None, "reason": "NO_LEDGER",
                    "live_get_authorized": False}
        with self._connect() as (_conn, row):
            return {"schema": SCHEMA, "phase": row["phase"],
                    "remaining_estimate": row["remaining"],
                    "reason": row["reason"],
                    "live_get_authorized": False}

    def reserve(self, url: str, *, reviewed_bootstrap: bool = False) -> str:
        if not _approved(url):
            raise CoreQuotaHold("CORE_UNAPPROVED_BASE_ROUTE_NO_GET")
        if type(reviewed_bootstrap) is not bool:
            raise CoreQuotaHold("CORE_BOOTSTRAP_FLAG_INVALID")
        now = self._now()
        denial = None
        token = None
        with self._connect(
                allow_create=reviewed_bootstrap and url == BASE_URL
        ) as (conn, row):
            phase, reason = row["phase"], row["reason"]
            rem, reset, seen = (
                row["remaining"], row["reset_epoch"], row["observed_epoch"]
            )
            if reviewed_bootstrap and phase != "NEW":
                raise CoreQuotaHold("CORE_BOOTSTRAP_CONSUMED_NO_GET")
            if phase == "NEW":
                if not reviewed_bootstrap or url != BASE_URL:
                    raise CoreQuotaHold("CORE_OWNER_FIRST_GET_REQUIRED")
                kind = "BOOTSTRAP"
                rem = None
            elif phase in ("READY", "HOLD") and (
                (phase == "READY" or reason in (
                    "STALE_WINDOW", "LOW_CORE_REMAINING"
                ))
                and url == BASE_URL
                and type(reset) is int and type(seen) is int
                and seen < reset
                and reset + RESET_SETTLE <= now <= reset + RESET_PROBE_WINDOW
            ):
                kind = "RESET_PROBE"
                rem = None
            elif phase == "READY":
                if (type(reset) is not int or type(seen) is not int
                        or type(rem) is not int or now < seen
                        or now - seen > MAX_OBSERVATION_AGE
                        or now >= reset):
                    denial = "STALE_WINDOW"
                elif rem <= SAFETY_FLOOR:
                    denial = "LOW_CORE_REMAINING"
                else:
                    kind = "OBSERVED"
                    rem -= 1
            else:
                raise CoreQuotaHold("CORE_INFLIGHT_OR_STICKY_HOLD_NO_GET")
            if denial is not None:
                conn.execute("UPDATE quota SET phase='HOLD',reason=? "
                             "WHERE slot=1", (denial,))
            else:
                token = secrets.token_hex(16)
                conn.execute(
                    "UPDATE quota SET phase='INFLIGHT', remaining=?, "
                    "token=?,request_kind=?,reason='NONE' WHERE slot=1",
                    (rem, token, kind),
                )
        if denial is not None:
            raise CoreQuotaHold("CORE_STALE_OR_FLOOR_HOLD_NO_GET")
        if token is None:
            raise CoreQuotaHold("CORE_RESERVATION_NOT_GRANTED")
        return token

    def complete(self, token: str, *, status_code: int | None,
                 headers: Mapping[str, str] | None = None) -> dict:
        if type(token) is not str or re.fullmatch("[0-9a-f]{32}", token) is None:
            raise CoreQuotaHold("CORE_INVALID_LEASE")
        if status_code is not None and type(status_code) is not int:
            raise CoreQuotaHold("CORE_INVALID_STATUS")
        now = self._now()
        with self._connect() as (conn, row):
            if row["phase"] != "INFLIGHT" or row["token"] != token:
                raise CoreQuotaHold("CORE_REPLAY_OR_FOREIGN_LEASE")
            remaining, reset, seen = (
                row["remaining"], row["reset_epoch"], row["observed_epoch"]
            )
            reason = None
            if status_code in (403, 429):
                reason = "UPSTREAM_403_429_STICKY_HOLD"
            elif status_code != 200:
                reason = "UNCERTAIN_RESPONSE_STICKY_HOLD"
            else:
                try:
                    observed_rem, observed_reset = _parse_headers(headers, now)
                    if row["request_kind"] in ("BOOTSTRAP", "RESET_PROBE"):
                        if (row["request_kind"] == "RESET_PROBE"
                                and (type(reset) is not int
                                     or observed_reset <= reset)):
                            raise CoreQuotaHold("CORE_RESET_NOT_ADVANCED")
                        remaining, reset = observed_rem, observed_reset
                    elif (type(reset) is not int or type(seen) is not int
                          or now < seen or now >= reset
                          or observed_reset != reset):
                        raise CoreQuotaHold("CORE_RESET_CLOCK_MISMATCH")
                    else:
                        remaining = min(remaining, observed_rem)
                    seen = now
                    if remaining <= SAFETY_FLOOR:
                        reason = "LOW_CORE_REMAINING"
                except (CoreQuotaHold, TypeError, ValueError):
                    reason = "CORE_RATE_HEADERS_INVALID_STICKY_HOLD"
            conn.execute(
                "UPDATE quota SET phase=?,remaining=?,reset_epoch=?,"
                "observed_epoch=?,token=NULL,request_kind=NULL,reason=? "
                "WHERE slot=1",
                ("HOLD" if reason else "READY",
                 remaining, reset, seen, reason or "NONE"),
            )
        return self.inspect()
