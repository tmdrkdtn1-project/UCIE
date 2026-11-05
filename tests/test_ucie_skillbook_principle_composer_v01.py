"""UCIE source-linked original cross-technique chapter and first-party tests."""
from __future__ import annotations

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from ucie_miner import skillbook_principle_composer_v01 as comp


class CuratedCrossSourcePrincipleTests(unittest.TestCase):
    def test_curated_two_sources_have_exact_versioned_lineage(self):
        book = comp.compose_bounded_metadata_principle()
        self.assertEqual(book["schema"], comp.SCHEMA)
        self.assertEqual(book["principle_id"], comp.PRINCIPLE_ID)
        self.assertEqual(len(book["sources"]), 2)
        self.assertEqual(len(book["chapters"]), 5)
        self.assertEqual(book["status"], "UCIE_CURATED_CROSS_SOURCE_CHAPTER_DRAFT_NO_GO")
        self.assertTrue(book["human_readable_original_chapter_created"])
        self.assertFalse(book["arbitrary_untrusted_source_synthesis_supported"])
        for row in book["sources"]:
            with self.subTest(row=row["skillbook_id"]):
                p = comp.SUPPORT[row["skillbook_id"]]
                self.assertEqual(row["source_id"], p["source_id"])
                self.assertEqual(row["document_sha256"], p["document_sha256"])
                self.assertEqual(row["source_tag"], p["source_tag"])
                self.assertEqual(row["callable"], p["callable"])
                self.assertEqual(len(row["library_item_id"]), 64)
                self.assertTrue(row["source_approved_for_research_not_redistribution"])

    def test_order_independent_determinism_and_original_authorship(self):
        books = comp._books()
        a = comp.compose_bounded_metadata_principle(books)
        b = comp.compose_bounded_metadata_principle(tuple(reversed(books)))
        self.assertEqual(a, b)
        self.assertEqual(a, comp.compose_bounded_metadata_principle())
        self.assertEqual(len(a["content_sha256"]), 64)
        text = comp.render_principle_markdown(a)
        self.assertIn("공통 원리", text)
        self.assertIn("권한", text)
        self.assertIn("128", text)
        self.assertIn("8192", text)
        self.assertIn("노출", text)
        self.assertIn("독립 검증: 미완료", text)
        self.assertIn("SCANDIR", text.upper())
        self.assertIn("GIT", text.upper())
        self.assertTrue(all(ch["claim_type"].startswith("UCIE_AUTHORED_")
                            for ch in a["chapters"]))

    def test_disclosure_is_not_falsely_homogenized(self):
        a = comp.compose_bounded_metadata_principle()
        pairs = {x["skillbook_id"]: x for x in a["sources"]}
        self.assertEqual(pairs[comp.PYTHON_ID]["data_disclosed"],
                         "SORTED_REGULAR_FILENAMES")
        self.assertEqual(pairs[comp.GIT_ID]["data_disclosed"],
                         "COUNTS_ONLY_NO_FILENAMES")
        self.assertIn("not counts-only", pairs[comp.PYTHON_ID]["risk_note"])
        self.assertFalse(a["machine_consumer"]["real_external_directory_allowed"])

    def test_all_public_and_release_claims_remain_denied(self):
        a = comp.compose_bounded_metadata_principle()
        for key in ("independent_qa_verified", "security_approved",
                    "rights_approved", "owner_approved", "signed",
                    "export_allowed", "released", "automatic_promotion",
                    "model_trained"):
            self.assertIs(a[key], False, key)
        self.assertFalse(a["revision_history"][0]["published"])
        self.assertEqual(a["revision_history"][0]["source_content_sha256"],
                         a["content_sha256"])
        self.assertFalse(a["revision_history"][0]["owner_approved"])
        self.assertEqual(a["network_requests"], 0)
        self.assertEqual(a["operating_database_writes"], 0)
        self.assertFalse(a["other_project_access"])

    def test_duplicate_missing_or_third_book_denied(self):
        p, g = comp._books()
        for items in ((p, p), (p,), (p, g, p), [], [p, g], None, (p, 3)):
            with self.subTest(kind=type(items).__name__):
                with self.assertRaises((comp.PrincipleCompositionError, TypeError)):
                    comp.compose_bounded_metadata_principle(items)

    def test_untrusted_book_mutation_cannot_launder_new_chapter(self):
        p, g = comp._books()
        attacks = (
            ("human_approved", True),
            ("export_allowed", True),
            ("status", "OWNER_APPROVED"),
            ("skillbook_id", "UCIE-SKILLBOOK-NOT-ALLOWED"),
        )
        for key, value in attacks:
            with self.subTest(key=key):
                b = deepcopy(p)
                b[key] = value
                with self.assertRaises(comp.PrincipleCompositionError):
                    comp.compose_bounded_metadata_principle((b, g))
        b = deepcopy(g)
        b["ucie_authored_chapters"][0]["text"] = "forged official claim"
        with self.assertRaises(comp.PrincipleCompositionError):
            comp.compose_bounded_metadata_principle((p, b))

    def test_changes_to_built_in_source_metadata_still_fail_closed(self):
        p, g = comp._books()
        altered = deepcopy(p)
        altered["source_evidence"]["source_tag"] = "v0.0.0"
        with patch.object(comp, "python_skillbook", return_value=altered):
            with self.assertRaises(comp.PrincipleCompositionError):
                comp.compose_bounded_metadata_principle()
        altered = deepcopy(g)
        altered["proof_gates"]["license_redistribution_approved"] = True
        with patch.object(comp, "git_skillbook", return_value=altered):
            with self.assertRaises(comp.PrincipleCompositionError):
                comp.compose_bounded_metadata_principle()

    def test_render_refuses_altered_principle_and_approval(self):
        manuscript = comp.compose_bounded_metadata_principle()
        for key, value in (
            ("owner_approved", True), ("export_allowed", True),
            ("source_content_sha256", "0" * 64),
        ):
            with self.subTest(key=key):
                altered = deepcopy(manuscript)
                altered[key] = value
                with self.assertRaises(comp.PrincipleCompositionError):
                    comp.render_principle_markdown(altered)

    def test_real_synthetic_both_recipes_comparison(self):
        out = comp.run_first_party_synthetic_comparison()
        self.assertEqual(out["schema"], comp.DEMO_SCHEMA)
        self.assertEqual(out["scandir_regular_file_count"], 2)
        self.assertEqual(out["git_parsed_status_entries"], 2)
        self.assertEqual(out["git_counts"]["tracked_changed"], 1)
        self.assertEqual(out["git_counts"]["untracked"], 1)
        self.assertFalse(out["scandir_names_returned_to_external_consumer"])
        self.assertFalse(out["git_names_returned"])
        self.assertFalse(out["independent_qa_verified"])
        self.assertFalse(out["export_allowed"])
        self.assertFalse(out["external_project_access"])
        self.assertEqual(out["operating_database_writes"], 0)
        raw = json.dumps(out, sort_keys=True)
        for secret in ("alpha.txt", "beta.txt", "first.txt", "second.txt"):
            self.assertNotIn(secret, raw)

    def test_contract_is_small_and_exactly_two_known_evidence_sources(self):
        a = comp.compose_bounded_metadata_principle()
        self.assertLessEqual(len(json.dumps(a, ensure_ascii=True).encode("ascii")), 15000)
        self.assertEqual({s["source_id"] for s in a["sources"]},
                         {"doc:python/cpython", "doc:git/git"})
        self.assertEqual(len({s["document_sha256"] for s in a["sources"]}), 2)


if __name__ == "__main__":
    unittest.main()
