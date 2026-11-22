"""UCIE-only host readiness parser synthetic fixture tests: no OS access."""
from __future__ import annotations

import json
import unittest

from ucie_public.policy import PolicyError
from ucie_public.unattended_host_readiness import (
    evaluate_ucie_host_preflight, parse_ucie_host_preflight,
)


def sample():
    return {
        "schema": "UCIE_WINDOWS_HOST_READONLY_PREFLIGHT_V1",
        "project_id": "UCIE",
        "status": "READONLY_OBSERVATION_HOST_ACTIVATION_NOT_AUTHORIZED",
        "current_user_sid_present": True,
        "root_exact_exists_and_not_linked": True,
        "git_checkout_exists": True,
        "git_origin_exact_ucie_https": True,
        "git_tracked_worktree_clean": True,
        "public_miner_file_present": True,
        "python_executable_present": True,
        "existing_hourly_miner_task_present": True,
        "existing_hourly_miner_principal_matches_current_user": True,
        "existing_hourly_miner_action_matches": True,
        "existing_hourly_miner_state": "Ready",
        "c40_exact_ucie_profile_client_pair_unique": True,
        "c40_matched_pairs_count": 1,
        "c40_profile_regular_file_present": True,
        "c40_client_regular_file_present": True,
        "c40_profile_sha256": "a" * 64,
        "c40_client_sha256": "b" * 64,
        "future_supervisor_task_name_is_already_occupied": False,
        "ucie_journal_dir_regular_and_not_linked": False,
        "ucie_journal_owner_sid_matches_current_user": False,
        "ucie_journal_acl_inheritance_disabled": False,
        "ucie_journal_broad_write_ace_denied": False,
        "owner_acl_independently_verified": False,
        "monotonic_external_anchor_verified": False,
        "short_lived_github_credential_verified": False,
        "c40_live_functional_probe_verified": False,
        "actual_host_service_installed": False,
        "service_restarted": False,
        "git_pushed": False,
        "task_registered": False,
        "automatic_rule_promotions": 0,
    }


class UCIEHostReadinessTests(unittest.TestCase):
    def test_canonical_good_observation_still_cannot_activate(self):
        v = evaluate_ucie_host_preflight(sample())
        self.assertEqual(
            v["status"], "UCIE_OWNER_HOST_OBSERVATION_CANDIDATE_BOOTSTRAP_PENDING")
        self.assertEqual(v["observation_blockers"], [])
        self.assertIn("monotonic_external_anchor_verified",
                      v["bootstrap_or_independent_acceptance_remaining"])
        self.assertFalse(v["owner_approval_obtained"])
        self.assertFalse(v["automatic_git_push_permitted"])
        self.assertFalse(v["service_restart_permitted"])
        self.assertFalse(v["automatic_rule_promotion_permitted"])

    def test_existing_wrong_git_or_duplicate_supervisor_blocks_install(self):
        for key, value in (
            ("git_origin_exact_ucie_https", False),
            ("existing_hourly_miner_principal_matches_current_user", False),
            ("existing_hourly_miner_action_matches", False),
            ("root_exact_exists_and_not_linked", False),
            ("git_tracked_worktree_clean", False),
            ("future_supervisor_task_name_is_already_occupied", True),
            ("existing_hourly_miner_state", "Disabled"),
        ):
            s = sample()
            s[key] = value
            with self.subTest(key=key):
                v = evaluate_ucie_host_preflight(s)
                self.assertEqual(v["status"],
                                 "UCIE_OWNER_HOST_OBSERVATION_BLOCKED_NO_INSTALL")
                self.assertIn(key, v["observation_blockers"])

    def test_uncertain_c40_paths_block_without_exposing_hashes(self):
        for count in (0, 2):
            s = sample()
            s.update({
                "c40_matched_pairs_count": count,
                "c40_exact_ucie_profile_client_pair_unique": False,
                "c40_client_regular_file_present": False,
                "c40_profile_regular_file_present": False,
                "c40_profile_sha256": None, "c40_client_sha256": None,
            })
            result = evaluate_ucie_host_preflight(s)
            self.assertEqual(result["status"],
                             "UCIE_OWNER_HOST_OBSERVATION_BLOCKED_NO_INSTALL")
        broken = sample()
        broken["c40_matched_pairs_count"] = 2
        with self.assertRaises(PolicyError):
            evaluate_ucie_host_preflight(broken)

    def test_attestation_or_reported_operations_cannot_be_spoofed(self):
        for field, value in (
            ("owner_acl_independently_verified", True),
            ("monotonic_external_anchor_verified", True),
            ("short_lived_github_credential_verified", True),
            ("c40_live_functional_probe_verified", True),
            ("actual_host_service_installed", True),
            ("service_restarted", True),
            ("git_pushed", True),
            ("task_registered", True),
            ("automatic_rule_promotions", 1),
            ("existing_hourly_miner_task_present", "True"),
            ("c40_profile_sha256", "incorrect"),
            ("c40_matched_pairs_count", True),
            ("schema", "UCIE_FOREIGN"),
            ("project_id", "OTHER"),
        ):
            s = sample()
            s[field] = value
            with self.subTest(field=field), self.assertRaises(PolicyError):
                evaluate_ucie_host_preflight(s)

    def test_bounded_json_duplicate_and_extra_fields_denied(self):
        good = json.dumps(sample(), separators=(",", ":")).encode("utf-8")
        parsed = parse_ucie_host_preflight(good)
        self.assertEqual(parsed["status"],
                         "UCIE_OWNER_HOST_OBSERVATION_CANDIDATE_BOOTSTRAP_PENDING")
        dup = good[:-1] + b',"project_id":"UCIE"}'
        for bad in (dup, good + b"garbage", b"[]", b"{not-json}",
                    good + b" " * 12000):
            with self.subTest(bad=bad[:35]), self.assertRaises(PolicyError):
                parse_ucie_host_preflight(bad)
        extra = sample()
        extra["service_private_key"] = "should-not-exist"
        with self.assertRaises(PolicyError):
            evaluate_ucie_host_preflight(extra)


if __name__ == "__main__":
    unittest.main()
