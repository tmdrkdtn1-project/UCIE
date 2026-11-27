"""UCIE B0/B1/B2-to-B4 honest local linkage tests."""
import unittest
from unittest.mock import patch

from ucie_miner.local_b4_journey_link_v01 import (
    LocalB4LinkError, build_local_b4_journey, render_local_b4_journey
)


class TestLocalB4Journey(unittest.TestCase):
    def test_known_cases_are_not_falsely_linked(self):
        for case_id in ("python-env", "powershell-command", "git-repository", "mcp-prompts"):
            with self.subTest(case_id=case_id):
                r = build_local_b4_journey(case_id)
                self.assertEqual(r["case_id"], case_id)
                self.assertEqual(r["case_to_b4_link"], "HOLD_NO_VERIFIED_B1_CAPSULE")
                self.assertIsNone(r["capsule_id"])
                self.assertIs(r["b4_linked_to_case"], False)
                self.assertIs(r["export_allowed"], False)
                self.assertEqual(len(r["b4_source_refs"]), 2)

    def test_real_b4_skillbook_provenance_retained(self):
        r = build_local_b4_journey("python-env")
        ids = {x["source_id"] for x in r["b4_source_refs"]}
        self.assertEqual(ids, {"doc:python/cpython", "doc:git/git"})
        self.assertEqual(len(r["b4_skillbook_sha256"]), 64)
        self.assertEqual(len(r["receipt_sha256"]), 64)

    def test_unknown_and_wrong_type_rejected(self):
        for case in ("fake-case", "BOUNDED_SCANDIR", None, 2):
            with self.subTest(case=case):
                with self.assertRaises(LocalB4LinkError):
                    build_local_b4_journey(case)

    def test_case_source_missing_rejected(self):
        with patch("ucie_miner.local_b4_journey_link_v01.get_case",
                   return_value={"case_id": "python-env", "official_url": "file:///private"}):
            with self.assertRaisesRegex(LocalB4LinkError, "CASE_SOURCE_NOT_VERIFIED"):
                build_local_b4_journey("python-env")

    def test_bad_case_identity_rejected(self):
        with patch("ucie_miner.local_b4_journey_link_v01.get_case",
                   return_value={"case_id": "other", "official_url": "https://example.org"}):
            with self.assertRaisesRegex(LocalB4LinkError, "CASE_ID_DRIFT"):
                build_local_b4_journey("python-env")

    def test_html_plain_status_no_unapproved_links(self):
        out = render_local_b4_journey("git-repository")
        self.assertIn("검증된 Capsule ID가 없어 보류", out)
        self.assertIn("data-ucie-b4-journey=", out)
        self.assertNotIn("<form", out)
        self.assertNotIn("http", out)

    def test_deterministic_receipt(self):
        self.assertEqual(build_local_b4_journey("mcp-prompts"),
                         build_local_b4_journey("mcp-prompts"))


if __name__ == "__main__":
    unittest.main()
