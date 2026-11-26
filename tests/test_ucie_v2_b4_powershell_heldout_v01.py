"""PowerShell held-out B4 generalization regressions (all first-party synthetic)."""
from __future__ import annotations

from copy import deepcopy
from unittest import TestCase, mock

from ucie_miner import ucie_v2_b4_powershell_heldout_v01 as held


class B4HeldoutPowerShellTests(TestCase):
    def test_deterministic_source_linked_heldout_proposal(self):
        x = held.build_heldout_hypothesis()
        self.assertEqual(x, held.build_heldout_hypothesis())
        self.assertEqual(x["schema"], held.SCHEMA)
        self.assertEqual(x["status"], held.STATUS)
        self.assertTrue(x["hypothesis_id"].startswith("UCIE-B4-HELDOUT-PS-"))
        self.assertIn(x["content_sha256"][:20], x["hypothesis_id"])
        self.assertEqual(x["heldout_case_id"], "powershell-command")
        self.assertEqual(x["source"]["repo"], "PowerShell/PowerShell")
        self.assertEqual(x["source"]["tag"], "v7.5.4")
        self.assertEqual(x["source"]["tag_commit_sha"], held.SOURCE_COMMIT)
        self.assertEqual(x["source"]["source_blob_sha"], held.SOURCE_BLOB_SHA)
        self.assertEqual(x["source"]["license_blob_sha"], held.LICENSE_BLOB_SHA)
        self.assertEqual(x["source"]["license_review_state"],
                         "MIT_FILE_INSPECTED_REUSE_NOT_AUTHORIZED")

    def test_original_reprocess_has_parent_and_counterclaims(self):
        x = held.build_heldout_hypothesis()
        self.assertEqual(len(x["parent_skillbooks"]), 2)
        self.assertEqual(len(x["conditional_facets_transferred"]), 4)
        self.assertEqual(len(x["nontransferable_claims"]), 4)
        self.assertIn("ALL_COMMANDS_WITH_SAME_NAME_ARE_ALWAYS_LOADED",
                      x["nontransferable_claims"])
        self.assertIn("PATH_QUALIFIED_COMMANDS_FOLLOW_UNQUALIFIED_PRECEDENCE",
                      x["nontransferable_claims"])
        self.assertIn("재배포", x["human_skillbook_chapter"]["limitations"])
        self.assertEqual(x["human_skillbook_chapter"]["status"],
                         "ORIGINAL_BOUNDED_HELDOUT_DRAFT_UNREVIEWED")

    def test_machine_recipe_is_original_and_no_implicit_shell(self):
        x = held.build_heldout_hypothesis()
        recipe = x["machine_recipe"]
        self.assertEqual(recipe["max_candidates"], 4)
        self.assertTrue(recipe["no_command_names_or_shell"])
        self.assertEqual(recipe["positive"], "EXPLICIT_CMDLET_FILTER")
        self.assertEqual(recipe["negative"], "ALIAS_OVER_CMDLET")
        self.assertEqual(recipe["counterexample"], "UNKNOWN_MODULE_LOAD_STATE")

    def test_six_concrete_transfer_controls_are_executed(self):
        x = held.build_heldout_hypothesis()
        result = held.evaluate_heldout_hypothesis(x)
        self.assertEqual(result["status"],
                         "FIRST_PARTY_HELDOUT_SYNTHETIC_RECIPE_EXECUTED_REVIEW_ONLY")
        self.assertEqual(result["outcomes"], list(held.EXPECTED))
        self.assertEqual(result["synthetic_cases_executed"], 6)
        self.assertEqual(result["negative_overgeneralizations_rejected"], 4)

    def test_alias_shadows_cmdlet_independent_of_input_order(self):
        for values in (("Alias", "Cmdlet"), ("Cmdlet", "Alias")):
            with self.subTest(values=values):
                result = held.finite_loaded_command_resolution(values)
                self.assertEqual(result["status"], "ALIAS_SHADOWS_CMDLET")
                self.assertEqual(result["predicted_type"], "Alias")

    def test_typed_cmdlet_request_disambiguates_alias_without_running(self):
        v = held.finite_loaded_command_resolution(
            ("Cmdlet", "Alias"), requested_type="Cmdlet")
        self.assertEqual(v["status"], "EXPLICIT_CMDLET_CONTRACT_FOUND")
        self.assertEqual(v["predicted_type"], "Cmdlet")
        self.assertFalse(v["session_state_read"])
        self.assertFalse(v["powershell_executed"])

    def test_loaded_function_wins_over_loaded_cmdlet(self):
        v = held.finite_loaded_command_resolution(("Function", "Cmdlet"))
        self.assertEqual(v["status"], "FUNCTION_SHADOWS_CMDLET")

    def test_unloaded_module_held_out_counterexample(self):
        v = held.finite_loaded_command_resolution(
            ("Alias", "Application"), load_state="UNKNOWN")
        self.assertEqual(v["status"], "HOLD_SESSION_LOAD_STATE_UNKNOWN")
        self.assertIsNone(v["predicted_type"])

    def test_path_qualified_syntax_not_covered_by_precedence(self):
        v = held.finite_loaded_command_resolution(
            ("Alias", "Application"), path_qualified=True)
        self.assertEqual(v["status"], "HOLD_PATH_QUALIFIED_DIFFERENT_RULE")
        self.assertIsNone(v["predicted_type"])

    def test_requested_type_missing_must_hold(self):
        v = held.finite_loaded_command_resolution(
            ("Alias",), requested_type="Cmdlet")
        self.assertEqual(v["status"], "HOLD_NO_MATCHING_COMMAND_TYPE")
        self.assertIsNone(v["predicted_type"])

    def test_app_only_and_explicit_function_are_distinct(self):
        app = held.finite_loaded_command_resolution(("Application",))
        func = held.finite_loaded_command_resolution(
            ("Function", "Alias"), requested_type="Function")
        self.assertEqual(app["status"], "ONLY_APPLICATION_DISCOVERED")
        self.assertEqual(func["status"], "EXPLICIT_TYPE_CONTRACT_FOUND")

    def test_no_host_io_or_rights_claims(self):
        x = held.build_heldout_hypothesis()
        output = held.evaluate_heldout_hypothesis(x)
        for field in ("model_trained", "auto_promoted", "published",
                      "export_allowed", "license_redistribution_approved",
                      "owner_host_tested"):
            self.assertFalse(x[field], field)
        self.assertEqual(x["rights"], "NOT_APPROVED")
        self.assertEqual(x["independent_qa"], "NOT_VERIFIED")
        for field in (
            "native_powershell_run", "independent_upstream_qa_verified",
            "customer_session_examined", "general_autonomous_semantic_discovery_proven",
            "human_rights_security_released", "customer_export_authorized",
            "auto_promoted", "model_trained",
        ):
            self.assertFalse(output[field], field)
        self.assertEqual(output["operating_database_writes"], 0)
        self.assertEqual(output["network_requests"], 0)

    def test_unsupported_or_oversized_input_rejected(self):
        for candidates in (
            (), ("Alias", "Alias"), ("Alias", "Cmdlet", "Function",
                                    "Application", "Filter"),
            ("NotACommandType",), ("Alias", None), ["Alias"], {"Alias"},
            "Alias", 1, True, None,
        ):
            with self.subTest(value=repr(candidates)):
                with self.assertRaises(held.HeldoutPowerShellError):
                    held.finite_loaded_command_resolution(candidates)

    def test_invalid_requested_type_rejected(self):
        for requested in ("", "Script", "alias", 1, True, [], {}):
            with self.subTest(requested=repr(requested)):
                with self.assertRaises(held.HeldoutPowerShellError):
                    held.finite_loaded_command_resolution(
                        ("Cmdlet",), requested_type=requested)

    def test_invalid_load_state_and_path_type_rejected(self):
        for state in ("AUTOLOAD", "UNKNOWN_NOT_APPROVED", False, None, 1):
            with self.subTest(state=repr(state)):
                with self.assertRaises(held.HeldoutPowerShellError):
                    held.finite_loaded_command_resolution(
                        ("Cmdlet",), load_state=state)
        for path in (None, 0, 1, "false", []):
            with self.subTest(path=repr(path)):
                with self.assertRaises(held.HeldoutPowerShellError):
                    held.finite_loaded_command_resolution(
                        ("Cmdlet",), path_qualified=path)

    def test_untrusted_hypothesis_and_forged_approval_rejected(self):
        x = held.build_heldout_hypothesis()
        for field, forged in (
            ("rights", "APPROVED"),
            ("export_allowed", True),
            ("independent_qa", "VERIFIED"),
            ("owner_host_tested", True),
            ("model_trained", True),
            ("auto_promoted", True),
            ("published", True),
            ("content_sha256", "0" * 64),
            ("parent_content_sha256", "0" * 64),
            ("network_requests", 1),
        ):
            with self.subTest(field=field):
                v = deepcopy(x)
                v[field] = forged
                with self.assertRaises(held.HeldoutPowerShellError):
                    held.evaluate_heldout_hypothesis(v)

    def test_unapproved_source_and_license_replacement_rejected(self):
        x = held.build_heldout_hypothesis()
        for field in ("repo", "tag_commit_sha", "source_blob_sha",
                      "official_command_precedence_document",
                      "license_blob_sha"):
            with self.subTest(field=field):
                v = deepcopy(x)
                v["source"][field] = "https://unapproved.invalid/source"
                with self.assertRaises(held.HeldoutPowerShellError):
                    held.evaluate_heldout_hypothesis(v)

    def test_forged_parent_hypothesis_fails_closed(self):
        from ucie_miner import ucie_v2_generalization_transfer_v01 as b4
        legitimate = b4.build_hypothesis()
        changed = {**legitimate, "export_allowed": True}
        with mock.patch.object(b4, "build_hypothesis", return_value=changed):
            with self.assertRaises(held.HeldoutPowerShellError):
                held.build_heldout_hypothesis()

    def test_forged_local_b2_synthetic_success_fails_closed(self):
        from ucie_miner import local_b2_connected_workbench_v01 as workbench
        actual = workbench.evaluate_case
        def forged(case, scenario):
            output = actual(case, scenario)
            if case == "powershell-command" and scenario == "issue":
                output["human_review_approved"] = True
            return output
        with mock.patch.object(workbench, "evaluate_case", side_effect=forged):
            with self.assertRaises(held.HeldoutPowerShellError):
                held.build_heldout_hypothesis()

    def test_no_outside_source_via_injected_parent_skillbook(self):
        from ucie_miner import ucie_v2_generalization_transfer_v01 as b4
        original = b4.build_hypothesis()
        forged = deepcopy(original)
        forged["parents"].append({"source_id": "repo:unapproved"})
        with mock.patch.object(b4, "build_hypothesis", return_value=forged):
            with self.assertRaises(held.HeldoutPowerShellError):
                held.build_heldout_hypothesis()


if __name__ == "__main__":
    import unittest
    unittest.main()
