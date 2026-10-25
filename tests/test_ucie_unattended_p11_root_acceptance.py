"""UCIE P11: owner-created root evidence is NOT a service release."""
import json
import unittest

from ucie_public.policy import PolicyError
from ucie_public.unattended_p11_root_acceptance import (
    assess_p10_owner_root, parse_p10_owner_root,
    OWNER_OBSERVATION_STATUS, REJECTION_STATUS,
)


def owner_p10_created():
    return {
        "schema": "UCIE_ONE_OWNER_PROTECTED_ROOT_BOOTSTRAP_P10_V1",
        "project_id": "UCIE",
        "status": "UCIE_P10_ONE_PROTECTED_DIRECTORY_CREATED_ACL_RECHECK_ONLY",
        "target_identifier": "WINDOWS_PROGRAMFILES_UCIE_UNATTENDEDHOST_ONE_ROOT",
        "parent_exists_unlinked": True,
        "parent_acl_readable": True,
        "parent_owner_well_known_system_or_administrators": True,
        "parent_dacl_canonical": True,
        "parent_foreign_mutating_allow_ace_present": False,
        "parent_foreign_inherit_only_allow_ace_present": False,
        "parent_unresolved_allow_identity": False,
        "parent_ace_identity_read_directly_as_sid": True,
        "protected_parent_preflight_passed": True,
        "caller_elevated_administrator": True,
        "target_preexisted": False,
        "target_created_this_invocation": True,
        "target_exact_admin_and_system_acl_verified": True,
        "existing_ucie_bridge_modified": False,
        "existing_ucie_miner_modified": False,
        "scheduled_task_registered": False,
        "c40_process_restarted": False,
        "github_credential_read": False,
        "git_pushed": False,
        "owner_host_signer_provisioned": False,
        "external_antireplay_anchor_provisioned": False,
        "service_writer_identity_provisioned": False,
        "rule_auto_promotion_enabled": False,
        "unattended_worker_activated": False,
    }


class P11OwnerInstallAcceptance(unittest.TestCase):
    def test_owner_exact_creation_accepted_not_auto_activation(self):
        result = assess_p10_owner_root(owner_p10_created())
        self.assertEqual(result["status"], OWNER_OBSERVATION_STATUS)
        self.assertTrue(result["owner_reported_root_created"])
        self.assertTrue(result["owner_reported_acl_exact"])
        for name in (
            "same_owner_source_claim_independently_attested",
            "post_bootstrap_independent_host_recheck",
            "protected_root_service_writer_ready", "host_signer_provisioned",
            "owner_signer_host_private_key_present",
            "external_monotonic_revocation_anchor",
            "protected_operational_journal_installed",
            "github_app_credential_verified", "c40_supervisor_registered",
            "c40_live_functional_recovery_verified",
            "automatic_git_publication_authorized", "automatic_rulepack_promotion",
            "unattended_host_go",
        ):
            with self.subTest(name=name):
                self.assertFalse(result[name])

    def test_no_go_for_each_missing_or_unapproved_fact(self):
        base = owner_p10_created()
        for field in (
            "parent_exists_unlinked", "parent_acl_readable",
            "parent_owner_well_known_system_or_administrators",
            "parent_dacl_canonical", "parent_ace_identity_read_directly_as_sid",
            "protected_parent_preflight_passed", "caller_elevated_administrator",
            "target_created_this_invocation",
            "target_exact_admin_and_system_acl_verified",
        ):
            with self.subTest(field=field):
                changed = dict(base, **{field: False})
                self.assertEqual(assess_p10_owner_root(changed)["status"], REJECTION_STATUS)
        for field in (
            "parent_foreign_mutating_allow_ace_present",
            "parent_foreign_inherit_only_allow_ace_present",
            "parent_unresolved_allow_identity", "target_preexisted",
            "existing_ucie_bridge_modified", "existing_ucie_miner_modified",
            "scheduled_task_registered", "c40_process_restarted",
            "github_credential_read", "git_pushed", "owner_host_signer_provisioned",
            "external_antireplay_anchor_provisioned",
            "service_writer_identity_provisioned",
            "rule_auto_promotion_enabled", "unattended_worker_activated",
        ):
            with self.subTest(field=field):
                changed = dict(base, **{field: True})
                self.assertEqual(assess_p10_owner_root(changed)["status"], REJECTION_STATUS)
        self.assertEqual(assess_p10_owner_root(dict(base, status="UNTRUSTED"))["status"], REJECTION_STATUS)

    def test_foreign_schema_type_extra_fields_rejected(self):
        base = owner_p10_created()
        for field, value in (
            ("project_id", "OTHER"),
            ("target_identifier", "WRONG"),
            ("target_created_this_invocation", 1),
            ("parent_acl_readable", "true"),
            ("status", None),
        ):
            with self.subTest(field=field), self.assertRaises(PolicyError):
                assess_p10_owner_root(dict(base, **{field: value}))
        extra = dict(base, unexpected="secret")
        with self.assertRaises(PolicyError):
            assess_p10_owner_root(extra)

    def test_json_duplicate_and_size_rejected(self):
        base = json.dumps(owner_p10_created(), separators=(",", ":")).encode("utf-8")
        self.assertEqual(parse_p10_owner_root(base)["status"], OWNER_OBSERVATION_STATUS)
        for bad in (
            b"[]", b"{}", b"garbage", base + b"x",
            base[:-1] + b',"project_id":"UCIE"}', base + b" " * 9000,
        ):
            with self.subTest(blob=bad[:24]), self.assertRaises(PolicyError):
                parse_p10_owner_root(bad)


if __name__ == "__main__":
    unittest.main()
