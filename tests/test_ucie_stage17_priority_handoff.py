"""Stage17 strict ranked Stage12-to-review handoff, synthetic offline only."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner.__main__ import main as cli_main
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, optional_hourly_review_learning,
)
from ucie_miner.public_candidate_staging import stage_public_candidates
from ucie_miner.public_discovery import SOURCE_SKILL
from ucie_miner.public_review_triage import triage_unverified_review_rows
from ucie_miner.stage17_priority_handoff import (
    SCHEMA, build_ranked_stage17_handoff, inspect_stage17_ranked_review,
)
from ucie_miner.stage17_review_docket import build_review_docket
from test_ucie_automated_candidate_qa import handoff
from test_ucie_stage17_review_docket import evidence
from test_ucie_stage11_hourly_stage import fixture_batch


def source_rows(handoff_receipt):
    return [
        (r["source"], r["reference"], SOURCE_SKILL[r["source"]],
         r["evidence_sha256"], ["API_CONTRACT"], None)
        for r in handoff_receipt["tasks"]
    ]


class Stage17RankedReviewTests(unittest.TestCase):
    def setUp(self):
        self.handoff = handoff()
        self.docket = build_review_docket(self.handoff, evidence())
        self.triage = triage_unverified_review_rows(source_rows(self.handoff))

    def test_exact_four_revisions_ranked_with_independent_review_required(self):
        out = build_ranked_stage17_handoff(
            self.handoff, self.docket, self.triage)
        self.assertEqual(out["schema"], SCHEMA)
        self.assertEqual(out["status"], "RANKED_HUMAN_REVIEW_AGENDA_NO_GO")
        self.assertEqual(out["source_revisions"], 4)
        self.assertEqual(out["linked_revisions"], 4)
        self.assertEqual(out["priority_selected_count"], 4)
        self.assertEqual(out["external_api_gets"], 0)
        self.assertEqual(out["persistent_writes"], 0)
        self.assertFalse(out["production_approved"])
        self.assertFalse(out["auto_promoted"])
        self.assertFalse(out["priority_is_confidence"])
        self.assertFalse(out["candidate_specific_ci_attested"])
        for selected in out["priority_selected_for_manual_review"]:
            self.assertEqual(selected["review_priority_band"], "REVIEW_FIRST")
            self.assertEqual(selected["review_priority_score"], 4)
            self.assertFalse(selected["independent_fix_verified"])
            self.assertFalse(selected["license_approved"])
            self.assertFalse(selected["human_approved"])
            self.assertFalse(selected["deploy_allowed"])
            self.assertTrue(selected["required_next_actions"])

    def test_no_stage16_observation_does_not_prevent_human_review(self):
        no16 = {
            "status": "STAGE16_ATTEMPT_ABSENT_NO_GO",
            "ci_run_id": None, "observed_utc": None,
            "synthetic_templates_observed": 0,
            "candidate_snapshot_at_ci_verified": False,
        }
        docket = build_review_docket(self.handoff, no16)
        out = build_ranked_stage17_handoff(
            self.handoff, docket, self.triage)
        self.assertEqual(out["priority_selected_count"], 4)
        self.assertEqual(out["stage16_aggregate_status"], no16["status"])
        self.assertTrue(all(
            x["stage17_review_lane"] == "STAGE16_AGGREGATE_EVIDENCE_MISSING_NO_GO"
            for x in out["priority_selected_for_manual_review"]))
        self.assertEqual(out["approved_rules_added"], 0)

    def test_missing_stage12_review_queue_has_zero_ranked_review(self):
        broken = deepcopy(self.handoff)
        broken["status"] = "SOURCE_REVISIONS_PENDING_NO_GO"
        broken["pending_source_revisions"] = 2
        broken["linked_revisions"] = 4
        docket = build_review_docket(broken, evidence())
        out = build_ranked_stage17_handoff(broken, docket, None)
        self.assertEqual(out["status"], "STAGE12_REVIEW_LEDGER_INCOMPLETE_NO_GO")
        self.assertEqual(out["priority_selected_count"], 0)
        self.assertFalse(out["production_approved"])

    def test_forged_revision_priority_and_candidate_approval_fail_closed(self):
        cases = [
            ("source", lambda triage, docket: triage[
                "selected_for_review"][0].update(source="unauthorized/private")),
            ("hash", lambda triage, docket: triage[
                "selected_for_review"][0].update(evidence_sha256="f" * 64)),
            ("approval", lambda triage, docket: triage[
                "selected_for_review"][0].update(rule_approved=True)),
            ("score", lambda triage, docket: triage[
                "selected_for_review"][0].update(review_priority_score=5)),
            ("tag", lambda triage, docket: triage[
                "selected_for_review"][0].update(error_pattern_tags=["MALICIOUS"])),
            ("action", lambda triage, docket: triage[
                "selected_for_review"][0].update(human_review_action="EXEC_UPSTREAM")),
            ("docket", lambda triage, docket: docket[
                "items"][0].update(human_approval=True)),
        ]
        for name, tamper in cases:
            with self.subTest(name=name):
                triage, docket = deepcopy(self.triage), deepcopy(self.docket)
                tamper(triage, docket)
                with self.assertRaises(ValueError):
                    build_ranked_stage17_handoff(
                        self.handoff, docket, triage)

    def test_existing_local_stage12_ledger_to_stage17_ranked_no_network(self):
        with tempfile.TemporaryDirectory() as rootdir:
            root = Path(rootdir) / "UCIE"
            runtime = root / "runtime"
            runtime.mkdir(parents=True)
            batch = fixture_batch(
                root=root,
                sources=("python/cpython", "PowerShell/PowerShell", "git/git",
                         "modelcontextprotocol/python-sdk", "actions/runner-images"),
                max_enrich=1, include_git_commits=True,
                include_docs=False, include_advisories=False, backfill_pages=1)
            stage_public_candidates(batch, root=root, allow_disk_write=True)
            (runtime / OPT_IN_FILENAME).write_text(OPT_IN_TOKEN, encoding="ascii")
            out = optional_hourly_review_learning(root)
            self.assertEqual(out["new_review_proposals"], 2)
            before = {p.name: p.read_bytes() for p in runtime.iterdir()
                      if p.is_file()}
            with patch(
                    "ucie_miner.automated_candidate_qa._public_json",
                    side_effect=AssertionError("NO API ALLOWED")):
                ranked = inspect_stage17_ranked_review(root)
            after = {p.name: p.read_bytes() for p in runtime.iterdir()
                     if p.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(ranked["status"], "RANKED_HUMAN_REVIEW_AGENDA_NO_GO")
            self.assertEqual(ranked["source_revisions"], 2)
            self.assertEqual(ranked["priority_selected_count"], 2)
            self.assertEqual(ranked["external_api_gets"], 0)
            self.assertFalse(ranked["production_approved"])

    def test_cli_read_only_ranked_review_dispatch(self):
        with patch("ucie_miner.__main__.inspect_stage17_ranked_review",
                   return_value={"schema": SCHEMA, "status": "NO_GO",
                                 "external_api_gets": 0}) as method:
            out = io.StringIO()
            with redirect_stdout(out):
                exit_code = cli_main(["inspect-stage17-ranked-review"])
        self.assertEqual(exit_code, 0)
        method.assert_called_once()
        self.assertEqual(json.loads(out.getvalue())["external_api_gets"], 0)


if __name__ == "__main__":
    unittest.main()
