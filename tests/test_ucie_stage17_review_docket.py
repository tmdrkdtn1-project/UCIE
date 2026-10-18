"""Stage17 read-only evidence handoff tests (synthetic UCIE runtime only)."""
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout

from ucie_miner.stage17_review_docket import (
    attest_stage16_aggregate, build_review_docket, inspect_stage17_review,
    SCHEMA,
)
from ucie_miner.__main__ import main as miner_main
from ucie_miner.public_safe_qa_cycle import STATE, STATE_SCHEMA
from test_ucie_automated_candidate_qa import handoff, RUN_ID

CLOCK = datetime(2026, 10, 18, 14, 0, 0, tzinfo=timezone.utc)
START = CLOCK - timedelta(minutes=1)
ATTEMPT = START + timedelta(seconds=3)
END = START + timedelta(seconds=13)


def evidence():
    return {
        "status": "STAGE16_AGGREGATE_CI_OBSERVED_NOT_INDEPENDENT_QA",
        "ci_run_id": RUN_ID, "observed_utc": START.isoformat(),
        "synthetic_templates_observed": 4,
        "candidate_snapshot_at_ci_verified": False,
    }


def example_receipt():
    return {
        "schema": "UCIE_MINER_CYCLE_V1",
        "status": "COLLECTED_UNVERIFIED",
        "started_utc": START.isoformat(),
        "finished_utc": END.isoformat(),
        "stage10_status": "STAGE10_UNVERIFIED_STAGED_NO_GO",
        "stage12_review_status": "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO",
        "stage16_safe_qa_status": "STAGE16_SAFE_QA_OBSERVED_REVIEW_REQUIRED",
        "stage16_safe_qa_templates": 4,
        "stage16_safe_qa_gets_upper_bound": 9,
        "verification_pass": 0,
        "production_approved": False,
    }


