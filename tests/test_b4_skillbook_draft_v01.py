"""Focused tests for B4 original SkillBook draft and machine contract."""
import unittest
from copy import deepcopy

from ucie_miner.b4_skillbook_draft_v01 import (
    B4SkillBookError, build_b4_skillbook, render_b4_skillbook_markdown,
)
from ucie_miner.b4_transfer_boundary_v01 import build_transfer_hypothesis


def changed_python():
    source = next(row for row in build_transfer_hypothesis()["parent_source_refs"]
                  if row["source_id"] == "doc:python/cpython")
    return [{
        "source_id": source["source_id"], "expected_sha256": source["sha256"],
        "observed_sha256": "f" * 64, "observed_tag": "v3.15.1",
        "independently_verified": False,
    }]


class TestB4SkillBookDraft(unittest.TestCase):
    def test_deterministic_original_draft(self):
        a = build_b4_skillbook()
        self.assertEqual(a, build_b4_skillbook())
        self.assertEqual(a["status"], "DRAFT_NOT_APPROVED")
        self.assertEqual(len(a["human_chapters"]), 4)
        self.assertEqual(len(a["source_provenance"]), 2)
        self.assertEqual(a["capsule_link_status"], "NOT_AVAILABLE_DO_NOT_INVENT")
        self.assertEqual(a["test_receipts"], [])

    def test_machine_contract_has_bounded_actions(self):
        b = build_b4_skillbook()
        m = b["machine_contract"]
        self.assertEqual(len(m["callables"]), 2)
        self.assertEqual(m["allowed_contexts"],
                         ["BOUNDED_GIT_PORCELAIN", "BOUNDED_SCANDIR"])
        for key in ("source_fetching", "retest_execution", "customer_project_access",
                    "independent_qa_verified", "export_allowed", "released"):
            self.assertIs(m[key], False)

    def test_rights_and_approval_fail_closed(self):
        b = build_b4_skillbook()
        for key in ("independent_qa_verified", "rights_approved", "owner_approved",
                    "export_allowed", "released", "automatic_promotion"):
            self.assertIs(b[key], False)

    def test_markdown_chapters_and_contract(self):
        md = render_b4_skillbook_markdown(build_b4_skillbook())
        self.assertIn("## Machine-readable contract", md)
        self.assertIn("NOT_AVAILABLE", build_b4_skillbook()["capsule_link_status"])
        self.assertIn("doc:python/cpython", md)
        self.assertIn("doc:git/git", md)
        self.assertIn("Export: prohibited", md)

    def test_modified_claim_does_not_render(self):
        b = deepcopy(build_b4_skillbook())
        b["human_chapters"][0]["text"] = "Automatically certified."
        with self.assertRaisesRegex(B4SkillBookError, "BOOK_CONTENT_MISMATCH"):
            render_b4_skillbook_markdown(b)

    def test_revision_impact_embedded_but_never_approved(self):
        b = build_b4_skillbook(changed_python())
        self.assertEqual(b["impact_proposal"]["retests_proposed"], 1)
        self.assertFalse(b["impact_proposal"]["revision_claims_authenticated"])
        self.assertFalse(b["export_allowed"])
        self.assertNotEqual(b["content_sha256"], build_b4_skillbook()["content_sha256"])

    def test_untrusted_revision_source_rejected(self):
        x = changed_python()
        x[0]["source_id"] = "doc:unknown"
        with self.assertRaises(ValueError):
            build_b4_skillbook(x)

    def test_revision_render_with_original_input(self):
        changes = changed_python()
        book = build_b4_skillbook(changes)
        md = render_b4_skillbook_markdown(book, changes)
        self.assertIn("Proposed source revision review", md)
        self.assertIn("Affected source count: 1", md)
        self.assertIn("Test execution: NOT_RUN", md)

    def test_revision_render_without_original_input_rejects(self):
        with self.assertRaisesRegex(B4SkillBookError, "BOOK_CONTENT_MISMATCH"):
            render_b4_skillbook_markdown(build_b4_skillbook(changed_python()))


if __name__ == "__main__":
    unittest.main()
