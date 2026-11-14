"""Standing UCIE policies: offline ephemeral signer, never operational."""
from copy import deepcopy
from datetime import datetime, timezone
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ucie_public.policy import PolicyError
from ucie_public.rulepack import canonical_json
from ucie_public.unattended_standing_policy import (
    SCHEMA, GIT_SCOPE, verify_standing_ucie_policy,
    preview_standing_git_publish, preview_standing_c40_recovery,
)
from ucie_public.unattended_c40_supervisor import decide_c40_recovery_need

NOW = datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)
EPOCH = "a"*64


def policy(purpose="GITHUB_DRAFT_PUBLISH"):
    return {
        "schema": SCHEMA, "project_id": "UCIE",
        "audience": "UCIE_OWNER_ONLY",
        "policy_id": "UCIE-POLICY-TEST-20261023",
        "sequence": 7, "purpose": purpose,
        "target": ("tmdrkdtn1-project/UCIE" if purpose == "GITHUB_DRAFT_PUBLISH"
                   else "UCIE_C40_TUNNEL"),
        "issued_at": "2026-10-23T09:00:00Z",
        "expires_at": ("2026-10-29T09:00:00Z" if purpose == "GITHUB_DRAFT_PUBLISH"
                       else "2026-11-20T09:00:00Z"),
        "external_revocation_epoch_sha256": EPOCH,
        "scope": (deepcopy(GIT_SCOPE) if purpose == "GITHUB_DRAFT_PUBLISH"
                  else {"binary_sha256": "b"*64, "profile_sha256": "c"*64,
                        "max_restarts_per_hour": 2, "max_restarts_per_day": 4,
                        "cooldown_minutes": 20, "new_tunnel_allowed": False}),
    }


class StandingUCIEPolicyTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.pub = self.key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo)

    def inspect(self, obj=None, *, epoch=EPOCH, sequence=6, at=NOW):
        raw = canonical_json(obj if obj is not None else policy())
        return verify_standing_ucie_policy(
            raw, self.key.sign(raw), self.pub,
            external_epoch_sha256=epoch,
            last_policy_sequence=sequence, at_time=at)

    def test_git_policy_limited_to_draft_pr_no_merge(self):
        result = self.inspect()
        self.assertFalse(result["auto_merge_authorized"])
        self.assertFalse(result["auto_rule_promotion_authorized"])
        self.assertFalse(result["operation_executed"])
        draft = preview_standing_git_publish(
            result, ["src/ucie_public/new.py", "tests/test_new.py"],
            prs_today=2, approved_ci=True)
        self.assertTrue(draft["draft_only"])
        self.assertFalse(draft["automatic_merge"])
        self.assertFalse(draft["main_push"])
        for paths, count, ci in (
            (["scripts/launch.ps1"], 0, True),
            ([".github/workflows/unsafe.yml"], 0, True),
            (["docs/secret.md"], 0, True),
            (["docs/safe.md"], 3, True),
            (["docs/safe.md"], 1, False),
        ):
            with self.subTest(paths=paths, count=count), self.assertRaises(PolicyError):
                preview_standing_git_publish(result, paths, prs_today=count, approved_ci=ci)

    def test_c40_policy_never_authorizes_new_tunnel(self):
        result = self.inspect(policy("C40_AUTORECOVERY"))
        readings = [
            {"observed_at": "2026-10-23T09:57:00Z", "c40_process_count": 1,
             "client_binary_and_profile_match": True, "process_owner_verified": True,
             "mcp_initialize_ok": True, "tools_list_ok": True,
             "legacy_library_search_ok": False, "admin_capabilities_ok": False},
            {"observed_at": "2026-10-23T09:59:00Z", "c40_process_count": 1,
             "client_binary_and_profile_match": True, "process_owner_verified": True,
             "mcp_initialize_ok": True, "tools_list_ok": True,
             "legacy_library_search_ok": False, "admin_capabilities_ok": False},
        ]
        state = decide_c40_recovery_need(readings, {
            "restarts_last_hour": 0, "last_restart_utc": None,
            "supervisor_lock_held": True, "scheduler_miner_idle": True,
            "external_rollback_anchor_ok": True,
        }, at_time=NOW)
        inspected = preview_standing_c40_recovery(result, state, restarts_last_day=3)
        self.assertFalse(inspected["service_restarted"])
        self.assertFalse(inspected["new_tunnel_registered"])
        with self.assertRaises(PolicyError):
            preview_standing_c40_recovery(result, state, restarts_last_day=4)

    def test_revoke_by_external_epoch_mismatch_or_rollback(self):
        with self.assertRaises(PolicyError):
            self.inspect(epoch="b"*64)
        with self.assertRaises(PolicyError):
            self.inspect(sequence=7)
        with self.assertRaises(PolicyError):
            self.inspect(at=datetime(2026, 12, 1, tzinfo=timezone.utc))

    def test_cannot_turn_standing_policy_into_arbitrary_execution(self):
        for key, val in (
            ("project_id", "FOREIGN"),
            ("purpose", "GITHUB_AUTO_MERGE"),
            ("audience", "SHARED"),
            ("target", "not-this-repo"),
            ("expires_at", "2030-01-01T00:00:00Z"),
            ("scope", {"auto_merge": True}),
            ("sequence", True),
        ):
            item = policy()
            item[key] = val
            with self.subTest(key=key), self.assertRaises(PolicyError):
                self.inspect(item)
        other = policy("C40_AUTORECOVERY")
        other["scope"]["new_tunnel_allowed"] = True
        with self.assertRaises(PolicyError):
            self.inspect(other)
        with self.assertRaises(PolicyError):
            preview_standing_git_publish(self.inspect(policy("C40_AUTORECOVERY")),
                                         ["tests/safe.py"], prs_today=0, approved_ci=True)


if __name__ == "__main__":
    unittest.main()
