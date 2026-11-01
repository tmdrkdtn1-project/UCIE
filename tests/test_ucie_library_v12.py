"""UCIE V1.2 operating proof + explicitly opted-in hourly quality regressions.

All tests use isolated synthetic UCIE-only roots and dummy public ledgers.
No real GitHub fetch, private project, task registration, worker external
source, Rulepack approval or arbitrary script execution occurs.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import json
import tempfile
import unittest

from test_ucie_library_v02 import fixture
from ucie_miner.library_audit_v07 import audit_handoff_receipts
from ucie_miner.library_quality_loop_v12 import (
    SCHEMA as QUALITY_SCHEMA, DISABLED, OBSERVED, REVIEW,
    OPT_IN_FILENAME, OPT_IN_TOKEN, QualityError,
    optional_hourly_library_quality, read_quality_snapshot,
)
from ucie_miner.library_hourly_proof_v12 import (
    SCHEMA as PROOF_SCHEMA, HourlyProofError,
    inspect_hourly_public_library,
)
from ucie_miner.worker import run_cycle

NOW = datetime(2026, 11, 1, 9, 0, 0, tzinfo=timezone.utc)


def parsed(fixture_root):
    return audit_handoff_receipts(fixture(), [])


def receipts_for(started: datetime, *, new_candidates: int = 1,
                 status: str = "COLLECTED_UNVERIFIED",
                 stage12: str = "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO",
                 stage17: str = "STAGE17_QUALITY_OBSERVED_UNVERIFIED_NO_GO",
                 approved=False):
    st = started.isoformat(timespec="seconds")
    end = (started + timedelta(seconds=12)).isoformat(timespec="seconds")
    return {
        "schema": "UCIE_MINER_CYCLE_V1",
        "status": status, "started_utc": st, "finished_utc": end,
        "new_candidates": new_candidates, "sources_checked": 2,
        "verification_pass": 0, "production_approved": approved,
        "consecutive_failures": 0,
        "stage10_status": "STAGE10_UNVERIFIED_STAGED_NO_GO",
        "stage12_review_status": stage12,
        "stage13_history_status": "EXTERNAL_HISTORY_BACKFILL_OK_NO_GO",
        "stage15_fix_evidence_status": "STAGE15_STRUCTURED_FIX_EVIDENCE_STAGED_NO_GO",
        "stage16_safe_qa_status": "STAGE16_SAFE_QA_OBSERVED_REVIEW_REQUIRED",
        "stage17_quality_status": stage17,
        "stage17_quality_candidate_count": 590,
        "stage17_quality_candidate_delta": 2,
    }


def store_hourly(root, previous, current):
    runtime = root / "runtime"
    runtime.mkdir(exist_ok=True)
    lines = [json.dumps(x, sort_keys=True) for x in (previous, current)]
    (runtime / "run_history.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (runtime / "last_run.json").write_text(lines[-1] + "\n", encoding="utf-8")


class HourlyQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ucie-v12-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "UCIE"
        self.root.mkdir()
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        # Windows owner path restriction must never be relaxed in production:
        # override only in the synthetic fixture with an exact bounded path.
        self.patch_root = patch(
            "ucie_miner.library_quality_loop_v12._root",
            side_effect=self._exact_root)
        self.patch_root.start()
        self.addCleanup(self.patch_root.stop)

    def _exact_root(self, value):
        path = Path(value)
        if path != self.root or not path.is_dir() or path.is_symlink():
            raise QualityError("synthetic UCIE fixture path must be exact")
        return path

    def test_hourly_receipts_are_not_scheduler_event_proof(self):
        before = receipts_for(NOW - timedelta(minutes=70))
        recent = receipts_for(NOW - timedelta(minutes=10))
        store_hourly(self.root, before, recent)
        report = inspect_hourly_public_library(self.root, now=NOW)
        self.assertEqual(report["schema"], PROOF_SCHEMA)
        self.assertEqual(report["status"],
                         "TWO_FRESH_CYCLE_RECEIPTS_OBSERVED_SCHEDULER_NOT_ATTESTED")
        self.assertTrue(report["two_successful_collection_receipts"])
        self.assertEqual(report["started_cadence_minutes"], 60.0)
        self.assertEqual(report["stage_statuses"][
            "stage12_unverified_review_learning"],
            "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO")
        self.assertFalse(report["task_scheduler_event_proof_checked"])
        self.assertFalse(report["model_weights_trained"])
        self.assertFalse(report["code_self_modified"])
        self.assertEqual(report["automatically_approved_rules"], 0)
        self.assertEqual(report["operator_marker_presence"]["stage17"], "NOT_ENABLED")
        self.assertEqual(report["operating_db_writes"], 0)

    def test_no_go_on_stale_or_failed_hourly_receipts(self):
        before = receipts_for(NOW - timedelta(hours=6))
        last = receipts_for(NOW - timedelta(hours=5))
        store_hourly(self.root, before, last)
        result = inspect_hourly_public_library(self.root, now=NOW)
        self.assertEqual(result["status"], "HOURLY_CYCLE_ACTIVITY_NOT_PROVEN_NO_GO")
        self.assertGreater(result["last_completed_age_minutes"], 90)
        last = receipts_for(NOW - timedelta(minutes=10),
                            status="COLLECTION_FAILED")
        store_hourly(self.root, receipts_for(NOW - timedelta(minutes=70)), last)
        result = inspect_hourly_public_library(self.root, now=NOW)
        self.assertEqual(result["status"], "HOURLY_CYCLE_ACTIVITY_NOT_PROVEN_NO_GO")
        self.assertFalse(result["two_successful_collection_receipts"])
        store_hourly(self.root,
                     receipts_for(NOW - timedelta(minutes=40)),
                     receipts_for(NOW - timedelta(minutes=10)))
        self.assertEqual(inspect_hourly_public_library(
            self.root, now=NOW)["status"], "HOURLY_CYCLE_ACTIVITY_NOT_PROVEN_NO_GO")

    def test_tampered_duplicate_or_bogus_run_history_fails_closed(self):
        a=receipts_for(NOW-timedelta(minutes=70))
        b=receipts_for(NOW-timedelta(minutes=10))
        store_hourly(self.root,a,b)
        (self.runtime/"last_run.json").write_text(
            json.dumps(dict(b, production_approved=True))+"\n",encoding="utf-8")
        with self.assertRaises(HourlyProofError):
            inspect_hourly_public_library(self.root, now=NOW)
        store_hourly(self.root,a,b)
        (self.runtime/"last_run.json").write_text(
            json.dumps(dict(b, new_candidates=9))+"\n",encoding="utf-8")
        with self.assertRaises(HourlyProofError):
            inspect_hourly_public_library(self.root, now=NOW)
        store_hourly(self.root,a,b)
        (self.runtime/"last_run.json").write_text(
            json.dumps(dict(b, stage17_quality_status="APPROVED"))+"\n",
            encoding="utf-8")
        with self.assertRaises(HourlyProofError):
            inspect_hourly_public_library(self.root, now=NOW)
        store_hourly(self.root,a,b)
        (self.runtime/"run_history.jsonl").write_text(
            json.dumps(a)+"\n"+json.dumps(b),
            encoding="utf-8")
        with self.assertRaises(HourlyProofError):
            inspect_hourly_public_library(self.root, now=NOW)

    def test_quality_requires_separate_optin_and_no_side_effects_when_absent(self):
        result = optional_hourly_library_quality(
            self.root, stage12_status="STAGE12_REVIEW_DISABLED",
            stage16_status="STAGE16_SAFE_QA_DISABLED",
            auditor=lambda r: self.fail("auditor called without owner marker"))
        self.assertEqual(result["status"], DISABLED)
        self.assertFalse((self.runtime/"quality_v12").exists())
        self.assertFalse(result["quality_snapshot_written"])
        marker = self.runtime / OPT_IN_FILENAME
        marker.write_text("unknown opt in", encoding="utf-8")
        with self.assertRaises(QualityError):
            optional_hourly_library_quality(
                self.root, stage12_status="STAGE12_REVIEW_DISABLED",
                stage16_status="STAGE16_SAFE_QA_DISABLED",
                auditor=parsed)
        self.assertFalse((self.runtime/"quality_v12").exists())

    def test_quality_first_hour_and_followup_delta_and_integrity(self):
        (self.runtime/OPT_IN_FILENAME).write_text(OPT_IN_TOKEN,encoding="utf-8")
        state = audit_handoff_receipts(fixture(),[])
        first = optional_hourly_library_quality(
            self.root, stage12_status="STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO",
            stage16_status="STAGE16_SAFE_QA_DISABLED",
            auditor=lambda root:state, clock=NOW)
        self.assertEqual(first["status"], OBSERVED)
        self.assertEqual(first["public_unverified_candidates"], 26)
        self.assertEqual(first["candidate_delta"], 0)
        self.assertFalse(first["production_approved"])
        snapshot = read_quality_snapshot(self.root)
        self.assertEqual(snapshot["schema"], QUALITY_SCHEMA)
        self.assertEqual(snapshot["source_candidate_count"],26)
        self.assertEqual(snapshot["approved_rule_count"],0)
        self.assertEqual(snapshot["database_changes"],0)
        self.assertFalse(snapshot["auto_promoted"])
        self.assertRegex(snapshot["snapshot_sha256"],"^[0-9a-f]{64}$")
        second = optional_hourly_library_quality(
            self.root, stage12_status="STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO",
            stage16_status="STAGE16_SAFE_QA_DISABLED",
            auditor=lambda root:state,
            clock=NOW+timedelta(hours=1))
        self.assertEqual(second["candidate_delta"],0)
        after = read_quality_snapshot(self.root)
        self.assertEqual(after["previous_quality_sha256"],
                         snapshot["snapshot_sha256"])
        self.assertEqual(after["source_candidate_count"],26)

    def test_quality_regression_or_conflict_has_no_go_status(self):
        (self.runtime/OPT_IN_FILENAME).write_text(OPT_IN_TOKEN, encoding="utf-8")
        current = audit_handoff_receipts(fixture(),[])
        initial = optional_hourly_library_quality(
            self.root, stage12_status="STAGE12_REVIEW_DISABLED",
            stage16_status="STAGE16_SAFE_QA_DISABLED",
            auditor=lambda root:current, clock=NOW)
        self.assertEqual(initial["status"], OBSERVED)
        lowered = dict(current, source_linked_candidates=20,
                       candidates=current["candidates"][:20])
        result = optional_hourly_library_quality(
            self.root, stage12_status="STAGE12_REVIEW_DISABLED",
            stage16_status="STAGE16_SAFE_QA_DISABLED",
            auditor=lambda root:lowered, clock=NOW+timedelta(hours=1))
        self.assertEqual(result["status"], REVIEW)
        self.assertEqual(result["candidate_delta"],-6)
        conflict = dict(current, conflicting_claim_groups=1,
                        status="RECEIPT_SOURCE_BINDING_CONFLICT_NO_GO")
        next_result = optional_hourly_library_quality(
            self.root, stage12_status="STAGE12_REVIEW_DISABLED",
            stage16_status="STAGE16_SAFE_QA_DISABLED",
            auditor=lambda root:conflict, clock=NOW+timedelta(hours=2))
        self.assertEqual(next_result["status"], REVIEW)
        self.assertEqual(next_result["approved_rules_added"],0)

    def test_corrupted_quality_snapshot_never_overwritten(self):
        (self.runtime/OPT_IN_FILENAME).write_text(OPT_IN_TOKEN, encoding="utf-8")
        current = audit_handoff_receipts(fixture(),[])
        optional_hourly_library_quality(
            self.root, stage12_status="STAGE12_REVIEW_DISABLED",
            stage16_status="STAGE16_SAFE_QA_DISABLED",
            auditor=lambda root:current, clock=NOW)
        output = self.runtime/"quality_v12"/"latest.json"
        tampered=json.loads(output.read_text(encoding="ascii"))
        tampered["approved_rule_count"]=1
        output.write_text(json.dumps(tampered),encoding="ascii")
        with self.assertRaises(QualityError):
            optional_hourly_library_quality(
                self.root, stage12_status="STAGE12_REVIEW_DISABLED",
                stage16_status="STAGE16_SAFE_QA_DISABLED",
                auditor=lambda root:current, clock=NOW+timedelta(hours=1))
        self.assertEqual(json.loads(output.read_text())["approved_rule_count"],1)

    def test_actual_existing_hourly_stage_calls_quality_after_review_and_qa(self):
        # Synthetic original collector stages: assert Stage17 is chained to
        # Stage10 under the same original caller, not a new task or service.
        from ucie_miner.public_hourly_staging import (
            optional_public_skill_staging, OPT_IN_FILENAME, OPT_IN_TOKEN,
        )
        from ucie_miner.public_discovery import SOURCES
        call_order = []
        def capture(phase, result):
            def inner(*args, **kwargs):
                call_order.append(phase)
                return result
            return inner
        batch = {
            "sources_fetched": list(SOURCES), "overall_gets_upper_bound": 0,
            "enriched_count": 0, "production_approved": False,
        }
        staged = {
            "status": "UNVERIFIED_CANDIDATES_STAGED_NO_GO",
            "mode": "OPT_IN_SEPARATE_DISK", "approved_rules_added": 0,
            "production_approved": False, "new_identities": 0,
            "evidence_revisions": 0, "git_commit_new_identities": 0,
            "git_commit_evidence_revisions": 0,
        }
        history = {"status": "STAGE13_EXTERNAL_HISTORY_DISABLED"}
        official = {"status": "STAGE14_OFFICIAL_DISABLED"}
        fix = {"status": "STAGE15_FIX_EVIDENCE_DISABLED"}
        learning = {"status": "STAGE12_REVIEW_DISABLED"}
        qa = {"status": "STAGE16_SAFE_QA_DISABLED",
              "public_gets_upper_bound": 0,
              "approved_rules_added": 0, "production_approved": False}
        quality = {"status": OBSERVED, "public_unverified_candidates": 26,
                   "candidate_delta": 2, "approved_rules_added": 0,
                   "production_approved": False}
        with patch(
            "ucie_miner.library_quality_loop_v12.optional_hourly_library_quality",
            side_effect=capture("quality", quality)
        ) as quality_call:
            disabled = optional_public_skill_staging(
                self.root, batch_builder=capture("batch", batch),
                stage_candidate_batch=capture("stage", staged))
            self.assertEqual(disabled["status"], "STAGE10_HOURLY_DISABLED")
            quality_call.assert_not_called()
        (self.runtime/OPT_IN_FILENAME).write_text(OPT_IN_TOKEN, encoding="utf-8")
        with (
            patch("ucie_miner.public_external_history.optional_external_history_backfill",
                  side_effect=capture("history", history)),
            patch("ucie_miner.public_official_evidence.optional_official_evidence_cycle",
                  side_effect=capture("official", official)),
            patch("ucie_miner.public_fix_evidence.optional_fix_evidence_enrichment",
                  side_effect=capture("fix", fix)),
            patch("ucie_miner.public_candidate_learning.optional_hourly_review_learning",
                  side_effect=capture("learning", learning)),
            patch("ucie_miner.public_safe_qa_cycle.optional_pinned_public_qa",
                  side_effect=capture("qa", qa)),
            patch("ucie_miner.library_quality_loop_v12.optional_hourly_library_quality",
                  side_effect=capture("quality", quality)) as quality_call
        ):
            result = optional_public_skill_staging(
                self.root, batch_builder=capture("batch", batch),
                stage_candidate_batch=capture("stage", staged))
            self.assertEqual(result["status"], "STAGE10_UNVERIFIED_STAGED_NO_GO")
            self.assertEqual(result["stage17_quality_status"], OBSERVED)
            self.assertEqual(result["stage17_quality_candidate_count"], 26)
            self.assertEqual(result["stage17_quality_candidate_delta"], 2)
            self.assertEqual(result["approved_rules_added"], 0)
            self.assertEqual(call_order, [
                "batch", "stage", "history", "official", "fix",
                "learning", "qa", "quality",
            ])
            quality_call.assert_called_once()
            self.assertEqual(quality_call.call_args.kwargs["stage12_status"],
                             "STAGE12_REVIEW_DISABLED")
            self.assertEqual(quality_call.call_args.kwargs["stage16_status"],
                             "STAGE16_SAFE_QA_DISABLED")

    def test_worker_receipt_writes_only_vetted_quality_fields(self):
        # Test worker validates Stage17 status/counters independently.
        def report(root):
            path=root/"runtime"/"reports"/"synthetic.md"
            path.parent.mkdir(exist_ok=True)
            path.write_text("UCIE synthetic test only",encoding="utf-8")
            return path
        def collected(root):
            return {
                "status":"COLLECTED_UNVERIFIED","new_candidates":2,
                "sources_checked":2,"verification_pass":0,
                "production_approved":False,
                "stage10":{
                    "status":"STAGE10_UNVERIFIED_STAGED_NO_GO",
                    "stage17_quality_status":"STAGE17_QUALITY_OBSERVED_UNVERIFIED_NO_GO",
                    "stage17_quality_candidate_count":590,
                    "stage17_quality_candidate_delta":2,
                },
            }
        result=run_cycle(self.root,collect=collected,write_report=report)
        self.assertEqual(result["status"],"COLLECTED_UNVERIFIED")
        self.assertEqual(result["stage17_quality_status"],
                         "STAGE17_QUALITY_OBSERVED_UNVERIFIED_NO_GO")
        self.assertEqual(result["stage17_quality_candidate_count"],590)
        self.assertEqual(result["stage17_quality_candidate_delta"],2)
        self.assertEqual(result["production_approved"],False)
        def forged(root):
            data=collected(root)
            data["stage10"]["stage17_quality_status"]="APPROVED"
            return data
        failed=run_cycle(self.root,collect=forged,write_report=report)
        self.assertEqual(failed["status"],"COLLECTION_FAILED")
        self.assertNotIn("stage17_quality_status",failed)


if __name__=="__main__":
    unittest.main()
