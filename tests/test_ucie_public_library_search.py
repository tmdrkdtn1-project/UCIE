"""UCIE Library actual search over the existing bounded public indices only."""
from contextlib import closing
from pathlib import Path
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from ucie_miner.public_discovery import SOURCES, DiscoveryError
from ucie_miner.public_library_search import search_public_library
from ucie_miner.public_external_history import (
    OPT_IN_FILE, OPT_IN_TOKEN, optional_external_history_backfill, DB_NAME,
)
from ucie_miner.public_candidate_staging import (
    stage_public_candidates, DB_NAME as RECENT_DB,
)
from ucie_miner.public_batch import build_public_batch
from test_ucie_stage9_batch import NOW, metadata, evidence
from test_ucie_stage13_external_history import upstream_pr

ROOT = Path(__file__).resolve().parents[1]


class PublicLibrarySearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)

    def test_absent_indexes_and_unrelated_dbs_never_changed(self):
        operating = self.root / "runtime" / "public_miner.sqlite3"
        operating.write_bytes(b"DO_NOT_TOUCH_OPERATING_DATA")
        response = search_public_library(self.root)
        self.assertEqual(response["status"], "PUBLIC_LIBRARY_INDEXES_ABSENT_NO_GO")
        self.assertEqual(response["results"], [])
        self.assertEqual(response["network_gets"], 0)
        self.assertEqual(response["operating_database_writes"], 0)
        self.assertFalse((self.root / "runtime" / DB_NAME).exists())
        self.assertFalse((self.root / "runtime" / RECENT_DB).exists())
        self.assertEqual(operating.read_bytes(), b"DO_NOT_TOUCH_OPERATING_DATA")

    def test_actual_stage13_and_stage10_metadata_search(self):
        runtime = self.root / "runtime"
        (runtime / OPT_IN_FILE).write_text(OPT_IN_TOKEN, encoding="ascii")

        def public_fixture(url):
            source = next(s for s in SOURCES if f"/repos/{s}/" in url)
            return ([upstream_pr(source, 1234, title="Fix regression in public API")], 40)

        history = optional_external_history_backfill(self.root, fetch=public_fixture)
        self.assertEqual(history["new_unverified_evidence_revisions"], 5)
        latest = build_public_batch(
            metadata_fetch=metadata, evidence_fetch=evidence,
            now=NOW, max_enrich=2)
        stage_public_candidates(
            latest, root=self.root, allow_disk_write=True, observed_utc=NOW)
        prev = {(runtime / DB_NAME): (runtime / DB_NAME).read_bytes(),
                (runtime / RECENT_DB): (runtime / RECENT_DB).read_bytes()}

        all_results = search_public_library(self.root, limit=15)
        self.assertEqual(all_results["status"],
                         "PUBLIC_LIBRARY_INDEX_SEARCH_PREVIEW_NO_GO")
        self.assertTrue(all_results["stage13_history_present"])
        self.assertTrue(all_results["stage10_recent_present"])
        self.assertGreaterEqual(all_results["result_count"], 5)
        self.assertEqual(len({(x["public_url"], x["revision_sha"])
                              for x in all_results["results"]}),
                         all_results["result_count"])
        self.assertTrue(all(x["status"] ==
                            "UNVERIFIED_PUBLIC_RESEARCH_ONLY_NO_GO" for x
                            in all_results["results"]))
        self.assertTrue(all(not x["installable_skill"]
                            for x in all_results["results"]))
        python_only = search_public_library(
            self.root, source="python/cpython", tag="REGRESSION")
        self.assertTrue(python_only["results"])
        self.assertTrue(all(item["skill_id"] == "python-runtime-safety"
                            and item["source"] == "python/cpython"
                            and "REGRESSION" in item["technical_tags"]
                            for item in python_only["results"]))
        all_skills = search_public_library(
            self.root, skill_id="mcp-api-compatibility")
        self.assertTrue(all(x["source"] == "modelcontextprotocol/python-sdk"
                            for x in all_skills["results"]))
        historical_only = search_public_library(
            self.root, index="history", limit=10)
        self.assertEqual(historical_only["result_count"], 5)
        self.assertTrue(all(x["record_origin"] == "STAGE13_PUBLIC_HISTORY"
                            for x in historical_only["results"]))
        recent_only = search_public_library(
            self.root, index="recent", limit=10)
        self.assertGreaterEqual(recent_only["result_count"], 1)
        self.assertTrue(all(x["record_origin"] ==
                            "STAGE10_UNVERIFIED_RESEARCH"
                            for x in recent_only["results"]))
        self.assertEqual(
            {p: p.read_bytes() for p in prev}, prev)

    def test_filters_fail_closed_without_any_io(self):
        for args in (
            {"source": "unknown/private"}, {"skill_id": "unsafe-execute"},
            {"tag": "PRIVATE"}, {"index": "private"}, {"limit": 51}, {"limit": True},
            {"source": "python/cpython", "skill_id": "powershell-safe-calls"},
        ):
            with self.subTest(args=args), self.assertRaises(DiscoveryError):
                search_public_library(self.root, **args)
        self.assertEqual(list((self.root / "runtime").iterdir()), [])

    def test_search_cli_is_read_only_and_needs_no_live_opt_in(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        run = subprocess.run(
            [sys.executable, "-m", "ucie_miner", "search-library",
             "--source", "python/cpython", "--limit", "5"],
            text=True, capture_output=True, cwd=ROOT, env=env, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result["schema"], "UCIE_PUBLIC_LIBRARY_SEARCH_V1")
        self.assertEqual(result["network_gets"], 0)
        self.assertFalse(result["production_approved"])


if __name__ == "__main__":
    unittest.main()
