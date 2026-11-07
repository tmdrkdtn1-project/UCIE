"""Full four-pillar UCIE installed staging CLI functional acceptance.

These are REAL first-party algorithm executions on fixed synthetic fixtures,
not an independent review or authorization to release a commercial product.
No actual customer's data, Git repository or system TaskScheduler is read.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from unittest.mock import patch
import unittest

from ucie_miner import customer_staging_v01 as stage


class FourPillarStagingAcceptance(unittest.TestCase):
    def test_all_four_first_party_product_pillars_execute(self):
        result = stage.run_four_pillar_staging()
        self.assertEqual(result["schema"], stage.SCHEMA)
        self.assertEqual(result["status"], stage.STATE)
        self.assertEqual(tuple(result["pillars_exercised"]), stage.PILLARS)
        self.assertEqual(set(result["workflows"]), set(stage.PILLARS))
        self.assertTrue(result["four_pillars_exercised"])
        self.assertTrue(result["product_capabilities_worked_in_staging"])
        self.assertFalse(result["complete_customer_functional_acceptance"])

    def test_real_scandir_recipe_and_guarded_iterator(self):
        item = stage.run_four_pillar_staging(
            pillar="error_prevention"
        )["workflows"]["error_prevention"]
        self.assertTrue(item["real_ucie_recipe_executed"])
        self.assertTrue(item["guarded_iterator_executed"])
        self.assertTrue(item["all_iterator_resources_closed"])
        self.assertEqual(item["synthetic_file_count"], 2)
        self.assertFalse(item["customer_directory_inspected"])
        self.assertFalse(item["automatic_fix_applied"])

    def test_development_engine_skill_and_learning_logic_all_execute(self):
        result = stage.run_four_pillar_staging(
            pillar="development_engines_and_skills"
        )
        recipes = result["workflows"][
            "development_engines_and_skills"
        ]["development_engine_skill_learning_logic_trials"]
        self.assertEqual(len(recipes), 3)
        self.assertEqual(
            {r["kind"] for r in recipes},
            {"DEVELOPMENT_ENGINE", "REUSABLE_SKILL", "LEARNING_LOGIC"},
        )
        for trial in recipes:
            self.assertTrue(trial["exact_result_equivalence_observed"])
            self.assertFalse(trial["production_adopted"])
            self.assertFalse(trial["upstream_benefit_verified"])

    def test_library_exposes_two_source_anchored_drafts_not_products(self):
        x = stage.run_four_pillar_staging(
            pillar="virtual_library_and_skillbooks"
        )["workflows"]["virtual_library_and_skillbooks"]
        self.assertEqual(x["fixed_library_total"], 2)
        self.assertEqual(x["filtered_book_count"], 2)
        self.assertEqual({b["source_id"] for b in x["books"]},
                         {"doc:python/cpython", "doc:git/git"})
        self.assertTrue(all(b["chapter_count"] >= 1 for b in x["books"]))
        self.assertTrue(all(b["customer_export_allowed"] is False
                            for b in x["books"]))
        self.assertEqual(x["approved_or_exportable_books"], 0)
        self.assertEqual(x["git_porcelain_recipe_synthetic_entries_verified"], 2)
        self.assertFalse(x["external_git_process_invoked"])

    def test_library_filter_and_empty_query_result_are_not_approval(self):
        a = stage.run_four_pillar_staging(
            pillar="virtual_library_and_skillbooks", query="porcelain"
        )["workflows"]["virtual_library_and_skillbooks"]
        self.assertEqual(a["fixed_library_total"], 2)
        self.assertEqual(a["filtered_book_count"], 1)
        self.assertEqual(a["books"][0]["source_id"], "doc:git/git")
        z = stage.run_four_pillar_staging(
            pillar="virtual_library_and_skillbooks", query="nonexistentlesson"
        )["workflows"]["virtual_library_and_skillbooks"]
        self.assertEqual(z["filtered_book_count"], 0)
        self.assertEqual(z["approved_or_exportable_books"], 0)

    def test_continuous_experiment_produces_real_no_promotion_receipt(self):
        row = stage.run_four_pillar_staging(
            pillar="continuous_evidence_evolution"
        )["workflows"]["continuous_evidence_evolution"]
        self.assertEqual(row["status"],
                         "UCIE_OWNED_NEXT_EXPERIMENT_EXERCISED_NO_PROMOTION")
        self.assertTrue(row["exact_result_equivalence_observed"])
        self.assertFalse(row["experience_ledger_written"])
        self.assertFalse(row["model_weights_changed"])
        self.assertFalse(row["production_change_applied"])
        self.assertEqual(len(row["experiment_dataset_sha256"]), 64)

    def test_no_later_pillar_executes_when_explicit_single_selected(self):
        with (patch.object(stage, "_engines") as engines,
              patch.object(stage, "_library") as library,
              patch.object(stage, "_evolution") as evolution):
            r = stage.run_four_pillar_staging(pillar="error_prevention")
        self.assertEqual(r["pillars_exercised"], ["error_prevention"])
        self.assertFalse(r["four_pillars_exercised"])
        engines.assert_not_called()
        library.assert_not_called()
        evolution.assert_not_called()

    def test_wrong_pillar_and_external_source_parameters_fail_closed(self):
        for key in ("../customer-repository", "all-and-install", "", None, 3):
            with self.subTest(key=key), self.assertRaises(
                stage.CustomerStagingError
            ):
                stage.run_four_pillar_staging(pillar=key)
        with self.assertRaises(stage.CustomerStagingError):
            stage.run_four_pillar_staging(
                pillar="error_prevention", query="customer source"
            )
        with self.assertRaises(stage.CustomerStagingError):
            stage.run_four_pillar_staging(query="a" * 49)

    def test_cli_prints_one_machine_readable_json_result(self):
        out = StringIO()
        with redirect_stdout(out):
            rc = stage.main(["--pillar", "virtual_library_and_skillbooks",
                             "--query", "porcelain"])
        self.assertEqual(rc, 0)
        parsed = json.loads(out.getvalue())
        self.assertEqual(parsed["requested_pillar"],
                         "virtual_library_and_skillbooks")
        self.assertEqual(parsed["workflows"][
            "virtual_library_and_skillbooks"
        ]["filtered_book_count"], 1)
        self.assertFalse(parsed["customer_distribution_authorized"])

    def test_cli_does_not_leak_exceptions_or_project_paths(self):
        with (patch.object(stage, "_engines",
                           side_effect=RuntimeError(
                               "sensitive customer directory and secret")),
              redirect_stdout(StringIO()) as out):
            code = stage.main(["--pillar",
                               "development_engines_and_skills"])
        self.assertEqual(code, 2)
        obj = json.loads(out.getvalue())
        self.assertEqual(obj["status"],
                         "UCIE_FOUR_PILLAR_STAGING_FAIL_CLOSED")
        self.assertNotIn("sensitive", out.getvalue())
        self.assertNotIn("secret", out.getvalue())
        self.assertFalse(obj["customer_distribution_authorized"])

    def test_no_real_customer_data_or_auto_release_claim(self):
        result = stage.run_four_pillar_staging()
        for name in ("customer_license_issued", "customer_bundle_signed",
                     "customer_distribution_authorized",
                     "customer_data_scanned", "upstream_source_executed",
                     "operating_ucie_database_written",
                     "customer_project_modified", "scheduler_modified",
                     "automatic_rule_promotion"):
            self.assertIs(result[name], False)
        self.assertEqual(result["distribution"],
                         "PRIVATE_DESIGNATED_CUSTOMERS_PROPRIETARY")
        self.assertEqual(result["execution_scope"],
                         "UCIE_AUTHORED_DISPOSABLE_SYNTHETIC_ONLY")

    def test_installed_entrypoint_metadata_is_declared_in_project(self):
        import os
        import tomllib
        if os.environ.get("GITHUB_ACTIONS") != "true":
            self.skipTest("owner local pyproject is preserved; check clean CI")
        with (Path(__file__).resolve().parents[1] /
              "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)
        self.assertEqual(project["project"]["scripts"][
            "ucie-product-preview"
        ], "ucie_miner.customer_staging_v01:main")


if __name__ == "__main__":
    unittest.main()
