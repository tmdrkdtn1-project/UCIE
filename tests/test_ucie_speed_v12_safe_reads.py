"""SPEED V1.2 UCIE-only source patch acceptance: no network or live quota."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ucie_miner.core import mine_once, PUBLIC_SOURCES, MiningError
from ucie_miner.worker import run_cycle

LIST = "pulls?state=closed&sort=updated&direction=desc&per_page=20"
STAMP = "2026-10-01T10:00:00Z"


def synthetic_fetch(url):
    # Exactly the two UCIE public source paths, NEVER a live request.
    if LIST in url:
        return [{"number": 42, "title": "Fix test regression",
                 "merged_at": STAMP}]
    if "/pulls/42/files?per_page=30" in url:
        return [{"filename": "tests/test_case.py", "patch": "+raise RuntimeError()"}]
    raise AssertionError("unexpected synthetic URL route")


def db_snapshot(root):
    # sqlite3.Connection's context manager DOES NOT CLOSE the handle.
    # Explicit close is essential for Windows Python 3.15 tempdir cleanup.
    conn = sqlite3.connect(root / "runtime" / "public_miner.sqlite3")
    try:
        candidates = conn.execute(
            "SELECT source,pr_number,public_url,merged_at,evidence_sha256,"
            "tags_json,status FROM candidates ORDER BY source,pr_number"
        ).fetchall()
        runs = conn.execute(
            "SELECT sources_count,added_candidates,status FROM runs ORDER BY run_id"
        ).fetchall()
        return candidates, runs
    finally:
        conn.close()


class UCIESpeedSafeReadLanes(unittest.TestCase):
    def test_default_is_sequential_and_preserves_old_sqlite_semantics(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            calls = []
            def serial_get(url):
                calls.append(url)
                return synthetic_fetch(url)
            baseline = mine_once(Path(a), fetch=serial_get)
            self.assertEqual(len(calls), 4)
            self.assertIn("python/cpython", calls[0])
            self.assertTrue(calls[1].endswith("/pulls/42/files?per_page=30"))
            self.assertIn("PowerShell/PowerShell", calls[2])
            parallel = mine_once(Path(b), fetch=synthetic_fetch, read_workers=2)
            self.assertEqual(baseline, parallel)
            self.assertEqual(db_snapshot(Path(a)), db_snapshot(Path(b)))
            self.assertEqual(baseline["verification_pass"], 0)
            self.assertIs(baseline["production_approved"], False)

    def test_two_lists_really_overlap_with_only_two_bounded_workers(self):
        # Barrier makes overlap mandatory; no wallclock 2x claim from this test.
        gate = threading.Barrier(2, timeout=3)
        lock = threading.Lock()
        intervals = {}
        calls = []
        def only_public_lists(url):
            self.assertIn(LIST, url)
            self.assertTrue(any(
                url.startswith("https://api.github.com/repos/" + src + "/")
                for src in PUBLIC_SOURCES
            ))
            source = next(s for s in PUBLIC_SOURCES if "/" + s + "/" in url)
            start = time.perf_counter_ns()
            gate.wait()
            time.sleep(0.03)
            end = time.perf_counter_ns()
            with lock:
                calls.append(source)
                intervals[source] = (start, end)
            return []
        with tempfile.TemporaryDirectory() as root:
            out = mine_once(Path(root), fetch=only_public_lists, read_workers=2)
            self.assertEqual(out["new_candidates"], 0)
            self.assertEqual(out["sources_checked"], 2)
            self.assertEqual(len(calls), 2)
            self.assertEqual(set(intervals), set(PUBLIC_SOURCES))
            x, y = (intervals[source] for source in PUBLIC_SOURCES)
            self.assertLess(max(x[0], y[0]), min(x[1], y[1]))
            self.assertEqual(len(db_snapshot(Path(root))[1]), 1)

    def test_invalid_worker_expansion_and_scope_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            for bad in (0, 3, True, 1.1, "2", -1):
                with self.subTest(value=bad), self.assertRaises(MiningError):
                    mine_once(Path(root), fetch=lambda u: self.fail("unexpected GET"),
                              read_workers=bad)
            with self.assertRaises(MiningError):
                mine_once(Path(root), fetch=lambda u: self.fail("unexpected GET"),
                          sources=(PUBLIC_SOURCES[0],), read_workers=2)
            with self.assertRaises(MiningError):
                mine_once(Path(root), fetch=lambda u: self.fail("unexpected GET"),
                          sources=("OTHER/private",), read_workers=1)

    def test_untrusted_rate_failure_is_not_retried_or_committed(self):
        calls = Counter()
        lock = threading.Lock()
        def fail_429(url):
            with lock:
                calls[url] += 1
            if "python/cpython" in url:
                raise RuntimeError("429 quota limit")
            return []
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(RuntimeError, "429"):
                mine_once(Path(root), fetch=fail_429, read_workers=2)
            self.assertEqual(sum(calls.values()), 2)
            self.assertEqual(max(calls.values()), 1)
            conn = sqlite3.connect(Path(root) / "runtime" / "public_miner.sqlite3")
            try:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0], 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 0)
            finally:
                conn.close()

    def test_late_failure_rolls_back_single_writer(self):
        def fail_second(url):
            if "PowerShell/PowerShell" in url and LIST in url:
                raise RuntimeError("upstream failure")
            return synthetic_fetch(url)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(RuntimeError):
                mine_once(Path(root), fetch=fail_second, read_workers=1)
            self.assertEqual(db_snapshot(Path(root)), ([], []))

    def test_existing_candidate_no_duplicate_files_or_db_row(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            mine_once(root, fetch=synthetic_fetch, read_workers=2)
            calls = []
            def record(url):
                calls.append(url)
                return synthetic_fetch(url)
            output = mine_once(root, fetch=record, read_workers=1)
            self.assertEqual(output["new_candidates"], 0)
            self.assertEqual(len(calls), 2)  # list GETs only; candidate files skipped
            self.assertEqual(len(db_snapshot(root)[0]), 2)

    def test_worker_receipt_uses_bounded_local_monotonic_durations(self):
        def collect(_):
            return {"status":"COLLECTED_UNVERIFIED", "new_candidates":0,
                    "sources_checked":2,"verification_pass":0,
                    "production_approved":False}
        def report(root):
            dest = root / "runtime" / "reports"
            dest.mkdir(exist_ok=True)
            path = dest / "synthetic.md"
            path.write_text("unverified")
            return path
        with tempfile.TemporaryDirectory() as root:
            import json
            from pathlib import Path
            path = Path(root)
            result = run_cycle(path, collect=collect, write_report=report)
            self.assertEqual(result["status"], "COLLECTED_UNVERIFIED")
            for key in ("cycle_elapsed_ms", "collection_elapsed_ms", "report_elapsed_ms"):
                self.assertIs(type(result[key]), int)
                self.assertGreaterEqual(result[key], 0)
                self.assertLessEqual(result[key], 3_600_000)
            stored = json.loads((path/"runtime"/"last_run.json").read_text())
            self.assertEqual(stored, result)
            self.assertEqual(len((path/"runtime"/"run_history.jsonl").read_text().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
