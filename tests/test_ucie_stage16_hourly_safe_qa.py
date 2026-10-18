"""Offline-only Stage16 hourly safe QA integration and refusal tests."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from ucie_miner.public_safe_qa_cycle import (
    OPT_IN, OPT_IN_SCHEMA, STATE, ALREADY, COOLDOWN, DISABLED,
    FAILED, PAUSED, PENDING, REVIEW, optional_pinned_public_qa,
)
from ucie_miner.public_hourly_staging import optional_public_skill_staging


RUN_A = 39115340824
RUN_B = 39114824649
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)


def fake_verdict(*, status="SAFE_TEMPLATE_QA_REVIEW_READY_NO_NEW_APPROVAL",
                 templates=2, approved=0):
    return {
        "schema": "UCIE_PUBLIC_SAFE_CANDIDATE_QA_V1",
        "status": status, "safe_templates_observed": templates,
        "new_rules_approved": approved, "auto_promoted": False,
        "owner_signed": False, "production_approved": False,
        "unsafe_external_code_executed": False, "persistent_writes": 0,
    }


class Stage16HourlySafeQATests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "UCIE"
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(parents=True)

    def opt_in(self, run_id=RUN_A):
        (self.runtime / OPT_IN).write_text(json.dumps({
            "schema": OPT_IN_SCHEMA, "run_id": run_id,
        }), encoding="utf-8")

    def test_missing_marker_never_reads_public_ci_or_writes_state(self):
        verifier = Mock(side_effect=AssertionError("unexpected QA request"))
        result = optional_pinned_public_qa(self.root, verifier=verifier, now=NOW)
        self.assertEqual(result["status"], DISABLED)
        self.assertEqual(result["public_gets_upper_bound"], 0)
        verifier.assert_not_called()
        self.assertFalse((self.runtime / STATE).exists())

    def test_first_pinned_verification_then_no_repeat_public_gets(self):
        self.opt_in()
        verifier = Mock(return_value=fake_verdict())
        first = optional_pinned_public_qa(self.root, verifier=verifier, now=NOW)
        self.assertEqual(first["status"], REVIEW)
        self.assertEqual(first["safe_templates_observed"], 2)
        self.assertEqual(first["public_gets_upper_bound"], 9)
        self.assertEqual(first["approved_rules_added"], 0)
        self.assertFalse(first["production_approved"])
        same = optional_pinned_public_qa(
            self.root, verifier=verifier, now=NOW + timedelta(days=10))
        self.assertEqual(same["status"], ALREADY)
        self.assertEqual(same["public_gets_upper_bound"], 0)
        verifier.assert_called_once_with(self.root, run_id=RUN_A)

    def test_changed_run_respects_cooldown_before_new_live_attempt(self):
        self.opt_in()
        verifier = Mock(return_value=fake_verdict())
        optional_pinned_public_qa(self.root, verifier=verifier, now=NOW)
        self.opt_in(RUN_B)
        paused = optional_pinned_public_qa(
            self.root, verifier=verifier, now=NOW + timedelta(hours=23))
        self.assertEqual(paused["status"], COOLDOWN)
        self.assertEqual(verifier.call_count, 1)
        allowed = optional_pinned_public_qa(
            self.root, verifier=verifier, now=NOW + timedelta(hours=24))
        self.assertEqual(allowed["status"], REVIEW)
        self.assertEqual(verifier.call_count, 2)
        self.assertEqual(json.loads((self.runtime / STATE).read_text())["run_id"],
                         RUN_B)

    def test_quota_pause_never_claims_attempt(self):
        self.opt_in()
        verifier = Mock(side_effect=AssertionError("rate pause bypassed"))
        blocked = optional_pinned_public_qa(
            self.root, verifier=verifier, rate_paused=True, now=NOW)
        self.assertEqual(blocked["status"], PAUSED)
        self.assertFalse((self.runtime / STATE).exists())
        verifier.assert_not_called()

    def test_failed_network_spends_attempt_without_leaking_exception(self):
        self.opt_in()
        verifier = Mock(side_effect=ValueError("PRIVATE_TOKEN_NEVER_PRINT"))
        bad = optional_pinned_public_qa(self.root, verifier=verifier, now=NOW)
        self.assertEqual(bad["status"], FAILED)
        self.assertEqual(bad["error_type"], "ValueError")
        self.assertNotIn("PRIVATE_TOKEN_NEVER_PRINT", json.dumps(bad))
        self.assertTrue((self.runtime / STATE).exists())
        no_retry = optional_pinned_public_qa(
            self.root, verifier=verifier, now=NOW + timedelta(minutes=60))
        self.assertEqual(no_retry["status"], ALREADY)
        self.assertEqual(verifier.call_count, 1)

    def test_incomplete_ledger_keeps_no_go_and_no_approval(self):
        self.opt_in()
        out = optional_pinned_public_qa(
            self.root, now=NOW,
            verifier=lambda root, *, run_id: fake_verdict(
                status="CANDIDATE_LEDGER_INCOMPLETE_NO_GO", templates=0))
        self.assertEqual(out["status"], PENDING)
        self.assertEqual(out["approved_rules_added"], 0)

    def test_forged_approval_and_bad_marker_fail_closed(self):
        self.opt_in()
        out = optional_pinned_public_qa(
            self.root, now=NOW,
            verifier=lambda root, *, run_id: fake_verdict(approved=1))
        self.assertEqual(out["status"], FAILED)
        self.assertEqual(out["approved_rules_added"], 0)
        self.opt_in(True)  # bool is not a valid run ID
        with self.assertRaises(ValueError):
            optional_pinned_public_qa(self.root, now=NOW)
        (self.runtime / OPT_IN).write_text(
            '{"schema":"UCIE_STAGE16_SAFE_QA_OPT_IN_V1","run_id":39115340824,"run_id":1}',
            encoding="utf-8")
        with self.assertRaises(ValueError):
            optional_pinned_public_qa(self.root, now=NOW)

    def test_tampered_state_or_future_clock_fails_closed(self):
        self.opt_in()
        (self.runtime / STATE).write_text(
            '{"schema":"UCIE_STAGE16_SAFE_QA_ATTEMPT_V1","run_id":39115340824,"attempted_utc":"2100-01-01T00:00:00+00:00"}',
            encoding="utf-8")
        with self.assertRaises(ValueError):
            optional_pinned_public_qa(self.root, now=NOW)

    def test_stage10_hourly_collects_stage16_without_a_new_scheduler(self):
        self.opt_in()
        (self.runtime / "stage10_hourly_opt_in.txt").write_text(
            "UCIE_STAGE10_HOURLY_OPT_IN_V1", encoding="utf-8")
        batch = {"sources_fetched": [
            "python/cpython", "PowerShell/PowerShell", "git/git",
            "modelcontextprotocol/python-sdk", "actions/runner-images",
        ], "overall_gets_upper_bound": 8, "enriched_count": 1,
            "production_approved": False}
        staged = {
            "status": "UNVERIFIED_CANDIDATES_STAGED_NO_GO",
            "mode": "OPT_IN_SEPARATE_DISK",
            "approved_rules_added": 0, "production_approved": False,
            "new_identities": 0, "evidence_revisions": 0,
            "git_commit_new_identities": 0, "git_commit_evidence_revisions": 0,
        }
        history = {"status": "EXTERNAL_HISTORY_BACKFILL_OK_NO_GO"}
        official = {"status": "STAGE14_OFFICIAL_OBSERVED_NO_GO"}
        fix = {"status": "STAGE15_FIX_EVIDENCE_DISABLED"}
        review = {"status": "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO",
                  "new_review_proposals": 0}
        ready = {
            "status": REVIEW, "safe_templates_observed": 1,
            "public_gets_upper_bound": 9, "approved_rules_added": 0,
            "production_approved": False,
        }
        with (
            patch("ucie_miner.public_external_history.optional_external_history_backfill",
                  return_value=history),
            patch("ucie_miner.public_official_evidence.optional_official_evidence_cycle",
                  return_value=official),
            patch("ucie_miner.public_fix_evidence.optional_fix_evidence_enrichment",
                  return_value=fix),
            patch("ucie_miner.public_candidate_learning.optional_hourly_review_learning",
                  return_value=review),
            patch("ucie_miner.public_safe_qa_cycle.optional_pinned_public_qa",
                  return_value=ready) as call,
        ):
            result = optional_public_skill_staging(
                self.root, batch_builder=lambda **kw: batch,
                stage_candidate_batch=lambda *a, **kw: staged)
        call.assert_called_once_with(self.root, rate_paused=False)
        self.assertEqual(result["stage16_safe_qa_status"], REVIEW)
        self.assertEqual(result["stage16_safe_qa_templates"], 1)
        self.assertFalse(result["scheduled_task_changed"])
        self.assertEqual(result["approved_rules_added"], 0)
        self.assertFalse(result["production_approved"])


if __name__ == "__main__":
    unittest.main()
