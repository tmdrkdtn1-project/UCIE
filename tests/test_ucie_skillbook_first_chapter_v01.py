"""First real UCIE-authored SkillBook draft acceptance, no upstream code run."""
from __future__ import annotations
import unittest

from ucie_miner.skillbook_first_chapter_v01 import (
    build_first_skillbook, search_first_skillbook, evaluate_synthetic_case, CASES,
)


class SkillBookFirstChapterTests(unittest.TestCase):
    def test_original_chapter_and_machine_contract(self):
        d = build_first_skillbook()
        self.assertIn("resource snapshot", d["human_readable_chapter"])
        self.assertEqual(d["machine_contract"]["schema"],
                         "UCIE_MACHINE_SKILL_CONTRACT_DRAFT_V01")
        self.assertEqual(d["library_entry"]["entry_status"], "UNVERIFIED_CANDIDATE_ONLY")
        self.assertFalse(d["machine_contract"]["installable"])

    def test_exact_public_identity_without_upstream_proof(self):
        d = build_first_skillbook()
        m = d["evidence_manifest"]
        self.assertEqual(m["source_url"], "https://github.com/python/cpython/pull/160930")
        self.assertEqual(m["merge_commit_sha"], "af79f49308f8f87896d1c09419db3f5ff67185af")
        self.assertEqual(m["digest_scope"], "UCIE_AUTHORED_METADATA_NOT_UPSTREAM_CONTENT")
        self.assertFalse(m["upstream_content_hashed"])
        self.assertEqual(m["version_status"], "UNVERIFIED")

    def test_three_positive_negative_synthetic_cases(self):
        d = build_first_skillbook()
        self.assertEqual(d["synthetic_evaluation"]["passed"], 3)
        self.assertEqual(d["synthetic_evaluation"]["total"], 3)
        cases = {x["case"]: x for x in d["synthetic_evaluation"]["cases"]}
        self.assertTrue(cases["benign_cleanup"]["naive_early_compare_flags_change"])
        self.assertFalse(cases["benign_cleanup"]["gated_compare_flags_change"])
        self.assertTrue(cases["changed_count"]["gated_compare_flags_change"])
        self.assertIsNone(cases["no_completion"]["gated_compare_flags_change"])

    def test_fail_closed_malformed_synthetic_case(self):
        for x in ([], {}, None, ("a", True, 1, 1, True, "STABLE_NO_CHANGE"),
                  ("a", -1, 1, 1, True, "STABLE_NO_CHANGE"),
                  ("a", 1, 1, 1, 1, "STABLE_NO_CHANGE"),
                  ("a", 1, 1, 1, True, "APPROVED")):
            with self.subTest(x=str(x)[:30]), self.assertRaises(ValueError):
                evaluate_synthetic_case(x)

    def test_deterministic_w04_linked_catalog(self):
        a = build_first_skillbook()
        self.assertEqual(a, build_first_skillbook())
        for q in ("", "Python", "STABLE", "python/cpython"):
            self.assertEqual(search_first_skillbook(q)["total_matches"], 1)
        self.assertEqual(search_first_skillbook("Ruby")["total_matches"], 0)
        row = search_first_skillbook("Python", kind="REUSABLE_SKILL",
                                     source_id="repo:python/cpython")["items"][0]
        self.assertEqual(row["library_item_id"], a["library_entry"]["library_item_id"])
        self.assertFalse(row["export_allowed"])

    def test_rejects_unapproved_query_and_filter(self):
        for q in (None, "a" * 81, "../private", "https://other.com"):
            with self.subTest(q=q), self.assertRaises(ValueError):
                search_first_skillbook(q)
        with self.assertRaises(ValueError):
            search_first_skillbook(kind="PUBLISHED")
        with self.assertRaises(ValueError):
            search_first_skillbook(source_id="repo:other/private")

    def test_no_approval_or_mutation(self):
        d = build_first_skillbook()
        for key in ("license_cleared", "version_verified", "owner_approved",
                    "independent_upstream_qa", "export_allowed", "model_trained",
                    "other_project_access"):
            self.assertFalse(d["gates"][key])
        self.assertEqual(d["gates"]["operating_database_writes"], 0)
        self.assertFalse(search_first_skillbook()["index_persisted"])


if __name__ == "__main__":
    unittest.main()