class Stage17PureReviewTests(unittest.TestCase):
    def test_pinned_four_candidates_are_review_tasks_never_qa_pass(self):
        result = build_review_docket(handoff(), evidence())
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["status"],
                         "CANDIDATES_READY_FOR_INDEPENDENT_REVIEW_NO_APPROVAL")
        self.assertEqual(result["candidate_count"], 4)
        self.assertEqual(result["stage16_ci_run_id"], RUN_ID)
        self.assertEqual(result["triage_counts"], {
            "PINNED_TEMPLATE_INDEPENDENT_REVIEW_REQUIRED": 4})
        self.assertFalse(result["stage16_candidate_snapshot_at_ci_verified"])
        self.assertEqual(result["independent_qa_pass_count"], 0)
        self.assertEqual(result["independent_security_pass_count"], 0)
        self.assertEqual(result["approved_rules_added"], 0)
        self.assertFalse(result["auto_promoted"])
        self.assertFalse(result["production_approved"])
        self.assertFalse(result["docket_digest_is_signature"])
        self.assertEqual(result["new_public_gets"], 0)
        self.assertEqual(result["persistent_writes"], 0)
        for row in result["items"]:
            self.assertIn(row["rule_id"],
                          {"PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO",
                           "PS_RESOLVE_PATH_DOT_PREFIX",
                           "PS_FUZZY_GET_COMMAND_DUPLICATES",
                           "PY_SCANDIR_SHARED_ITERATOR_RACE"})
            self.assertEqual(row["independent_qa"], "NOT_PERFORMED")
            self.assertEqual(row["candidate_level_ci_binding"], "NOT_ATTESTED")
            self.assertFalse(row["deploy_allowed"])
            self.assertFalse(row["human_approval"])
            self.assertTrue(row["pinned_public_pr"].startswith("https://github.com/"))
            self.assertNotIn("executable_command", row)

    def test_unknown_candidate_is_never_considered_pinned(self):
        q = handoff()
        q["tasks"].append({
            "candidate_id_sha256": "f" * 64,
            "evidence_sha256": "e" * 64,
            "status": "UNVERIFIED_CANDIDATE_ONLY",
            "approval": False, "source": "git/git",
            "reference": "git-commit:unknown",
            "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
            "stage6_candidate": None,
        })
        q["source_revisions"] += 1
        q["linked_revisions"] += 1
        result = build_review_docket(q, evidence())
        self.assertEqual(result["candidate_count"], 5)
        self.assertEqual(result["triage_counts"].get(
            "UNSUPPORTED_SAFE_RECIPE_NO_GO"), 1)
        item = next(row for row in result["items"] if row["rule_id"] is None)
        self.assertIsNone(item["pinned_public_pr"])
        self.assertIsNone(item["safe_synthetic_test_step"])

    def test_ambiguous_revision_blocks_safe_template_even_with_ci(self):
        q = handoff()
        from copy import deepcopy
        duplicate = deepcopy(q["tasks"][0])
        duplicate["candidate_id_sha256"] = "e" * 64
        duplicate["evidence_sha256"] = "d" * 64
        q["tasks"].append(duplicate)
        q["linked_revisions"] += 1
        q["source_revisions"] += 1
        result = build_review_docket(q, evidence())
        self.assertEqual(result["triage_counts"].get(
            "AMBIGUOUS_SOURCE_REVISION_NO_GO"), 2)
        self.assertEqual(result["approved_rules_added"], 0)

    def test_missing_stage16_and_incomplete_ledger_remain_no_go(self):
        missing = {
            "status": "STAGE16_ATTEMPT_ABSENT_NO_GO",
            "ci_run_id": None, "observed_utc": None,
            "synthetic_templates_observed": 0,
            "candidate_snapshot_at_ci_verified": False,
        }
        result = build_review_docket(handoff(), missing)
        self.assertEqual(result["status"], "EVIDENCE_INCOMPLETE_NO_GO")
        self.assertEqual(result["triage_counts"], {
            "STAGE16_AGGREGATE_EVIDENCE_MISSING_NO_GO": 4})
        queue = handoff()
        queue["status"] = "SOURCE_REVISIONS_PENDING_NO_GO"
        queue["pending_source_revisions"] = 1
        queue["source_revisions"] += 1
        result = build_review_docket(queue, evidence())
        self.assertEqual(result["status"], "EVIDENCE_INCOMPLETE_NO_GO")
        self.assertEqual(result["triage_counts"], {
            "INCOMPLETE_REVIEW_LEDGER_NO_GO": 4})

    def test_forged_source_approval_or_aggregate_is_rejected(self):
        q = handoff()
        q["tasks"][0]["approval"] = True
        with self.assertRaises(ValueError):
            build_review_docket(q, evidence())
        for change in (
            {"candidate_snapshot_at_ci_verified": True},
            {"synthetic_templates_observed": 10},
            {"ci_run_id": "untrusted"},
        ):
            obj = evidence()
            obj.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                build_review_docket(handoff(), obj)

    def test_repeat_docket_deterministic_and_non_signed(self):
        first = build_review_docket(handoff(), evidence())
        second = build_review_docket(handoff(), evidence())
        self.assertEqual(first["docket_sha256"], second["docket_sha256"])
        self.assertFalse(first["rulepack_signed"])


