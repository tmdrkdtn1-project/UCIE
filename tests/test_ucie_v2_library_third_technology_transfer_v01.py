"""Third technology (MCP) falsifies overly broad Python/Git transfer."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from ucie_miner import ucie_v2_library_third_technology_transfer_v01 as s
from ucie_miner import ucie_v2_revision_impact_v01 as b3


class TransferBoundaryTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=s.build_heldout_transfer_review()

    def test_three_exact_techniques_pinned(self):
        self.assertEqual(len(self.report["parents"]),2)
        self.assertEqual({p["source_id"] for p in self.report["parents"]},
                         {"doc:python/cpython","doc:git/git"})
        self.assertEqual(self.report["third_technology"]["source_commit"],
                         b3.PINS["repo:modelcontextprotocol/python-sdk"])

    def test_positive_and_two_negative_transfer_controls(self):
        self.assertEqual([t["observed_first_party_review_result"]
                          for t in self.report["heldout_trials"]],
                         [True,False,False])

    def test_actual_first_party_machine_classifier_not_only_text(self):
        self.assertTrue(s._bounded_transfer_check(
            "BOUNDED_INPUT_AND_EXPLICIT_SCOPE"))
        self.assertFalse(s._bounded_transfer_check("ALL_OUTPUTS_ANONYMIZED"))
        self.assertFalse(s._bounded_transfer_check("UNIVERSAL_SDK_COMPATIBILITY"))

    def test_unapproved_hypothesis_rejected(self):
        with self.assertRaises(s.TransferReviewError):
            s._bounded_transfer_check("ALLOW_ALL_DATA")

    def test_human_original_and_machine_contract_both_created(self):
        self.assertIn("그러나 Python",self.report["original_human_skillbook_chapter"])
        m=self.report["machine_test_contract"]
        self.assertIn("ALL_OUTPUTS_ANONYMIZED",m["rejected_claims"])
        self.assertFalse(m["runtime_execution_enabled"])
        self.assertFalse(m["export_allowed"])

    def test_no_forged_qa_rights_or_release(self):
        for key in ("independent_qa_verified","rights_approved",
                    "customer_release_authorized",
                    "actual_mcp_sdk_reexecuted_now",
                    "autonomous_semantic_discovery_verified"):
            self.assertIs(self.report[key],False)
        self.assertEqual(self.report["network_requests"],0)
        self.assertEqual(self.report["operating_database_writes"],0)

    def test_same_evidence_deterministic(self):
        self.assertEqual(self.report,s.build_heldout_transfer_review())

    def test_source_pin_drift_holds(self):
        with patch.dict(b3.PINS,{"doc:git/git":"b"*64}):
            with self.assertRaises(s.TransferReviewError):
                s.build_heldout_transfer_review()

    def test_forged_release_even_after_rehash_not_rendered(self):
        bad=deepcopy(self.report)
        bad["customer_release_authorized"]=True
        bad["content_sha256"]=s._hash({k:v for k,v in bad.items()
                                       if k!="content_sha256"})
        with self.assertRaises(s.TransferReviewError):
            s.render_heldout_transfer_review(bad)

    def test_review_panel_preserves_rejected_lessons(self):
        html=s.render_heldout_transfer_review(self.report)
        self.assertIn("REJECT_OVERBROAD_OR_UNTESTED_TRANSFER",html)
        self.assertIn("독립 QA 미완료",html)
        self.assertNotIn("<script",html)
        self.assertNotIn("<form",html)
