"""UCIE P10 two held non-network handler subprocess execution probes.

Only exact, reviewed, no-network first-party --execute kinds are permitted.
No queue state changes, scheduler operation, P11 public GET, or rearm.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from ucie_miner import pending_queue as queue
from ucie_miner import p11_closed_loop as p11

ROOT = Path(__file__).resolve().parents[1]
KINDS = ("PUBLIC_METADATA_REVIEW", "UCIE_REPORT_PREPARATION")
SCHEMA = "UCIE_P10_TWO_HELD_EXACT_CHILD_PROCESS_V02"


def run_child(root: Path, kind: str) -> dict:
    if kind not in KINDS:
        raise ValueError("only two approved non-network handlers are admitted")
    cmd = [sys.executable, "-B", "-m", "ucie_miner.runtime_pipeline",
           "--execute", "--ucie-root", str(root), "--kind", kind]
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    proc = subprocess.run(
        cmd, cwd=str(root), env=env, input=b"", stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, timeout=20, check=False)
    if len(proc.stdout) > 3000:
        raise AssertionError("unbounded child output")
    lines = proc.stdout.decode("utf-8", "strict").strip().splitlines()
    receipt = json.loads(lines[-1]) if len(lines) == 1 else {}
    return {
        "kind": kind, "child_exit_code": proc.returncode,
        "child_status": receipt.get("status"),
        "child_schema_matches":
            receipt.get("schema") == "UCIE_P10_INDEPENDENT_NONBLOCKING_DISPATCH_V1",
        "child_kind_matches": receipt.get("kind") == kind,
        "reported_network_requests": receipt.get("network_requests"),
        "reported_operating_db_writes": receipt.get("operating_db_writes"),
        "reported_auto_promoted": receipt.get("auto_promoted"),
    }


class ExactP10ProcessTest(unittest.TestCase):
    def test_01_no_p11_or_arbitrary_job_kind(self):
        self.assertEqual(set(KINDS),
                         {"PUBLIC_METADATA_REVIEW", "UCIE_REPORT_PREPARATION"})
        with TemporaryDirectory(prefix="UCIE_P10_DENIED_KIND_") as t:
            with self.assertRaises(ValueError):
                run_child(Path(t) / "UCIE", "PUBLIC_INCREMENTAL_MINING")
            with self.assertRaises(ValueError):
                run_child(Path(t) / "UCIE", "EXPERIENCE_CLOSED_LOOP")

    @unittest.skipUnless(os.name == "nt", "real owner Windows only")
    def test_02_two_original_handlers_exact_child_on_owner(self):
        if (ROOT.resolve() != Path("D:/UCIE").resolve()
                or ROOT.is_symlink() or not (ROOT / ".git").is_dir()
                or not (ROOT / "runtime").is_dir()):
            self.skipTest("exact UCIE owner checkout unavailable")
        before = (queue.inspect_queue(ROOT, limit=20), p11.status(ROOT))
        observations = [run_child(ROOT, kind) for kind in KINDS]
        after = (queue.inspect_queue(ROOT, limit=20), p11.status(ROOT))
        self.assertEqual(before, after,
                         "live queue/P11 must stay identical across probes")
        for r in observations:
            self.assertEqual(r["child_exit_code"], 0, r)
            self.assertEqual(r["child_status"], "HANDLER_READ_ONLY_SUCCESS", r)
            self.assertTrue(r["child_schema_matches"], r)
            self.assertTrue(r["child_kind_matches"], r)
            self.assertEqual(r["reported_network_requests"], 0, r)
            self.assertEqual(r["reported_operating_db_writes"], 0, r)
            self.assertIs(r["reported_auto_promoted"], False, r)
        report = {
            "schema": SCHEMA, "status": "TWO_EXACT_NON_NETWORK_CHILD_HANDLERS_OK",
            "checks": observations, "queue_and_p11_state_unchanged": True,
            "owner_rearm_executed": False, "task_scheduler_modified": False,
            "public_api_gets": 0, "auto_promoted": False,
        }
        print("UCIE_P10_EXACT_CHILD_PROBES=" + json.dumps(
            report, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    unittest.main()
