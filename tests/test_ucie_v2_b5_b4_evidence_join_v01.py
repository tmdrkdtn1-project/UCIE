"""UCIE first-party negative controls for B4-to-B5 source-linked synthetic join."""
from __future__ import annotations
from unittest import TestCase, mock
from ucie_miner import ucie_v2_b5_b4_evidence_join_v01 as j
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5

def row(method="OFFICIAL_DOCS_ONLY"):
    return {"study_id": b5.STUDY_ID, "case_id": b5.CASE_ID,
            "anonymous_trial_token": "F01", "method": method,
            "cohort": "FIRST_TIME_CODER", "first_safe_action_time_ms": 1000,
            "correct_safe_action": True, "false_version_or_rights_claim": False,
            "evidence_detail_found": False, "origin": b5.SYNTHETIC_ORIGIN}

def sample_hypothesis():
    return {"schema": j.B4_SCHEMA, "hypothesis_id": "UCIE-B4-HYP-test",
            "content_sha256": "a"*64,
            "target_capsule_id": "UCIE-CAPSULE-MCP-PROMPTS-A",
            "shared_candidate_facets": sorted(j.FACETS),
            "parents": [
                {"source_id": s, "skillbook_id": b, "document_sha256": d*64,
                 "independent_qa": False, "rights_approved": False}
                for s,b,d in (("doc:python/cpython","PY","b"),("doc:git/git","GIT","c"))
            ], "cross_source_model_generalization_verified": False,
            "export_allowed": False, "auto_promoted": False, "model_trained": False}

def sample_transfer(h):
    return {"schema": j.B4_SCHEMA, "hypothesis_id": h["hypothesis_id"],
            "content_sha256": h["content_sha256"],
            "positive_negative_control": j.CONTROLS[:],
            "overbroad_output_privacy_claim_rejected": True,
            "real_upstream_sdk_rerun": False, "independent_qa_verified": False,
            "candidate_automatically_approved": False, "export_allowed": False,
            "network_requests": 0, "operating_database_writes": 0}

class B4B5JoinTests(TestCase):
    def evaluate(self, rows, h=None, t=None):
        h = sample_hypothesis() if h is None else h
        t = sample_transfer(h) if t is None else t
        with mock.patch.object(j, "build_hypothesis", return_value=h), \
             mock.patch.object(j, "run_bounded_transfer", return_value=t):
            return j.source_linked_synthetic_review(rows)

    def test_all_three_pairs_review_only(self):
        result = self.evaluate(tuple(row(method) for method in b5.METHODS))
        self.assertEqual(result["status"], "PAIRED_SYNTHETIC_WITH_PINNED_B4_REVIEW_ONLY")
        self.assertEqual(len(result["source_lineage"]), 2)
        self.assertFalse(result["human_study_completed"])
        self.assertFalse(result["real_competitive_advantage_verified"])
        self.assertFalse(result["customer_release_authorized"])

    def test_missing_arm_holds(self):
        report = self.evaluate((row(),))
        self.assertEqual(report["status"], "PAIRED_SYNTHETIC_INCOMPLETE_HOLD")
        self.assertIsNone(report["paired_synthetic_summary"]["comparison"])

    def test_empty_holds(self):
        self.assertEqual(self.evaluate(())["status"], "PAIRED_SYNTHETIC_INCOMPLETE_HOLD")

    def test_bad_source_hash(self):
        h = sample_hypothesis(); h["content_sha256"] = "invalid"
        with self.assertRaises(j.B5SourceJoinError): self.evaluate((),h)

    def test_wrong_repository_denied(self):
        h = sample_hypothesis(); h["parents"][0]["source_id"] = "unapproved/repo"
        with self.assertRaises(j.B5SourceJoinError): self.evaluate((),h)

    def test_negative_control_required(self):
        h = sample_hypothesis(); t = sample_transfer(h)
        t["positive_negative_control"][1] = "CONTRACT_MATCH"
        with self.assertRaises(j.B5SourceJoinError): self.evaluate((),h,t)

    def test_stale_hypothesis_receipt_denied(self):
        h = sample_hypothesis(); t = sample_transfer(h); t["hypothesis_id"] = "old"
        with self.assertRaises(j.B5SourceJoinError): self.evaluate((),h,t)

    def test_promoted_hypothesis_denied(self):
        h = sample_hypothesis(); h["auto_promoted"] = True
        with self.assertRaises(j.B5SourceJoinError): self.evaluate((),h)

    def test_fake_sdk_rerun_denied(self):
        h = sample_hypothesis(); t = sample_transfer(h); t["real_upstream_sdk_rerun"] = True
        with self.assertRaises(j.B5SourceJoinError): self.evaluate((),h,t)

    def test_duplicate_input_denied(self):
        with self.assertRaises(b5.B5StudyContractError): self.evaluate((row(),row()))

    def test_private_field_denied(self):
        bad = row(); bad["user_name"] = "untrusted"
        with self.assertRaises(b5.B5StudyContractError): self.evaluate((bad,))

    def test_false_rights_denied(self):
        h = sample_hypothesis(); h["parents"][0]["rights_approved"] = True
        with self.assertRaises(j.B5SourceJoinError): self.evaluate((),h)
