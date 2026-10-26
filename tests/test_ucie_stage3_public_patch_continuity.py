"""Stage3 bounded public PR rejection continuity, all synthetic and offline."""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ucie_miner.core import mine_once
from ucie_miner.stage3_public_window import rotating_public_pr_rows
from ucie_miner.worker import run_cycle

SOURCE="python/cpython"

class BoundedPublicPatchContinuity(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def test_hourly_window_is_deterministic_and_never_drops_rows(self):
        source=list(range(4))
        self.assertEqual(rotating_public_pr_rows(source,hour_index=0,limit=2),
                         [0,1,2,3])
        self.assertEqual(rotating_public_pr_rows(source,hour_index=1,limit=2),
                         [2,3,0,1])
        self.assertEqual(source,list(range(4)))

    def test_window_strict_bounds(self):
        for kwargs in ({"hour_index":-1,"limit":2},
                       {"hour_index":True,"limit":2},
                       {"hour_index":0,"limit":0},
                       {"hour_index":0,"limit":6}):
            with self.assertRaises(ValueError):
                rotating_public_pr_rows([1,2,3],**kwargs)
        with self.assertRaises(ValueError):
            rotating_public_pr_rows([1]*21,hour_index=0,limit=2)

    def test_oversized_patch_does_not_roll_back_valid_candidate(self):
        calls=[]
        def public_get(url):
            self.assertTrue(url.startswith("https://api.github.com/repos/python/cpython/"))
            calls.append(url)
            if "pulls?state=closed" in url:
                return [
                    {"number":101,"title":"Fix inert exception case","merged_at":"2026-10-01T00:00:00Z"},
                    {"number":102,"title":"Fix inert test issue","merged_at":"2026-10-01T00:00:00Z"},
                ]
            if "/pulls/101/files?" in url:
                return [{"filename":"Lib/test_inert.py","patch":"X"*50001}]
            if "/pulls/102/files?" in url:
                return [{"filename":"Lib/test_inert.py","patch":"+raise RuntimeError('inert')\n"}]
            self.fail("unexpected synthetic GET")
        result=mine_once(self.root,fetch=public_get,sources=(SOURCE,),
                         max_new_per_source=2,crosscheck_origin=False)
        self.assertEqual(result["status"],"COLLECTED_UNVERIFIED_PARTIAL_NO_GO")
        self.assertEqual(result["new_candidates"],1)
        self.assertEqual(result["rejected_public_pr_count"],1)
        self.assertEqual(result["rejected_public_source"],SOURCE)
        self.assertFalse(result["production_approved"])
        self.assertEqual(len(calls),3)
        with sqlite3.connect(self.root/"runtime"/"public_miner.sqlite3") as db:
            actual=db.execute("SELECT pr_number,status FROM candidates").fetchall()
        self.assertEqual(actual,[(102,"UNVERIFIED_CANDIDATE_ONLY")])

    def test_worker_keeps_partial_no_go_and_bounded_receipt(self):
        def collect(root):
            return {"status":"COLLECTED_UNVERIFIED_PARTIAL_NO_GO",
                    "new_candidates":1,"sources_checked":1,
                    "rejected_public_pr_count":1,
                    "rejected_public_source":SOURCE,
                    "rejected_public_reason_code":"PUBLIC_PATCH_METADATA_REJECTED",
                    "verification_pass":0,"production_approved":False}
        def report(root):
            p=root/"runtime"/"reports"/"inert.md"
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text("UNVERIFIED ONLY",encoding="utf-8")
            return p
        out=run_cycle(self.root,collect=collect,write_report=report)
        self.assertEqual(out["status"],"COLLECTED_UNVERIFIED_PARTIAL_NO_GO")
        self.assertEqual(out["collector_rejected_count"],1)
        self.assertEqual(out["collector_rejected_source"],SOURCE)
        self.assertFalse(out["production_approved"])
        self.assertEqual(json.loads((self.root/"runtime"/"last_run.json").read_text())["status"],
                         out["status"])

    def test_forged_partial_receipt_is_denied(self):
        def collect(root):
            return {"status":"COLLECTED_UNVERIFIED_PARTIAL_NO_GO",
                    "new_candidates":0,"sources_checked":1,
                    "rejected_public_pr_count":True,
                    "rejected_public_source":SOURCE,
                    "rejected_public_reason_code":"PUBLIC_PATCH_METADATA_REJECTED",
                    "verification_pass":0,"production_approved":False}
        out=run_cycle(self.root,collect=collect,
                      write_report=lambda _:self.fail("should not report"))
        self.assertEqual(out["status"],"COLLECTION_FAILED")
        self.assertFalse(out["production_approved"])

if __name__=="__main__":
    unittest.main()
