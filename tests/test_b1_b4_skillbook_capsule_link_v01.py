"""Focused native Windows test: real B1 source pins -> B4 draft case journey."""
import unittest
from unittest.mock import patch

from ucie_miner.b1_b4_skillbook_capsule_link_v01 import (
    CapsuleLinkError, build_pinned_b1_capsules, build_b4_capsule_journey,
    render_b4_capsule_journey,
)


class TestPinnedB1B4(unittest.TestCase):
    def test_two_real_curated_source_capsules(self):
        capsules = build_pinned_b1_capsules()
        self.assertEqual(len(capsules), 2)
        self.assertEqual({c["source_id"] for c in capsules},
                         {"doc:python/cpython", "doc:git/git"})
        self.assertEqual(len({c["capsule_id"] for c in capsules}), 2)
        self.assertTrue(all(c["capsule_id"].startswith("UCIE-B1-") for c in capsules))

    def test_case_capsule_and_b4_draft_actually_link(self):
        for c in build_pinned_b1_capsules():
            with self.subTest(case_id=c["case_id"]):
                r = build_b4_capsule_journey(c["case_id"])
                self.assertEqual(r["capsule_id"], c["capsule_id"])
                self.assertEqual(r["capsule_sha256"], c["content_sha256"])
                self.assertEqual(r["stage_b4"], "LINKED_REVIEW_ONLY_UNVERIFIED")
                self.assertEqual(r["source_id"], c["source_id"])
                self.assertEqual(len(r["receipt_sha256"]), 64)

    def test_no_false_upstream_or_owner_approval(self):
        for c in build_pinned_b1_capsules():
            self.assertEqual(c["upstream_authenticity"], "NOT_INDEPENDENTLY_ATTESTED")
            self.assertIs(c["export_allowed"], False)
            r = build_b4_capsule_journey(c["case_id"])
            for k in ("independent_upstream_attestation", "independent_qa_verified",
                      "rights_approved", "owner_approved", "export_allowed",
                      "new_local_route_registered"):
                self.assertIs(r[k], False)

    def test_existing_four_error_cases_not_falsely_linked(self):
        for name in ("python-env", "git-repository", "powershell-command",
                     "mcp-prompts", "invented", None):
            with self.subTest(name=name):
                with self.assertRaises(CapsuleLinkError):
                    build_b4_capsule_journey(name)

    def test_deterministic_capsules(self):
        self.assertEqual(build_pinned_b1_capsules(), build_pinned_b1_capsules())

    def test_source_pin_drift_rejected(self):
        from ucie_miner import b1_b4_skillbook_capsule_link_v01 as link
        original = link.build_b4_skillbook
        def changed():
            book = original()
            book["source_provenance"][0]["sha256"] = "0" * 64
            return book
        for capsule in build_pinned_b1_capsules():
            if capsule["source_id"] == "doc:git/git":
                case_id = capsule["case_id"]
                break
        with patch.object(link, "build_b4_skillbook", changed):
            with self.assertRaisesRegex(CapsuleLinkError, "B4_SOURCE_OR_VERSION_DRIFT"):
                build_b4_capsule_journey(case_id)

    def test_render_uses_real_ids_no_form(self):
        case = build_pinned_b1_capsules()[0]
        html = render_b4_capsule_journey(case["case_id"])
        self.assertIn(case["capsule_id"], html)
        self.assertIn("B4", html)
        self.assertNotIn("<form", html)
        self.assertNotIn("href=", html)


if __name__ == "__main__":
    unittest.main()
