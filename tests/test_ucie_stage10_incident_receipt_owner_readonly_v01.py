"""Exact UCIE-only incident receipt metadata: no raw errors or source contents.

One optional owner-host, on-demand read of the fixed UCIE run_history.jsonl.
No database or Windows scheduler access, no task registration and no writes.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import unittest

from ucie_miner.public_discovery import STAGE10_FAILURE_PHASES

SCHEMA = "UCIE_STAGE10_INCIDENT_METADATA_READONLY_V01"
CATEGORIES = frozenset({
    "UPSTREAM_HTTP_429", "UPSTREAM_HTTP_403", "UPSTREAM_HTTP_OTHER",
    "UPSTREAM_NETWORK_FAILURE", "UPSTREAM_IO_OR_TIMEOUT",
    "PUBLIC_JSON_INVALID", "DISCOVERY_VALIDATION_OR_RESPONSE_REJECTED",
    "OTHER_FAILURE",
})
TARGET_STARTS = frozenset({
    "2026-11-08T04:37:11+00:00",
    "2026-11-08T05:37:11+00:00",
})
MAX_BYTES = 65536
MAX_RECEIPT = 4096


def sanitize_receipt(item: dict) -> dict:
    if type(item) is not dict or item.get("schema") != "UCIE_MINER_CYCLE_V1":
        raise ValueError("invalid UCIE run schema")
    if item.get("status") != "COLLECTED_UNVERIFIED":
        raise ValueError("not a successful legacy collector run")
    stage = item.get("stage10_status")
    if stage not in (
        "STAGE10_HOURLY_FAILED_NO_GO", "STAGE10_HOURLY_PARTIAL_NO_GO",
        "STAGE10_UNVERIFIED_STAGED_NO_GO", "STAGE10_HOURLY_DISABLED"):
        raise ValueError("unknown optional stage status")
    result = {"started_utc": item["started_utc"], "legacy_status": item["status"],
              "stage10_status": stage, "stage10_error_type": None,
              "stage10_error_category": None, "stage10_error_phase": None}
    if stage == "STAGE10_HOURLY_FAILED_NO_GO":
        name = item.get("stage10_error_type")
        category = item.get("stage10_error_category")
        phase = item.get("stage10_error_phase")
        if (type(name) is not str or not name.isascii()
                or not name.isidentifier() or len(name) > 80
                or category not in CATEGORIES or phase not in STAGE10_FAILURE_PHASES):
            raise ValueError("untrusted stage10 error metadata")
        result["stage10_error_type"] = name
        result["stage10_error_category"] = category
        result["stage10_error_phase"] = phase
    return result


class UCIEStage10IncidentReceiptTests(unittest.TestCase):
    def test_synthetic_failure_classification_retains_no_raw_message(self):
        sample = {
            "schema": "UCIE_MINER_CYCLE_V1",
            "status": "COLLECTED_UNVERIFIED",
            "started_utc": "2026-11-08T04:37:11+00:00",
            "stage10_status": "STAGE10_HOURLY_FAILED_NO_GO",
            "stage10_error_type": "DiscoveryError",
            "stage10_error_category": "UPSTREAM_HTTP_429",
            "stage10_error_phase": "STAGE10_BATCH",
            "untrusted_external_message": "NEVER_FORWARD",
        }
        result = sanitize_receipt(sample)
        self.assertEqual(result["stage10_error_phase"], "STAGE10_BATCH")
        self.assertEqual(result["stage10_error_category"], "UPSTREAM_HTTP_429")
        self.assertNotIn("untrusted_external_message", result)
        self.assertNotIn("NEVER_FORWARD", json.dumps(result))
        self.assertEqual(len(result), 6)

    def test_malformed_or_forged_error_metadata_is_rejected(self):
        item = {
            "schema": "UCIE_MINER_CYCLE_V1",
            "status": "COLLECTED_UNVERIFIED",
            "started_utc": "2026-11-08T04:37:11+00:00",
            "stage10_status": "STAGE10_HOURLY_FAILED_NO_GO",
            "stage10_error_type": "DiscoveryError",
            "stage10_error_category": "UPSTREAM_HTTP_429",
            "stage10_error_phase": "STAGE10_BATCH",
        }
        for key, value in (
            ("stage10_error_type", "file/secret"),
            ("stage10_error_category", "RELEASED"),
            ("stage10_error_phase", "SCHEDULER_CHANGED"),
        ):
            altered = dict(item, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                sanitize_receipt(altered)

    @unittest.skipUnless(os.name == "nt", "Owner D:/UCIE Windows only")
    def test_owner_exact_historical_stage10_receipt(self):
        root = Path(__file__).resolve().parents[1]
        if root.is_symlink() or root.resolve() != Path("D:/UCIE").resolve():
            self.skipTest("not exact UCIE owner checkout")
        runtime = root / "runtime"
        target = runtime / "run_history.jsonl"
        self.assertTrue(runtime.is_dir() and not runtime.is_symlink())
        self.assertTrue(target.is_file() and not target.is_symlink())
        with target.open("rb") as stream:
            size = stream.seek(0, 2)
            stream.seek(max(0, size - MAX_BYTES))
            raw = stream.read(MAX_BYTES)
        if size > MAX_BYTES:
            first_end = raw.find(b"\n")
            self.assertGreaterEqual(first_end, 0)
            raw = raw[first_end + 1:]
        lines = raw.splitlines()[-16:]
        matches = []
        for line in lines:
            self.assertLessEqual(len(line), MAX_RECEIPT)
            row = json.loads(line.decode("utf-8", "strict"))
            if row.get("started_utc") in TARGET_STARTS:
                matches.append(sanitize_receipt(row))
        matches.sort(key=lambda value: value["started_utc"])
        self.assertLessEqual(len(matches), 2)
        output = {"schema": SCHEMA,
                  "incident_window": "2026-11-08T04:37-05:37Z",
                  "matching_ucie_legacy_receipts": matches,
                  "historical_root_cause_proven": False,
                  "scheduler_event_201_root_cause_proven": False,
                  "operating_database_writes": 0,
                  "task_scheduler_changes": 0,
                  "other_project_data_included": False}
        print("UCIE_STAGE10_INCIDENT_METADATA_READONLY=" +
              json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
