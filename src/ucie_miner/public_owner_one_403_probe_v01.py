"""UCIE owner exact one HTTP403 public metadata diagnostic, no auto resume.

One explicit anonymous GET to already-approved python/cpython PR-list route.
No candidate/queue/legacy miner DB mutation, credentials, downloads or
scheduler changes; the existing 403 last_run.json remains unmodified.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import re
import tempfile

from . import worker
from . import p10_owner_single_live_rearm_v02 as owner
from . import p11_rate_guard_v03 as rate
from .public_discovery import (
    public_feed_get, public_feed_url, classify_stage10_discovery_error
)

SCHEMA = "UCIE_PUBLIC_MINER_ONE_HTTP403_OWNER_PROBE_V01"
CONSENT = "UCIE_OWNER_ACCEPTS_ONE_GET_AFTER_HTTP403_WITH_UNKNOWN_SHARED_BUDGET"
SOURCE = "python/cpython"
OPERATION = "FETCH_PR_LIST"
PROBE_NAME = "public_miner_http403_owner_probe_v01.json"
SYNTH_MARKER = "UCIE_PUBLIC_MINER_403_PROBE_SYNTH_ONLY_V01"
MINIMUM_403_COOLDOWN = timedelta(minutes=60)


class One403Error(ValueError):
    pass


def _scope(root: Path) -> Path:
    if not isinstance(root, Path) or root.is_symlink():
        raise One403Error("exact UCIE root required")
    resolved = root.resolve()
    if resolved == owner.ROOT.resolve():
        owner._validate_root(resolved)
        owner._attest_windows_owner(resolved)
    else:
        marker = (resolved / "runtime" /
                  "UCIE_PUBLIC_403_PROBE_SYNTH_ONLY.marker")
        if (resolved.name.casefold() != "ucie"
                or not resolved.is_relative_to(
                    Path(tempfile.gettempdir()).resolve())
                or marker.is_symlink() or not marker.is_file()
                or marker.read_text(encoding="ascii") != SYNTH_MARKER):
            raise One403Error("nonowner root without synthetic marker")
    if (resolved / "runtime").is_symlink():
        raise One403Error("unsafe runtime link")
    return resolved


def _receipt(root: Path, *, now: datetime) -> tuple[str, str]:
    path = root / "runtime" / "last_run.json"
    if (path.is_symlink() or not path.is_file()
            or not 50 <= path.stat().st_size <= 4096):
        raise One403Error("bounded first-party failure receipt required")
    raw = path.read_bytes()
    try:
        receipt = json.loads(raw.decode("utf-8"))
        stamp = rate._parse(receipt["finished_utc"])
    except (KeyError, ValueError, UnicodeError, TypeError) as exc:
        raise One403Error("invalid original failure receipt") from exc
    if (not isinstance(receipt, dict)
            or receipt.get("schema") != "UCIE_MINER_CYCLE_V1"
            or receipt.get("status") != "COLLECTION_FAILED"
            or type(receipt.get("error_http_status")) is not int
            or receipt.get("error_http_status") != 403
            or receipt.get("error_public_source") != SOURCE
            or receipt.get("error_public_operation") != OPERATION
            or type(receipt.get("consecutive_failures")) is not int
            or not 1 <= receipt["consecutive_failures"] <= 6
            or receipt.get("production_approved") is not False):
        raise One403Error("exact first-party 403 scope drift")
    if (now < stamp + MINIMUM_403_COOLDOWN
            or now - stamp > timedelta(days=2)):
        raise One403Error("one-hour 403 cooldown or 48h stale review required")
    return sha256(raw).hexdigest(), stamp.isoformat()


def _probe_path(root: Path) -> Path:
    path = root / "runtime" / PROBE_NAME
    if path.is_symlink() or path.exists():
        raise One403Error("exact one prior probe exists: do not replay")
    return path


def preview(root: Path, *, now: datetime | None = None) -> dict:
    now = datetime.now(timezone.utc) if now is None else now
    rate._stamp(now)
    root = _scope(root)
    fingerprint, failure_utc = _receipt(root, now=now)
    _probe_path(root)
    return {
        "schema": SCHEMA,
        "status": "EXACT_ONE_403_OWNER_DIAGNOSTIC_PREVIEW_ONLY",
        "approved_source": SOURCE,
        "approved_operation": OPERATION,
        "original_failure_utc": failure_utc,
        "original_receipt_sha256": fingerprint,
        "unknown_shared_rate_budget": True,
        "maximum_approved_gets": 1,
        "public_gets_requested": 0,
        "operating_miner_receipt_modified": False,
        "p10_queue_modified": False, "p11_rearmed": False,
        "task_modified": False, "auto_promoted": False,
    }


def _numeric_rate(headers) -> dict:
    def parse(name):
        try:
            value = headers.get(name)
        except (TypeError, ValueError, AttributeError):
            return None
        if (type(value) is not str
                or re.fullmatch(r"[0-9]{1,12}", value.strip()) is None):
            return None
        return int(value.strip())
    remaining = parse("X-RateLimit-Remaining")
    reset = parse("X-RateLimit-Reset")
    return {
        "remaining":remaining if remaining is not None and remaining <= 500000 else None,
        "reset_epoch":reset if reset is not None and reset <= 4102444800 else None,
    }


def _write_once(path: Path, receipt: dict) -> None:
    # x mode and an operation receipt BEFORE network make this nonreplayable
    # even after a crash, timeout, malformed response or owner interruption.
    raw = json.dumps(receipt, sort_keys=True, ensure_ascii=True).encode("ascii")
    if len(raw) > 1500:
        raise One403Error("receipt exceeds hard bound")
    with path.open("xb") as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())


def _seal(path: Path, original: dict, newer: dict) -> None:
    if (not path.is_file() or path.is_symlink()
            or json.loads(path.read_text(encoding="ascii")) != original):
        raise One403Error("existing one-shot receipt changed")
    body = json.dumps(newer, sort_keys=True, ensure_ascii=True).encode("ascii")
    if len(body) > 1500:
        raise One403Error("completed receipt exceeds hard bound")
    fd, temporary = tempfile.mkstemp(
        prefix=".ucie_403_probe_",suffix=".tmp",dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(body)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def apply_one(root: Path, *, expected_sha256: str, consent: str,
              now: datetime | None = None, fetch=None) -> dict:
    if (consent != CONSENT or type(expected_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None):
        raise One403Error("exact owner one-get consent/fingerprint required")
    now = datetime.now(timezone.utc) if now is None else now
    rate._stamp(now)
    root = _scope(root)
    if root == owner.ROOT.resolve() and fetch is not None:
        raise One403Error("real owner cannot inject transport")
    with worker._single_instance(root / "runtime") as acquired:
        if not acquired:
            raise One403Error("public miner already running")
        evidence = preview(root, now=now)
        if evidence["original_receipt_sha256"] != expected_sha256:
            raise One403Error("first-party prior 403 receipt changed")
        path = _probe_path(root)
        operation = sha256(
            (SCHEMA+"|"+expected_sha256+"|"+rate._stamp(now)).encode("ascii")
        ).hexdigest()
        prepared = {
            "schema":SCHEMA,"state":"PREPARED",
            "operation_sha256":operation,"prior_sha256":expected_sha256,
            "requested_utc":rate._stamp(now),
            "source_id":"repo:"+SOURCE,"public_gets_requested":0,
        }
        _write_once(path, prepared)
        seen = 0
        snapshot = {"remaining":None,"reset_epoch":None}
        state = "FAILED"
        error_class = None
        reason = None
        def one_fetch(url):
            nonlocal seen
            if url != public_feed_url(SOURCE) or seen:
                raise One403Error("exact approved one GET only")
            seen=1
            if fetch is not None:  # marked synthetic test root only
                return fetch(url)
            return public_feed_get(
                url, observe_rate_headers=lambda h:
                    snapshot.update(_numeric_rate(h)))
        try:
            payload = one_fetch(public_feed_url(SOURCE))
            if not isinstance(payload,list) or len(payload)>20:
                raise One403Error("unexpected bounded GitHub public metadata")
            state = "SUCCESS"
        except Exception as exc:
            error_class = classify_stage10_discovery_error(exc)
            http = rate._http_error(exc)
            if http is not None:
                snapshot.update(_numeric_rate(http.headers))
                advice = rate.calculate(exc, now=now, prior=None)
                reason = advice["reason"] if advice else None
        outcome = {
            **prepared, "state":state,
            "public_gets_requested":seen,
            "sanitized_error_category":error_class,
            "rate_hold_reason":reason,
            "rate_remaining":snapshot["remaining"],
            "rate_reset_epoch":snapshot["reset_epoch"],
        }
        _seal(path,prepared,outcome)
    return {
        "schema":SCHEMA,
        "status":("EXACT_ONE_403_DIAGNOSTIC_SUCCEEDED_UNVERIFIED"
                  if state=="SUCCESS" else
                  "EXACT_ONE_403_DIAGNOSTIC_FAILED_NO_RETRY"),
        "operation_sha256":operation,
        "public_gets_requested":seen,
        "source_id":"repo:"+SOURCE,
        "sanitized_error_category":error_class,
        "rate_hold_reason":reason,
        "rate_remaining":snapshot["remaining"],
        "rate_reset_epoch":snapshot["reset_epoch"],
        "base_miner_original_last_run_modified":False,
        "p10_queue_modified":False,"p11_rearmed":False,
        "task_modified":False,"auto_promoted":False,
        "shared_quota_proven_for_future_runs":False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE owner one 403 diagnostic")
    parser.add_argument("--ucie-root",type=Path,required=True)
    parser.add_argument("--apply",action="store_true")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--owner-consent")
    args=parser.parse_args()
    try:
        if args.apply:
            if args.expected_sha256 is None or args.owner_consent is None:
                raise One403Error("explicit one-shot owner approval required")
            value=apply_one(args.ucie_root,
                            expected_sha256=args.expected_sha256,
                            consent=args.owner_consent)
        else:
            if args.expected_sha256 is not None or args.owner_consent is not None:
                raise One403Error("preview accepts no mutation fields")
            value=preview(args.ucie_root)
    except (One403Error,OSError,ValueError) as exc:
        print(json.dumps({
            "schema":SCHEMA,"status":"EXACT_ONE_403_DIAGNOSTIC_FAIL_CLOSED",
            "error_type":type(exc).__name__,
            "public_gets_requested":None,
            "p10_queue_modified":False,"p11_rearmed":False,
            "task_modified":False,"auto_promoted":False,
        },sort_keys=True))
        return 2
    print(json.dumps(value,sort_keys=True))
    return 0 if value["status"] != "EXACT_ONE_403_DIAGNOSTIC_FAILED_NO_RETRY" else 3


if __name__ == "__main__":
    raise SystemExit(main())
