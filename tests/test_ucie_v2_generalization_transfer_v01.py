"""B4 original source-bound hypothesis and negative transfer control tests."""
from __future__ import annotations

from copy import deepcopy
from unittest import TestCase, mock

from ucie_miner import ucie_v2_generalization_transfer_v01 as b4


class UCIEB4TransferTests(TestCase):
    def test_distinct_python_git_sources_and_exact_digest_pins(self):
        x = b4.build_hypothesis()
        self.assertEqual(x["schema"], b4.SCHEMA)
        self.assertEqual(len(x["parents"]), 2)
        self.assertEqual({p["source_id"] for p in x["parents"]},
                         {"doc:python/cpython", "doc:git/git"})
        self.assertEqual(x["shared_candidate_facets"], sorted(b4.FACETS))
        self.assertEqual(len(x["content_sha256"]), 64)

    def test_real_third_ucie_mcp_synthetic_positive_negative_control(self):
        x = b4.run_bounded_transfer(b4.build_hypothesis())
        self.assertEqual(x["positive_negative_control"], [
            "CONTRACT_MATCH", "CONTRACT_VIOLATION", "CONTROL_ONLY"])
        self.assertEqual(x["synthetic_cases_executed"], 3)
        self.assertFalse(x["real_upstream_sdk_rerun"])
        self.assertFalse(x["independent_qa_verified"])

    def test_deterministic_hypothesis_id(self):
        a, b = b4.build_hypothesis(), b4.build_hypothesis()
        self.assertEqual(a, b)
        self.assertIn(a["content_sha256"][:20], a["hypothesis_id"])

    def test_human_original_hypothesis_is_not_upstream_fact(self):
        x = b4.build_hypothesis()
        self.assertEqual(x["method"], b4.METHOD)
        self.assertIn("설계 후보", x["hypothesis"])
        self.assertEqual(x["human_skillbook_chapter_status"],
                         "UCIE_ORIGINAL_HYPOTHESIS_DRAFT_ONLY")
        self.assertFalse(x["source_facts_independently_verified"])
        self.assertFalse(x["cross_source_model_generalization_verified"])

    def test_no_distribution_or_training_claim(self):
        x = b4.build_hypothesis()
        for key in ("model_trained", "owner_approved",
                    "license_redistribution_approved", "published",
                    "export_allowed", "auto_promoted"):
            self.assertIs(x[key], False)

    def test_safe_machine_contract_never_executes_customer_inputs(self):
        x = b4.build_hypothesis()
        recipe = x["machine_test_recipe"]
        self.assertEqual(recipe["positive_case"], "missing_required_argument")
        self.assertFalse(recipe["target_runtime_import_or_network_allowed"])
        self.assertFalse(recipe["customer_data_input_allowed"])
        self.assertEqual(x["network_requests"], 0)
        self.assertEqual(x["operating_database_writes"], 0)

    def test_forged_hypothesis_id_denied(self):
        x = b4.build_hypothesis()
        x["hypothesis_id"] = "UCIE-B4-HYP-FAKE"
        with self.assertRaises(b4.B4HypothesisError):
            b4.run_bounded_transfer(x)

    def test_forged_export_approval_denied(self):
        x = b4.build_hypothesis()
        x["export_allowed"] = True
        with self.assertRaises(b4.B4HypothesisError):
            b4.run_bounded_transfer(x)

    def test_forged_parent_source_digest_denied(self):
        x = b4.build_hypothesis()
        x["parents"][0]["document_sha256"] = "0"*64
        with self.assertRaises(b4.B4HypothesisError):
            b4.run_bounded_transfer(x)

    def test_extra_untrusted_source_denied(self):
        x = b4.build_hypothesis()
        x["parents"].append({"source_id": "repo:unapproved"})
        with self.assertRaises(b4.B4HypothesisError):
            b4.run_bounded_transfer(x)

    def test_malformed_hypothesis_denied(self):
        for candidate in (None, "", {}, [], False):
            with self.subTest(candidate=str(type(candidate))):
                with self.assertRaises(b4.B4HypothesisError):
                    b4.run_bounded_transfer(candidate)

    def test_unreviewed_resource_scope_rejected(self):
        real_py = __import__(
            "ucie_miner.skillbook_product_v01", fromlist=["build_skillbook"]
        )
        altered = deepcopy(real_py.build_skillbook())
        altered["machine_skill_contract"]["inputs"]["max_entries"] = "UNBOUNDED"
        with self.assertRaises(b4.B4HypothesisError):
            b4._valid_book(
                altered, "doc:python/cpython",
                "9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a",
                "UCIE-SKILLBOOK-PY-SCANDIR-001",
                "ucie_miner.skillbook_scandir_recipe_v01.bounded_regular_file_names",
            )

    def test_source_io_and_private_access_forgery_rejected(self):
        mod = __import__("ucie_miner.skillbook_product_v01", fromlist=["build_skillbook"])
        original = mod.build_skillbook()
        for field, forged in (("network_requests", 1),
                              ("operating_database_writes", 1),
                              ("other_project_access", True),
                              ("upstream_source_executed", True)):
            with self.subTest(field=field):
                altered = deepcopy(original)
                altered[field] = forged
                with self.assertRaises(b4.B4HypothesisError):
                    b4._valid_book(
                        altered, "doc:python/cpython",
                        "9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a",
                        "UCIE-SKILLBOOK-PY-SCANDIR-001",
                        "ucie_miner.skillbook_scandir_recipe_v01.bounded_regular_file_names",
                    )

    def test_missing_fail_closed_control_rejected(self):
        mod = __import__(
            "ucie_miner.skillbook_git_porcelain_product_v01",
            fromlist=["build_skillbook"]
        )
        altered = deepcopy(mod.build_skillbook())
        altered["machine_skill_contract"]["outputs"]["on_failure"] = "SILENT_SUCCESS"
        with self.assertRaises(b4.B4HypothesisError):
            b4._valid_book(
                altered, "doc:git/git",
                "1cdd1c7339dfc64093687b6e072d59feee584b8639c0203ece0a1150ce23d325",
                "UCIE-SKILLBOOK-GIT-PORCELAIN-002",
                "ucie_miner.skillbook_git_porcelain_recipe_v01.summarize_porcelain_v1_z",
            )

    def test_false_approval_on_book_rejected(self):
        mod = __import__("ucie_miner.skillbook_product_v01", fromlist=["build_skillbook"])
        altered = deepcopy(mod.build_skillbook())
        altered["proof_gates"]["human_approved"] = True
        with self.assertRaises(b4.B4HypothesisError):
            b4._valid_book(
                altered, "doc:python/cpython",
                "9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a",
                "UCIE-SKILLBOOK-PY-SCANDIR-001",
                "ucie_miner.skillbook_scandir_recipe_v01.bounded_regular_file_names",
            )

    def test_inherited_b3_pins_drift_rejected(self):
        from ucie_miner import ucie_v2_revision_impact_v01 as b3
        with mock.patch.dict(b3.PINS, {"doc:python/cpython": "f"*64}):
            with self.assertRaises((b4.B4HypothesisError, b3.RevisionImpactError)):
                b4.build_hypothesis()


if __name__ == "__main__":
    import unittest
    unittest.main()