class Stage17RuntimeLinkTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "UCIE"
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(parents=True)

    def write_state(self, attempted=ATTEMPT):
        (self.runtime / STATE).write_text(json.dumps({
            "schema": STATE_SCHEMA,
            "run_id": RUN_ID,
            "attempted_utc": attempted.isoformat(),
        }), encoding="utf-8")

    def append(self, receipt):
        with (self.runtime / "run_history.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt) + "\n")

    def test_exact_attempt_to_success_receipt_links_after_cached_hours(self):
        self.write_state()
        self.append(example_receipt())
        cached = example_receipt()
        cached["started_utc"] = (START + timedelta(hours=1)).isoformat()
        cached["finished_utc"] = (END + timedelta(hours=1)).isoformat()
        cached["stage16_safe_qa_status"] = (
            "STAGE16_SAFE_QA_ALREADY_ATTEMPTED_NO_GO")
        cached["stage16_safe_qa_gets_upper_bound"] = 0
        self.append(cached)
        out = attest_stage16_aggregate(self.root, now=CLOCK)
        self.assertEqual(out["status"],
                         "STAGE16_AGGREGATE_CI_OBSERVED_NOT_INDEPENDENT_QA")
        self.assertEqual(out["ci_run_id"], RUN_ID)
        self.assertEqual(out["synthetic_templates_observed"], 4)

    def test_observed_stage17_cli_inspection_no_files_modified_no_network(self):
        self.write_state()
        self.append(example_receipt())
        before = {
            p.name: p.read_bytes() for p in self.runtime.iterdir() if p.is_file()
        }
        with patch("ucie_miner.stage17_review_docket.prepare_verification_handoff",
                   return_value=handoff()), patch(
                       "ucie_miner.automated_candidate_qa._public_json",
                       side_effect=AssertionError("No API reads allowed")):
            result = inspect_stage17_review(self.root, now=CLOCK)
        after = {
            p.name: p.read_bytes() for p in self.runtime.iterdir() if p.is_file()
        }
        self.assertEqual(before, after)
        self.assertEqual(result["status"],
                         "CANDIDATES_READY_FOR_INDEPENDENT_REVIEW_NO_APPROVAL")
        self.assertEqual(result["new_public_gets"], 0)

    def test_missing_state_time_mismatch_and_stale_fail_closed(self):
        self.assertEqual(attest_stage16_aggregate(
            self.root, now=CLOCK)["status"], "STAGE16_ATTEMPT_ABSENT_NO_GO")
        self.write_state(ATTEMPT + timedelta(hours=1))
        self.append(example_receipt())
        self.assertEqual(attest_stage16_aggregate(
            self.root, now=CLOCK + timedelta(hours=2))["status"],
            "STAGE16_MATCHING_RECEIPT_ABSENT_NO_GO")
        self.write_state()
        self.assertEqual(attest_stage16_aggregate(
            self.root, now=CLOCK + timedelta(days=8))["status"],
            "STAGE16_ATTESTATION_STALE_NO_GO")

    def test_bad_stage16_receipt_claim_rejected(self):
        self.write_state()
        altered = example_receipt()
        altered["stage16_safe_qa_gets_upper_bound"] = 100
        self.append(altered)
        with self.assertRaises(ValueError):
            attest_stage16_aggregate(self.root, now=CLOCK)

    def test_duplicate_json_and_oversized_lines_are_rejected(self):
        self.write_state()
        (self.runtime / "run_history.jsonl").write_text(
            '{"stage16_safe_qa_status":"STAGE16_SAFE_QA_OBSERVED_REVIEW_REQUIRED",'
            '"stage16_safe_qa_status":"STAGE16_SAFE_QA_OBSERVED_REVIEW_REQUIRED"}\n',
            encoding="utf-8")
        with self.assertRaises(ValueError):
            attest_stage16_aggregate(self.root, now=CLOCK)
        (self.runtime / "run_history.jsonl").write_text(
            ("x" * 8193) + "\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            attest_stage16_aggregate(self.root, now=CLOCK)

    def test_cli_routes_readonly_stage17_without_live_flag(self):
        with patch("ucie_miner.__main__.inspect_stage17_review",
                   return_value={"status": "EVIDENCE_INCOMPLETE_NO_GO",
                                 "new_public_gets": 0}) as called:
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = miner_main(["inspect-stage17-review"])
        self.assertEqual(exit_code, 0)
        called.assert_called_once()
        self.assertEqual(json.loads(output.getvalue())["new_public_gets"], 0)


if __name__ == "__main__":
    unittest.main()
