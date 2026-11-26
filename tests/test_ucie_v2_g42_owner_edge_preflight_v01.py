"""G4.2 source-only owner Windows Edge preflight, never host authorization."""
from __future__ import annotations

from copy import deepcopy
from unittest import TestCase

from ucie_miner import ucie_v2_g42_owner_edge_preflight_v01 as gate


def snapshot() -> dict:
    return {
        "main_sha": gate.BASE_MAIN, "g41_head_sha": gate.ISOLATED_G41_HEAD,
        "isolated_edge_ci_passed": True,
        "cross_os_source_ci_passed": True,
        "owner_worktree_dirty": True,
        "readonly_bridge_responded": True,
        "owner_v2_runtime_implemented_verified": False,
        "owner_edge_screen_acceptance_verified": False,
        "backup_rollback_for_v2_verified": False,
        "specific_owner_v2_activation_approval_authenticated": False,
    }


class G42OwnerHoldTests(TestCase):
    def test_reviewed_readonly_state_is_not_a_v2_runtime_pass(self):
        x = gate.review_owner_edge_snapshot(snapshot())
        self.assertEqual(x["schema"], gate.SCHEMA)
        self.assertEqual(x["status"], gate.STATUS)
        self.assertEqual(x["main_sha"], gate.BASE_MAIN)
        self.assertEqual(x["g41_head_sha"], gate.ISOLATED_G41_HEAD)
        self.assertEqual(x["isolated_windows_edge_qa"],
                         "CI_PASS_ON_GITHUB_RUNNER_ONLY")
        self.assertTrue(x["owner_worktree_dirty_observed"])
        self.assertFalse(x["owner_v2_runtime_implemented_verified"])
        self.assertFalse(x["owner_actual_edge_uat_accepted"])
        self.assertFalse(x["owner_v2_installation_authorized"])

    def test_all_protected_manual_gates_preserved(self):
        x = gate.review_owner_edge_snapshot(snapshot())
        self.assertEqual(x["manual_owner_gates"], list(gate.PROTECTED_GATES))
        self.assertEqual(len(x["manual_owner_gates"]), 7)
        self.assertIn("OWNER_FROZEN_V04_CSP_AND_POST_CONTRACT",
                      x["manual_owner_gates"])
        self.assertIn("OWNER_DIRTY_TREE_PRESERVATION_AND_BACKUP_ROLLBACK",
                      x["manual_owner_gates"])

    def test_no_owner_files_or_operating_db_writes(self):
        x = gate.review_owner_edge_snapshot(snapshot())
        self.assertEqual(x["owner_files_modified"], 0)
        self.assertEqual(x["operating_database_writes"], 0)
        self.assertEqual(x["network_requests"], 0)
        self.assertFalse(x["model_trained"])
        self.assertFalse(x["auto_promoted"])
        self.assertFalse(x["customer_distribution_authorized"])
        self.assertTrue(x["v04_frozen"])

    def test_unknown_or_extra_private_field_denied(self):
        for field in ("customer_code", "auth_key", "owner_name",
                      "owner_approved", "real_edge_screenshot"):
            x = snapshot()
            x[field] = "untrusted"
            with self.subTest(field=field):
                with self.assertRaises(gate.OwnerEdgePreflightError):
                    gate.review_owner_edge_snapshot(x)

    def test_missing_fields_denied(self):
        for key in snapshot():
            x = snapshot()
            x.pop(key)
            with self.subTest(key=key):
                with self.assertRaises(gate.OwnerEdgePreflightError):
                    gate.review_owner_edge_snapshot(x)

    def test_sha_drift_denied(self):
        for field in ("main_sha", "g41_head_sha"):
            x = snapshot()
            x[field] = "0" * 40
            with self.subTest(field=field):
                with self.assertRaises(gate.OwnerEdgePreflightError):
                    gate.review_owner_edge_snapshot(x)

    def test_boolean_as_integer_or_string_denied(self):
        for field in ("isolated_edge_ci_passed", "readonly_bridge_responded",
                      "owner_worktree_dirty", "owner_edge_screen_acceptance_verified"):
            for bad in (1, 0, "true", None, [], {}):
                x = snapshot()
                x[field] = bad
                with self.subTest(field=field, bad=repr(bad)):
                    with self.assertRaises(gate.OwnerEdgePreflightError):
                        gate.review_owner_edge_snapshot(x)

    def test_ci_and_bridge_prerequisites_must_be_present(self):
        for field in ("isolated_edge_ci_passed", "cross_os_source_ci_passed",
                      "readonly_bridge_responded"):
            x = snapshot()
            x[field] = False
            with self.subTest(field=field):
                with self.assertRaises(gate.OwnerEdgePreflightError):
                    gate.review_owner_edge_snapshot(x)

    def test_self_attested_owner_permission_cannot_grant_ui_pass(self):
        for field in (
            "owner_v2_runtime_implemented_verified",
            "owner_edge_screen_acceptance_verified",
            "backup_rollback_for_v2_verified",
            "specific_owner_v2_activation_approval_authenticated",
        ):
            x = snapshot()
            x[field] = True
            with self.subTest(field=field):
                with self.assertRaises(gate.OwnerEdgePreflightError):
                    gate.review_owner_edge_snapshot(x)

    def test_even_all_claims_forged_cannot_grant_activation(self):
        x = snapshot()
        for name in (
            "owner_v2_runtime_implemented_verified",
            "owner_edge_screen_acceptance_verified",
            "backup_rollback_for_v2_verified",
            "specific_owner_v2_activation_approval_authenticated",
        ):
            x[name] = True
        with self.assertRaises(gate.OwnerEdgePreflightError):
            gate.review_owner_edge_snapshot(x)

    def test_invalid_container_does_not_qualify(self):
        for value in (None, "", [], (), 0, False, True):
            with self.subTest(value=repr(value)):
                with self.assertRaises(gate.OwnerEdgePreflightError):
                    gate.review_owner_edge_snapshot(value)

    def test_dirty_tree_false_cannot_self_assert_owner_clean_state(self):
        x = snapshot()
        x["owner_worktree_dirty"] = False
        result = gate.review_owner_edge_snapshot(x)
        self.assertEqual(result["status"], gate.STATUS)
        self.assertFalse(result["owner_actual_edge_uat_accepted"])
        self.assertFalse(result["owner_v2_installation_authorized"])


if __name__ == "__main__":
    import unittest
    unittest.main()
