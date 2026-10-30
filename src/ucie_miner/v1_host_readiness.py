"""One-shot UCIE-only V1 host acceptance observations; never an approval engine.

No network, writes, scheduler operation, promotion, private source scan or
signing. Operates only on an explicit dedicated UCIE root and existing
bounded read-only ledgers; honest NO_GO for unobserved product requirements.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from .core import PUBLIC_SOURCES
from .public_candidate_staging import inspect_staged_candidates
from .pending_queue import inspect_queue
from .p11_closed_loop import status as inspect_experience_loop
from .product_v1 import integrated_product_preview
from .source_registry import preview_source_registry

SCHEMA = "UCIE_V1_LOCAL_READONLY_ACCEPTANCE_OBSERVATIONS_V1"
MAX_REPORT_BYTES = 24000
SYNTHETIC_SCANDIR = """import os
from concurrent.futures import ThreadPoolExecutor
def review(folder, callback):
    iterator = os.scandir(folder)
    with ThreadPoolExecutor(max_workers=2) as pool:
        return pool.submit(callback, iterator).result()
"""


class HostAcceptanceError(ValueError):
    pass


def _root(root: Path) -> tuple[Path, Path]:
    if (type(root) is not Path or root.name.casefold() != "ucie"
            or root.is_symlink() or not root.is_dir()):
        raise HostAcceptanceError("DEDICATED_UCIE_ROOT_REQUIRED")
    runtime = root / "runtime"
    if runtime.is_symlink() or (runtime.exists() and not runtime.is_dir()):
        raise HostAcceptanceError("UCIE_RUNTIME_PATH_UNSAFE")
    return root, runtime


def _utc(value: object) -> datetime:
    if type(value) is not str or not 10 <= len(value) <= 55:
        raise HostAcceptanceError("INVALID_MINER_TIME")
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HostAcceptanceError("INVALID_MINER_TIME") from exc
    if d.tzinfo is None or d.utcoffset().total_seconds() != 0:
        raise HostAcceptanceError("MINER_TIME_NOT_UTC")
    return d


def _receipt(runtime: Path) -> dict:
    path = runtime / "last_run.json"
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise HostAcceptanceError("UNSAFE_MINER_RECEIPT")
    if not path.is_file():
        return {"status": "LAST_CYCLE_RECEIPT_NOT_FOUND"}
    if not 0 < path.stat().st_size <= 4096:
        raise HostAcceptanceError("LAST_CYCLE_RECEIPT_SIZE_INVALID")
    try:
        x = json.loads(path.read_text(encoding="utf-8"))
        if (type(x) is not dict or x.get("schema") != "UCIE_MINER_CYCLE_V1"
                or x.get("status") not in (
                    "COLLECTED_UNVERIFIED", "COLLECTED_UNVERIFIED_PARTIAL_NO_GO",
                    "COLLECTION_FAILED")
                or x.get("production_approved") is not False
                or x.get("verification_pass") != 0
                or type(x.get("consecutive_failures")) is not int
                or x["consecutive_failures"] < 0):
            raise HostAcceptanceError("UNTRUSTED_LAST_CYCLE_RECEIPT")
        time = _utc(x["finished_utc"])
        return {
            "status": "LAST_CYCLE_RECEIPT_OBSERVED_NOT_AUTHORIZED",
            "last_cycle_status": x["status"],
            "finished_utc": time.isoformat(),
            "consecutive_failures": x["consecutive_failures"],
            "stage10_status": x.get("stage10_status", "NOT_REPORTED"),
        }
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        raise HostAcceptanceError("INVALID_LAST_CYCLE_RECEIPT") from exc


def _miner(runtime: Path, now: datetime) -> dict:
    file = runtime / "public_miner.sqlite3"
    if file.is_symlink() or (file.exists() and not file.is_file()):
        raise HostAcceptanceError("UNSAFE_MINER_DB")
    if not file.exists():
        return {
            "status": "MINER_OPERATING_DB_NOT_FOUND_NO_GO",
            "candidate_count": 0, "run_count": 0,
            "last_run_freshness": "NOT_OBSERVED",
            "continuous_hourly_execution_verified": False,
        }
    try:
        with closing(sqlite3.connect(file.as_uri() + "?mode=ro",
                                     uri=True, timeout=2)) as conn:
            conn.execute("PRAGMA query_only=ON")
            integrity = conn.execute("PRAGMA quick_check(1)").fetchone()[0]
            candidates, invalid, foreign = conn.execute(
                "SELECT COUNT(*),"
                " COALESCE(SUM(CASE WHEN status <> 'UNVERIFIED_CANDIDATE_ONLY' "
                "THEN 1 ELSE 0 END),0),"
                " COALESCE(SUM(CASE WHEN source NOT IN (?,?) "
                "THEN 1 ELSE 0 END),0) FROM candidates", PUBLIC_SOURCES
            ).fetchone()
            runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            last = conn.execute(
                "SELECT at_utc,status FROM runs ORDER BY run_id DESC LIMIT 1"
            ).fetchone()
    except (OSError, sqlite3.Error) as exc:
        raise HostAcceptanceError("MINER_DB_READONLY_INSPECTION_FAILED") from exc
    if integrity != "ok" or invalid or foreign or candidates < 0 or runs < 0:
        raise HostAcceptanceError("MINER_DB_INTEGRITY_OR_PROVENANCE_FAILED")
    if last is not None:
        last_time = _utc(last[0])
        if type(last[1]) is not str or len(last[1]) > 80:
            raise HostAcceptanceError("MINER_RUN_STATUS_MALFORMED")
        age = (now - last_time).total_seconds()
        freshness = ("CLOCK_SKEW_NO_GO" if age < -300 else
                     "FRESH_WITHIN_THREE_HOURS" if age <= 10800 else
                     "STALE_OVER_THREE_HOURS_NO_GO")
    else:
        age, freshness = None, "NO_STORED_RUN_NO_GO"
    receipt = _receipt(runtime)
    if receipt["status"] == "LAST_CYCLE_RECEIPT_OBSERVED_NOT_AUTHORIZED":
        age_receipt = (now - _utc(receipt["finished_utc"])).total_seconds()
        if age_receipt < -300:
            freshness = "CLOCK_SKEW_NO_GO"
        elif age_receipt > 10800:
            freshness = "STALE_OVER_THREE_HOURS_NO_GO"
        # A last-run file is not a registered Windows scheduler receipt.
    return {
        "status": "MINER_DB_READONLY_OBSERVED_UNVERIFIED",
        "database_integrity": "ok",
        "candidate_count": candidates, "run_count": runs,
        "invalid_candidate_states": invalid, "foreign_sources": foreign,
        "last_stored_status": last[1] if last else None,
        "last_stored_run_at_utc": last[0] if last else None,
        "last_stored_run_age_seconds": max(0, int(age)) if age is not None else None,
        "last_run_freshness": freshness,
        "last_cycle_receipt": receipt,
        "continuous_hourly_execution_verified": False,
        "windows_scheduled_task_verified": False,
        "auto_promotion_verified_active": False,
        "new_approved_rules": 0,
    }


def _component(label: str, action) -> dict:
    try:
        x = action()
        if type(x) is not dict or "status" not in x:
            raise HostAcceptanceError("COMPONENT_CONTRACT_MISMATCH")
        return x
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError,
            ImportError) as exc:
        return {
            "status": "COMPONENT_READONLY_CHECK_FAILED_NO_GO",
            "component": label, "error_type": type(exc).__name__,
        }


def observe_ucie_host(root: Path, *, serial4_pack: Path | None = None,
                      owner_public_trust: Path | None = None,
                      serial5_pack: Path | None = None,
                      now: datetime | None = None) -> dict:
    """Read-only bounded observation. Output is never a V1 approval."""
    root, runtime = _root(root)
    if (serial4_pack is None) != (owner_public_trust is None):
        raise HostAcceptanceError("SIGNATURE_PACK_AND_PUBLIC_TRUST_MUST_BE_PAIRED")
    if serial5_pack is not None and serial4_pack is None:
        raise HostAcceptanceError("SERIAL5_REQUIRES_SERIAL4")
    current = now or datetime.now(timezone.utc)
    if not isinstance(current, datetime) or current.tzinfo is None:
        raise HostAcceptanceError("AWARE_TIME_REQUIRED")
    current = current.astimezone(timezone.utc)
    miner = _component("public_miner", lambda: _miner(runtime, current))
    staging = _component("stage10", lambda: inspect_staged_candidates(root))
    queue = _component("pending_queue", lambda: inspect_queue(root, limit=5))
    learning = _component("p11", lambda: inspect_experience_loop(root))
    registry = _component(
        "approved_sources",
        lambda: preview_source_registry(include_research=False))
    product = _component(
        "product_v1",
        lambda: integrated_product_preview(
            root, limit=5, signed_serial4=serial4_pack,
            owner_public_trust=owner_public_trust, signed_serial5=serial5_pack))
    signed = {
        "status": "EXISTING_OWNER_SIGNED_PACK_NOT_SUPPLIED_NO_GO",
        "verified_rule_count": 0, "synthetic_signed_scan_matches": 0,
    }
    if serial4_pack is not None:
        def scan():
            from .existing_rule_inspection import inspect_existing_python
            from .signed_rule_library import inspect_signed_library
            shelf = inspect_signed_library(
                root, serial4_pack=serial4_pack,
                owner_public_trust=owner_public_trust, serial5_pack=serial5_pack)
            scanned = inspect_existing_python(
                SYNTHETIC_SCANDIR, root=root, serial4_pack=serial4_pack,
                owner_public_trust=owner_public_trust, serial5_pack=serial5_pack)
            if (shelf.get("signed_rule_count") not in (4, 5)
                    or scanned.get("source_executed") is not False
                    or scanned.get("source_files_read") != 0
                    or scanned.get("database_writes") != 0
                    or scanned.get("network_requests") != 0
                    or scanned.get("auto_promoted") is not False
                    or scanned.get("existing_signed_manual_matches") != 1
                    or not any(
                        f.get("rule_id") == "PY_SCANDIR_SHARED_ITERATOR_RACE"
                        and f.get("authorization") ==
                        "EXISTING_OWNER_SIGNED_MANUAL_ONLY"
                        for f in scanned["findings"])):
                raise HostAcceptanceError("EXISTING_SIGNED_STATIC_SCAN_NO_GO")
            return {
                "status": "CURRENT_PACK_VERIFIED_ON_UCIE_SYNTHETIC_INPUT_ONLY",
                "verified_rule_count": shelf["signed_rule_count"],
                "synthetic_signed_scan_matches": 1,
                "pack_sha256s": shelf["source_pack_sha256s"],
                "real_user_source_scanned": False,
                "production_version_applicability_verified": False,
            }
        signed = _component("signed_manual", scan)
    failures = []
    if miner["status"] != "MINER_DB_READONLY_OBSERVED_UNVERIFIED":
        failures.append("MINER_OPERATING_DB_UNVERIFIED")
    elif miner["last_run_freshness"] != "FRESH_WITHIN_THREE_HOURS":
        failures.append("MINER_LAST_RUN_NOT_FRESH")
    if staging["status"] != "UNVERIFIED_CANDIDATE_STAGING_INSPECTED_NO_GO":
        failures.append("PUBLIC_CANDIDATE_STAGE_NOT_OBSERVED")
    if queue["status"] != "READ_ONLY_PENDING_QUEUE_SNAPSHOT":
        failures.append("PENDING_QUEUE_NOT_OBSERVED")
    if learning["status"] != "P11_PUBLIC_EVIDENCE_EXPERIENCE_READ_ONLY":
        failures.append("P11_EXPERIENCE_LOOP_NOT_OBSERVED")
    if product["status"] != "P9_INTEGRATED_READ_ONLY_PRODUCT_PREVIEW_NO_GO":
        failures.append("PRODUCT_PREVIEW_NOT_VERIFIED")
    if signed["status"] != "CURRENT_PACK_VERIFIED_ON_UCIE_SYNTHETIC_INPUT_ONLY":
        failures.append("CURRENT_OWNER_SIGNED_PACK_NOT_VERIFIED")
    failures.extend([
        "WINDOWS_SCHEDULED_TASK_RUN_RESULT_NOT_INSPECTED",
        "REAL_HOST_SIGNED_RULE_SCAN_OF_EXPLICIT_SOURCE_NOT_ATTESTED",
        "APPROVED_GENERIC_PACKAGE_EXPORT_NOT_EVIDENCED",
        "UCIE_V1_COMPLETE_PRODUCT_ACCEPTANCE_NOT_ATTESTED",
    ])
    result = {
        "schema": SCHEMA, "status": "UCIE_V1_LOCAL_OBSERVATIONS_NO_GO",
        "inspection_utc": current.isoformat(), "collector": miner,
        "stage10": {
            "status": staging["status"],
            "candidate_revisions": staging.get("candidate_revisions", 0),
            "git_commit_revisions": staging.get("git_commit_revisions", 0),
            "error_type": staging.get("error_type"),
        },
        "queue": {
            "status": queue["status"],
            "counts": queue.get("counts", {}),
            "error_type": queue.get("error_type"),
        },
        "experience": {
            "status": learning["status"],
            "first_party_experiences": learning.get("first_party_experiences", 0),
            "synthetic_equivalence_observed":
                learning.get("synthetic_equivalence_observed", 0),
            "error_type": learning.get("error_type"),
        },
        "approved_sources": {
            "status": registry["status"],
            "source_count": registry.get("active_source_count", 0),
        },
        "product": {
            "status": product["status"],
            "catalog_returned_count": product.get(
                "unified_catalog_search", {}).get("returned_count", 0),
            "blockers": product.get("gates_blocking_product_acceptance", []),
            "error_type": product.get("error_type"),
        },
        "signed_manual": signed,
        "blockers": failures,
        "read_only_database_statements": True,
        "network_requests_this_command": 0,
        "scheduler_actions_this_command": 0,
        "rule_promotion_actions_this_command": 0,
        "pack_signing_actions_this_command": 0,
        "model_weight_changes_this_command": 0,
        "real_host_v1_accepted": False,
    }
    if len(json.dumps(result, ensure_ascii=True).encode("utf-8")) > MAX_REPORT_BYTES:
        raise HostAcceptanceError("HOST_REPORT_SIZE_EXCEEDED")
    return result


def main() -> int:
    p = argparse.ArgumentParser(
        description="One-shot read-only observations, never UCIE V1 approval")
    p.add_argument("--ucie-root", type=Path, required=True)
    p.add_argument("--serial4-pack", type=Path)
    p.add_argument("--owner-public-trust", type=Path)
    p.add_argument("--serial5-pack", type=Path)
    args = p.parse_args()
    try:
        report = observe_ucie_host(
            args.ucie_root, serial4_pack=args.serial4_pack,
            owner_public_trust=args.owner_public_trust,
            serial5_pack=args.serial5_pack)
    except (HostAcceptanceError, ValueError, OSError, sqlite3.Error):
        report = {
            "schema": SCHEMA, "status": "UCIE_V1_HOST_INSPECTION_FAIL_CLOSED",
            "real_host_v1_accepted": False,
            "scheduler_actions_this_command": 0,
            "rule_promotion_actions_this_command": 0,
            "network_requests_this_command": 0,
        }
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 2 if report["status"] == "UCIE_V1_HOST_INSPECTION_FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
