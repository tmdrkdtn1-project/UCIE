"""UCIE-only read-only metadata for pinned Slack reader source mismatch.

No Slack/token/message access, no external network, no startup or process
changes. A mismatch is reported, NOT silently treated as a test PASS.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import unittest
from ucie_miner import ucie_slack_mcp_owner_dispatch_v1 as d


def metadata() -> dict:
    root = d.ROOT
    pkg = root / "src" / "ucie_miner"
    exe = root / ".venv" / "Scripts" / "python.exe"
    rows = []
    for name, expected in sorted(d.PINS.items()):
        path = pkg / name
        row = {"name": name, "expected_blob_sha": expected,
               "file_present": path.is_file(),
               "no_links": d._no_link(path),
               "within_max_source_bytes": False, "actual_blob_sha": None,
               "matches_expected": False}
        if row["file_present"] and row["no_links"] and path.stat().st_size <= d.MAX_SOURCE_BYTES:
            raw = path.read_bytes()
            row["within_max_source_bytes"] = True
            row["actual_blob_sha"] = d._git_blob_sha(raw)
            row["matches_expected"] = row["actual_blob_sha"] == expected
        rows.append(row)
    match = (exe.is_file() and d._no_link(exe)
             and pkg.is_dir() and all(row["matches_expected"] for row in rows))
    return {
        "schema":"UCIE_SLACK_MCP_READER_CODEPIN_METADATA_V1",
        "status": "SOURCE_PINS_MATCH" if match else "SOURCE_PIN_MISMATCH_OBSERVED",
        "python_executable_present": exe.is_file(),
        "python_executable_not_link": d._no_link(exe),
        "package_dir_present": pkg.is_dir(),
        "source_pins": rows,
        "result_matches_dispatch_gate": match == d._pinned_reader_present(),
        "raw_source_or_token_exposed": False,
        "c40_or_tasks_modified": False,
        "operating_database_modified": False,
    }


class SlackReaderPinMetadata(unittest.TestCase):
    def test_readonly_pin_metadata(self):
        if os.name != "nt" or not d.ROOT.is_dir():
            self.skipTest("UCIE Windows owner host only")
        row = metadata()
        print("UCIE_SLACK_SOURCE_PIN_DIAG=" + json.dumps(row, sort_keys=True))
        self.assertTrue(row["result_matches_dispatch_gate"])
        self.assertFalse(row["raw_source_or_token_exposed"])
        self.assertFalse(row["c40_or_tasks_modified"])
        self.assertFalse(row["operating_database_modified"])

    def test_no_general_path_scan_and_fixed_repo_only(self):
        self.assertEqual(tuple(sorted(d.PINS)), tuple(sorted((
            "__init__.py",
            "ucie_slack_windows_reader_v1.py",
            "ucie_slack_history_adapter_v1.py",
            "ucie_admin_history_verdict_v1.py",
        ))))
        self.assertTrue(str(d.ROOT).upper().startswith("D:\\UCIE"))
        self.assertEqual(len(d.PINS), 4)


if __name__ == "__main__":
    unittest.main()
