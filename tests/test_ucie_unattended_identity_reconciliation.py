"""Synthetic UCIE owner identity / separate journal / Bridge ACL gate tests."""
from copy import deepcopy
import json
import unittest

from ucie_public.policy import PolicyError
from ucie_public.unattended_identity_reconciliation import (
    OPS_PATH, assess_owner_identity_acl_v2, parse_owner_identity_acl_v2,
)


def acl(*, exists=False, readable=False, owner=False, admin=False,
        inherited=True, broad=False, review=True):
    return {
        "exists_unlinked": exists,
        "acl_readable": readable,
        "owned_by_current_user": owner,
        "owner_is_builtin_administrators": admin,
        "owner_is_local_system": False,
        "inheritance_disabled": not inherited,
        "broad_allow_write_ace_found": broad,
        "acl_requires_owner_review": review,
    }


def report():
    return {
        "schema": "UCIE_WINDOWS_IDENTITY_ACL_READONLY_DIAGNOSTIC_V2",
        "project_id": "UCIE",
        "status": "DIAGNOSTIC_OBSERVATION_ONLY_NOT_HOST_APPROVAL",
        "root_exists_and_no_reparse_ancestors": True,
        "miner_task_present": True,
        "miner_task_account_sid_resolvable": True,
        "miner_task_sid_matches_current_user": True,
        "miner_task_logon_type": "Interactive",
        "miner_task_run_level": "Limited",
        "miner_task_state": "Ready",
        "supervisor_task_name_occupied": False,
        "existing_bridge_directory": acl(
            exists=True, readable=True, admin=True, inherited=True,
            broad=True, review=True),
        "proposed_independent_operations_directory": acl(),
        "private_owner_key_provisioned_or_read": False,
        "windows_acl_modified": False,
        "existing_bridge_files_modified": False,
        "scheduled_task_modified": False,
        "service_restarted": False,
        "github_push_performed": False,
        "production_rule_promoted": False,
        "operator_install_authorized": False,
    }


class UCIEIdentityReconciliationTests(unittest.TestCase):
    def test_actual_shape_owner_principal_matches_and_bridge_acl_is_risk(self):
        result = assess_owner_identity_acl_v2(report())
        self.assertEqual(result["status"],
                         "UCIE_OWNER_IDENTITY_CONFIRMED_SEPARATE_JOURNAL_SETUP_PENDING")
        self.assertTrue(result["existing_miner_task_sid_matches_current_user"])
        self.assertEqual(result["existing_admin_bridge_state"],
                         "OWNER_REVIEW_REQUIRED_POTENTIALLY_BROAD_WRITE")
        self.assertEqual(result["operations_journal_path"], OPS_PATH)
        self.assertFalse(result["operations_journal_present"])
        self.assertFalse(result["existing_admin_bridge_acl_modified"])
        self.assertFalse(result["windows_host_install_approved"])
        self.assertFalse(result["automatic_rule_promotion_activated"])

    def test_unmatched_identity_and_existing_supervisor_are_hold(self):
        for key, value, expected in (
            ("miner_task_sid_matches_current_user", False,
             "UCIE_OWNER_IDENTITY_OR_MINER_TASK_HOLD_NO_INSTALL"),
            ("miner_task_account_sid_resolvable", False,
             "UCIE_OWNER_IDENTITY_OR_MINER_TASK_HOLD_NO_INSTALL"),
            ("miner_task_run_level", "Highest",
             "UCIE_OWNER_IDENTITY_OR_MINER_TASK_HOLD_NO_INSTALL"),
            ("miner_task_logon_type", "S4U",
             "UCIE_OWNER_IDENTITY_OR_MINER_TASK_HOLD_NO_INSTALL"),
            ("supervisor_task_name_occupied", True,
             "UCIE_SUPERVISOR_NAME_OCCUPIED_NO_INSTALL"),
        ):
            test = report()
            test[key] = value
            with self.subTest(key=key):
                self.assertEqual(assess_owner_identity_acl_v2(test)["status"], expected)

    def test_existing_bridge_acl_is_never_assumed_ops_journal(self):
        test = report()
        test["existing_bridge_directory"]["owned_by_current_user"] = True
        test["existing_bridge_directory"]["inheritance_disabled"] = True
        test["existing_bridge_directory"]["broad_allow_write_ace_found"] = False
        test["existing_bridge_directory"]["acl_requires_owner_review"] = False
        v = assess_owner_identity_acl_v2(test)
        self.assertFalse(v["operations_journal_present"])
        self.assertEqual(v["existing_admin_bridge_state"],
                         "NO_BROAD_WRITE_OBSERVED_IN_V2")

    def test_proposed_existing_journal_requires_owner_only_acl(self):
        test = report()
        test["proposed_independent_operations_directory"] = acl(
            exists=True, readable=True, owner=True,
            inherited=False, broad=False, review=False)
        result = assess_owner_identity_acl_v2(test)
        self.assertEqual(result["status"],
                         "UCIE_JOURNAL_ACL_OBSERVED_INDEPENDENT_SECURITY_GATES_PENDING")
        self.assertFalse(result["external_antirollback_anchor_verified"])
        test["proposed_independent_operations_directory"]["broad_allow_write_ace_found"] = True
        self.assertEqual(assess_owner_identity_acl_v2(test)["status"],
                         "UCIE_SEPARATE_JOURNAL_ACL_UNTRUSTED_NO_INSTALL")

    def test_broken_claims_foreign_project_and_invalid_acl_are_rejected(self):
        for key, value in (
            ("project_id", "FOREIGN"),
            ("private_owner_key_provisioned_or_read", True),
            ("operator_install_authorized", True),
            ("production_rule_promoted", True),
            ("github_push_performed", True),
            ("windows_acl_modified", True),
            ("miner_task_sid_matches_current_user", "true"),
            ("miner_task_logon_type", "Invented"),
        ):
            test = report()
            test[key] = value
            with self.subTest(key=key), self.assertRaises(PolicyError):
                assess_owner_identity_acl_v2(test)
        test = report()
        test["proposed_independent_operations_directory"]["owned_by_current_user"] = True
        with self.assertRaises(PolicyError):
            assess_owner_identity_acl_v2(test)
        test = report()
        test["existing_bridge_directory"]["secret_file"] = "unexpected"
        with self.assertRaises(PolicyError):
            assess_owner_identity_acl_v2(test)

    def test_json_duplicates_and_oversize_denied(self):
        clean = json.dumps(report(), separators=(",", ":")).encode("utf-8")
        self.assertTrue(parse_owner_identity_acl_v2(clean)["operations_journal_install_proposed"])
        for invalid in (
            b'{"project_id":"UCIE","project_id":"foreign"}',
            clean[:-1] + b',"project_id":"UCIE"}',
            clean + b"x",
            clean + b" " * 8000,
            b"[]",
        ):
            with self.subTest(blob=invalid[:28]), self.assertRaises(PolicyError):
                parse_owner_identity_acl_v2(invalid)


if __name__ == "__main__":
    unittest.main()
