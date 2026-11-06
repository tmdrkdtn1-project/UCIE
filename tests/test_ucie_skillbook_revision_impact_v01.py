"""UCIE draft revision impact: real existing W04 read-only local HTTP flow.

All content is UCIE first-party or synthetic. No external network, operating
DB, release, auto-withdrawal, Git mutation, human approval or actual QA runs.
"""
from __future__ import annotations

from copy import deepcopy
from http.server import HTTPServer
import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from ucie_miner import skillbook_editorial_production_v01 as author
from ucie_miner import skillbook_catalog_union_v01 as catalog
from ucie_miner import skillbook_pinned_source_review_v01 as pinned
from ucie_miner import skillbook_revision_review_v01 as revision


class RevisionReviewImpactTests(unittest.TestCase):
    def setUp(self):
        self.base = author.compose_curated_two_book_pilot()
        self.new_input = deepcopy(self.base["authoring_input"])
        self.new_input["previous_revision"] = self.base["draft_sha256"]
        self.new_input["draft_version"] = "0.1.1-draft"
        self.new_input["revision_note"] = (
            "Manual proposal after comparing scoped source and negative QA.")
        self.new_input["chapters"][0]["body"] += (
            " Any newly claimed facts require independent validation.")
        self.current = author.compile_review_draft(self.new_input)
        self.raw = b"UCIE synthetic wrong version source; not an official file\n"
        bad = pinned.verify_pinned_raw_bytes("doc:python/cpython", self.raw)
        self.event = pinned.propose_source_review(bad)
        self.journal, _ = pinned.extend_review_journal(b"", self.event)
        self.root = Path("/UCIE_SYNTHETIC_NO_OWNER_RUNTIME")

    def test_linked_revision_marks_retests_and_source_mismatch(self):
        result = revision.assess_revision_review_impact(
            self.base, self.current, pinned_review_history=self.journal)
        self.assertEqual(result["schema"], revision.REVISION_IMPACT_SCHEMA)
        self.assertEqual(result["status"],
                         "AUTHORING_REVISION_REQUIRES_EXPERT_REVIEW_NO_GO")
        self.assertEqual(result["old_draft_sha256"], self.base["draft_sha256"])
        self.assertEqual(result["new_draft_sha256"], self.current["draft_sha256"])
        self.assertEqual(result["changed_chapter_ids"], ["MECHANISM"])
        self.assertIn("MECHANISM", result["recheck_chapter_ids"])
        self.assertEqual(result["journal_event_count"], 1)
        self.assertEqual(len(result["required_retests"]), 4)
        self.assertTrue(all(x["execution_status"] ==
                            "NOT_RUN_BY_REVISION_ASSESSMENT"
                            for x in result["required_retests"]))
        self.assertFalse(result["technical_claim_review_completed"])
        self.assertFalse(result["independent_qa_completed"])
        self.assertFalse(result["withdrawal_executed"])
        self.assertFalse(result["review_journal_written"])
        self.assertFalse(result["owner_approval_granted"])
        self.assertFalse(result["export_allowed"])
        self.assertFalse(result["released"])
        self.assertEqual(result["operating_database_writes"], 0)
        py = next(x for x in result["sources"]
                  if x["source_id"] == "doc:python/cpython")
        self.assertEqual(py["source_ledger_state"],
                         "PIN_MISMATCH_REVALIDATION_REQUIRED")
        self.assertEqual(py["review_event_id"], self.event["event_id"])
        self.assertFalse(py["export_allowed"])
        self.assertTrue(set(py["associated_chapter_ids"]).issubset(
            set(result["recheck_chapter_ids"])))

    def test_changed_machine_contract_rechecks_negative_cases(self):
        record = deepcopy(self.new_input)
        record["machine_contract"]["failure_contract"] += (
            " Every contradictory case must block further processing.")
        changed = author.compile_review_draft(record)
        report = revision.assess_revision_review_impact(
            self.base, changed, pinned_review_history=b"")
        self.assertTrue(report["machine_contract_changed"])
        for cid in ("SAFE_PRECONDITIONS", "BOUNDED_APPLICATION",
                    "COUNTEREXAMPLES", "VERSION_AND_QA_LIMITATIONS"):
            self.assertIn(cid, report["recheck_chapter_ids"])
        self.assertFalse(report["running_skill_mutated"])

    def test_unrelated_parent_does_not_create_forged_lineage(self):
        tampered = deepcopy(self.current)
        tampered["authoring_input"]["previous_revision"] = "0" * 64
        with self.assertRaises(author.EditorialDraftError):
            revision.assess_revision_review_impact(self.base, tampered)
        rec = deepcopy(self.new_input)
        rec["previous_revision"] = "0" * 64
        orphan = author.compile_review_draft(rec)
        with self.assertRaises(author.EditorialDraftError):
            revision.assess_revision_review_impact(self.base, orphan)
        with self.assertRaises(author.EditorialDraftError):
            revision.assess_revision_review_impact(
                self.base, self.current, pinned_review_history=b"not-journal")

    def test_unlinked_revision_cannot_be_misrepresented_as_approved(self):
        detail = catalog.inspect_review_candidate(
            self.current["draft_sha256"],
            editorial_records=(self.new_input,), pinned_review_history=self.journal)
        impact = detail["revision_review_impact"]
        self.assertEqual(impact["status"],
                         "PREVIOUS_REVISION_NOT_SUPPLIED_REVIEW_BLOCKED")
        self.assertFalse(impact["export_allowed"])
        self.assertFalse(impact["owner_approval_granted"])
        self.assertIn("이전 초안 실물 미제공",
                      catalog.render_review_candidate(detail))

    def test_browse_with_explicit_prior_returns_same_retest_worksheet(self):
        detail = catalog.inspect_review_candidate(
            self.current["draft_sha256"],
            editorial_records=(self.new_input,),
            pinned_review_history=self.journal,
            previous_editorial_draft=self.base)
        impact = detail["revision_review_impact"]
        self.assertEqual(impact["changed_chapter_ids"], ["MECHANISM"])
        self.assertIn("COUNTEREXAMPLES", impact["recheck_chapter_ids"])
        self.assertEqual(impact["journal_event_count"], 1)
        self.assertFalse(detail["manual_editorial_review_completed"])
        self.assertFalse(detail["export_allowed"])
        html = catalog.render_review_candidate(detail)
        self.assertIn("개정 영향 및 필수 재검토", html)
        self.assertIn("PIN_MISMATCH_REVALIDATION_REQUIRED", html)
        self.assertIn("test_ucie_skillbook_w09_release_gate_v01.py", html)
        self.assertIn("미실행", html)

    def test_real_http_detail_and_json_with_prerecorded_history(self):
        handler = catalog.make_handler(
            self.root, public_reader=lambda *_a, **_k: self.fail("W04 not requested"),
            editorial_records=(self.new_input,),
            pinned_review_history=self.journal,
            previous_editorial_draft=self.base)
        with HTTPServer(("127.0.0.1", 0), handler) as server:
            thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.05}, daemon=True)
            thread.start()
            base_url = "http://127.0.0.1:" + str(server.server_port)
            def get(route, host=None):
                request = Request(
                    base_url + route,
                    headers={} if host is None else {"Host": host})
                try:
                    with urlopen(request, timeout=6) as response:
                        return response.status, response.read().decode("utf-8")
                except HTTPError as exc:
                    with exc:
                        return exc.code, exc.read().decode("utf-8")
            try:
                with patch.object(
                    pinned, "persist_review_event",
                    side_effect=AssertionError("GET must never write")):
                    with patch.object(
                        pinned, "verify_ucie_inbox",
                        side_effect=AssertionError("GET must not read original bytes")):
                        sha = self.current["draft_sha256"]
                        status, html = get("/catalog/review?id=" + sha)
                        self.assertEqual(status, 200)
                        self.assertIn("개정 영향 및 필수 재검토", html)
                        status, body = get("/catalog/review.json?id=" + sha)
                        self.assertEqual(status, 200)
                        detail = json.loads(body)
                        impact = detail["revision_review_impact"]
                        self.assertEqual(impact["journal_head_sha256"],
                                         pinned.inspect_review_journal(
                                             self.journal)["last_hash"])
                        self.assertFalse(impact["withdrawal_executed"])
                        self.assertEqual(impact["external_network_requests"], 0)
                        self.assertEqual(impact["operating_database_writes"], 0)
                        self.assertEqual(get("/catalog/review?approve=true")[0], 400)
                        self.assertEqual(get("/catalog/review?withdraw=true")[0], 400)
                        self.assertEqual(get("/catalog/review.json?id=" + sha,
                                             host="untrusted.invalid")[0], 403)
            finally:
                server.shutdown()
                thread.join(timeout=3)

    def test_no_actual_review_journal_event_created_by_diff(self):
        detail = catalog.inspect_review_candidate(
            self.current["draft_sha256"],
            editorial_records=(self.new_input,),
            pinned_review_history=self.journal,
            previous_editorial_draft=self.base)
        self.assertEqual(detail["revision_review_impact"]["journal_event_count"], 1)
        self.assertEqual(
            pinned.inspect_review_journal(self.journal)["total_events"], 1)
        self.assertTrue(detail["pinned_review_history_is_unsigned"])
        self.assertFalse(detail["revision_review_impact"]["review_journal_written"])


if __name__ == "__main__":
    unittest.main()
