"""P9 UCIE ACL candidate closure: synthetic object + untrusted JSON tests."""
import json
import unittest

from ucie_public.policy import PolicyError
from ucie_public.unattended_protected_root_gate import (
    classify_owner_p8_candidate, parse_owner_p8_candidate,
)


def owner_report():
    return {
        "schema": "UCIE_OWNER_LOCALAPPDATA_ACE_SCOPE_READONLY_V2",
        "project_id": "UCIE",
        "status": "UCIE_FOREIGN_EFFECTIVE_DESTRUCTIVE_PARENT_RIGHTS_NO_GO",
        "target_identifier": "CURRENT_OWNER_LOCALAPPDATA_UCIE_UNATTENDED_STATE",
        "parent_exists": True,
        "parent_reparse_free": True,
        "parent_acl_readable": True,
        "parent_owned_by_current_user": True,
        "parent_acl_inheritance_enabled": True,
        "foreign_mutating_allow_count": 2,
        "foreign_mutating_inherit_only_count": 0,
        "foreign_mutating_effective_on_parent_count": 2,
        "foreign_mutating_inherited_count": 0,
        "foreign_mutating_can_inherit_to_children_count": 2,
        "foreign_effective_parent_delete_child": False,
        "foreign_effective_parent_delete": True,
        "foreign_effective_parent_change_dacl_or_owner": False,
        "foreign_effective_parent_create_child": True,
        "foreign_effective_parent_write": True,
        "foreign_broad_effective_modify": False,
        "unresolved_allow_ace_identity": False,
        "target_already_exists": False,
        "os_accesscheck_executed": False,
        "security_grant_authorized": False,
        "new_directory_created": False,
        "existing_acl_changed": False,
        "service_restarted": False,
        "git_pushed": False,
        "automatic_rule_promotion": False,
    }


class ProtectedRootGateTests(unittest.TestCase):
    def test_owner_real_shape_rejects_both_untrusted_parents(self):
        result = classify_owner_p8_candidate(owner_report())
        self.assertEqual(result["status"],
                         "UCIE_EXISTING_CANDIDATE_REJECTED_PROTECTED_ROOT_DESIGN_REQUIRED")
        self.assertEqual(result["previous_data_parent"], "UCIE_D_DATA_PARENT_REJECTED")
        self.assertEqual(result["alternative_parent"], "OWNER_LOCALAPPDATA_PARENT_REJECTED")
        self.assertTrue(result["foreign_parent_delete_allow_ace_observed"])
        self.assertFalse(result["foreign_parent_delete_child_allow_ace_observed"])
        self.assertTrue(result["parent_delete_is_not_delete_child"])
        self.assertFalse(result["foreign_effective_access_proven"])
        self.assertFalse(result["install_authorized"])
        self.assertFalse(result["additional_random_parent_probing_required"])
        for flag in (
            "protected_root_installed", "external_antirollback_anchor_verified",
            "git_automation_activated", "c40_restarted",
            "rule_auto_promotion_activated", "owner_release_grant_obtained",
        ):
            self.assertFalse(result[flag])

    def test_inherit_only_remains_no_go_not_automatically_promoted(self):
        sample = owner_report()
        sample.update({
            "status": "UCIE_FOREIGN_ACE_INHERIT_ONLY_CHILD_DACL_REVIEW_REQUIRED",
            "foreign_mutating_inherit_only_count": 2,
            "foreign_mutating_effective_on_parent_count": 0,
            "foreign_effective_parent_delete": False,
            "foreign_effective_parent_create_child": False,
            "foreign_effective_parent_write": False,
        })
        result = classify_owner_p8_candidate(sample)
        self.assertEqual(result["status"],
                         "UCIE_ALTERNATIVE_CANDIDATE_STILL_UNATTESTED_NO_GO")
        self.assertFalse(result["install_authorized"])

    def test_bad_counts_or_forged_authorization_fail_closed(self):
        for field, value in (
            ("foreign_mutating_allow_count", -1),
            ("foreign_mutating_allow_count", True),
            ("foreign_mutating_inherit_only_count", 1),
            ("foreign_mutating_inherited_count", 3),
            ("foreign_mutating_can_inherit_to_children_count", 3),
            ("os_accesscheck_executed", True),
            ("security_grant_authorized", True),
            ("new_directory_created", True),
            ("existing_acl_changed", True),
            ("git_pushed", True),
            ("automatic_rule_promotion", True),
            ("project_id", "FOREIGN"),
            ("target_identifier", "OTHER"),
            ("status", "APPROVED"),
        ):
            s = owner_report()
            s[field] = value
            with self.subTest(field=field), self.assertRaises(PolicyError):
                classify_owner_p8_candidate(s)

    def test_parse_duplicate_foreign_and_oversize_report(self):
        good = json.dumps(owner_report(), separators=(",", ":")).encode()
        self.assertFalse(parse_owner_p8_candidate(good)["install_authorized"])
        for bad in (
            good[:-1] + b',"project_id":"UCIE"}',
            good + b"junk",
            b"[]", b"{}", b"not json", good + b" " * 9000,
        ):
            with self.subTest(candidate=bad[:24]), self.assertRaises(PolicyError):
                parse_owner_p8_candidate(bad)
        extraneous = owner_report()
        extraneous["command"] = "restart"
        with self.assertRaises(PolicyError):
            classify_owner_p8_candidate(extraneous)


if __name__ == "__main__":
    unittest.main()
