"""Offline UCIE-only signed unattended-operation gate regressions.

Synthetic ephemeral Ed25519 keys and observations only. No owner key, Git
push, Windows process, scheduler, credential, tunnel, Rulepack or DB access.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ucie_public.policy import PolicyError
from ucie_public.rulepack import canonical_json
from ucie_public.unattended_ops import (
    REPO, SCHEMA, preview_c40_recovery, preview_git_branch_publish,
    preview_rule_shadow, verify_owner_operation_grant,
)

NOW = datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)
SHA = "a" * 40


def grant_payload(op="GIT_BRANCH_PUBLISH"):
    return {
        "schema": SCHEMA,
        "project_id": "UCIE",
        "audience": "UCIE_OWNER_ONLY",
        "operation": op,
        "target": {
            "GIT_BRANCH_PUBLISH": REPO,
            "C40_RECOVERY": "UCIE_C40_TUNNEL",
            "RULE_SHADOW_REVIEW": "UCIE_PUBLIC_RULE_SHADOW",
        }[op],
        "task_id": "UCIE-P0-TEST-20261023",
        "sequence": 11,
        "nonce": "a" * 32,
        "revision_sha": SHA,
        "issued_at": "2026-10-23T09:59:00Z",
        "expires_at": "2026-10-23T10:09:00Z",
    }


def git_observed():
    return {
        "repository": REPO,
        "base_sha": SHA,
        "branch": "automation/ucie-safe-test-20261023",
        "changed_paths": ["src/ucie_public/sample.py", "tests/test_sample.py"],
        "root_is_ucie": True,
        "worktree_clean_before_edit": True,
        "all_paths_regular_nonlinks": True,
        "protected_paths_unchanged": True,
        "secrets_scan_passed": True,
        "offline_tests_passed": True,
        "remote_owner_verified": True,
        "branch_nonexistent": True,
        "credentials_owner_scoped": True,
    }


def recovery_observed():
    return {
        "service_identity": "UCIE_C40_TUNNEL",
        "exact_binary_and_profile_sha_match": True,
        "owner_process_identity_verified": True,
        "single_owner_lock_held": True,
        "functional_mcp_probe_failed": True,
        "old_process_exited": True,
        "active_miner_jobs_zero": True,
        "cooldown_elapsed": True,
        "prior_attempts": 0,
    }


class UCIEUnattendedGateTests(unittest.TestCase):
    def setUp(self):
        self.signer = Ed25519PrivateKey.generate()
        self.trust = self.signer.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo)

    def verified(self, payload=None, *, last=10, at=NOW):
        raw = canonical_json(payload or grant_payload())
        return verify_owner_operation_grant(
            raw, self.signer.sign(raw), self.trust,
            last_consumed_sequence=last, at_time=at)

    def test_owner_signed_git_preflight_never_pushes(self):
        g = self.verified()
        self.assertFalse(g["operation_executed"])
        self.assertFalse(g["durable_replay_claim_performed"])
        result = preview_git_branch_publish(g, git_observed())
        self.assertEqual(result["status"], "UCIE_GIT_PREFLIGHT_READY_NO_PUSH")
        self.assertFalse(result["git_push_performed"])
        self.assertFalse(result["git_commit_performed"])
        self.assertFalse(result["production_deployed"])
        self.assertTrue(result["os_durable_replay_claim_required"])

    def test_all_operations_gated_and_nonexecuting(self):
        c = preview_c40_recovery(self.verified(grant_payload("C40_RECOVERY")),
                                 recovery_observed())
        self.assertEqual(c["status"], "UCIE_C40_RESTART_PREFLIGHT_READY_NO_RESTART")
        self.assertFalse(c["restart_performed"])
        self.assertFalse(c["functional_recovery_verified"])
        shadow = preview_rule_shadow(self.verified(grant_payload("RULE_SHADOW_REVIEW")))
        self.assertEqual(shadow["automatic_rule_promotions"], 0)
        self.assertFalse(shadow["rulepack_signed"])

    def test_wrong_signature_key_and_message_fail_closed(self):
        raw = canonical_json(grant_payload())
        sig = self.signer.sign(raw)
        foreign = Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        for payload, signature, key in (
            (raw, b"x" * 64, self.trust),
            (raw, sig, foreign),
            (raw + b"x", sig, self.trust),
        ):
            with self.subTest(payload=payload[-6:], key_match=key == self.trust):
                with self.assertRaises(PolicyError):
                    verify_owner_operation_grant(
                        payload, signature, key,
                        last_consumed_sequence=10, at_time=NOW)

    def test_canonical_field_and_project_scope_rejected(self):
        for key, val in (
            ("project_id", "FOREIGN"),
            ("audience", "SHARED"),
            ("target", "another/repo"),
            ("operation", "RUN_SHELL"),
            ("revision_sha", "x" * 40),
            ("nonce", "../secret"),
            ("task_id", "WRONG"),
            ("sequence", True),
            ("expires_at", "2026-10-23T10:30:00Z"),
        ):
            item = grant_payload()
            item[key] = val
            with self.subTest(key=key), self.assertRaises(PolicyError):
                self.verified(item)
        item = grant_payload()
        item["command"] = "powershell -c unrestricted"
        with self.assertRaises(PolicyError):
            self.verified(item)
        raw = b'{"schema":"x","schema":"x"}'
        with self.assertRaises(PolicyError):
            verify_owner_operation_grant(raw, self.signer.sign(raw), self.trust,
                                         last_consumed_sequence=10, at_time=NOW)

    def test_rollback_and_grant_time_gates(self):
        with self.assertRaises(PolicyError):
            self.verified(last=11)
        with self.assertRaises(PolicyError):
            self.verified(at=NOW + timedelta(hours=1))
        with self.assertRaises(PolicyError):
            self.verified(at=NOW - timedelta(hours=1))
        with self.assertRaises(PolicyError):
            self.verified(last=True)
        with self.assertRaises(PolicyError):
            self.verified(at=NOW.replace(tzinfo=None))

    def test_foreign_paths_and_secrets_and_protected_files_blocked(self):
        paths = (
            ["../other_project/main.py"],
            ["src/ucie_public/../../something.py"],
            [".github/workflows/ci.yml"],
            ["src/ucie_public/.env"],
            ["src/ucie_public/github_token.py"],
            ["src/ucie_public/secret.json"],
            ["src/ucie_public/x.py", "src/ucie_public/x.py"],
            ["src/ucie_public/x.exe"],
            ["src/ucie_public/x.py" + "\x00"],
            ["src\\ucie_public\\test.py"],
        )
        for changed in paths:
            obs = git_observed()
            obs["changed_paths"] = changed
            with self.subTest(paths=changed), self.assertRaises(PolicyError):
                preview_git_branch_publish(self.verified(), obs)

    def test_other_branch_dirty_worktree_or_unapproved_checks_rejected(self):
        for key, val in (
            ("repository", "outside/repo"),
            ("base_sha", "b" * 40),
            ("branch", "main"),
            ("branch", "automation/ucie-../../main"),
            ("worktree_clean_before_edit", False),
            ("root_is_ucie", False),
            ("secrets_scan_passed", False),
            ("offline_tests_passed", False),
            ("all_paths_regular_nonlinks", False),
            ("credentials_owner_scoped", False),
            ("branch_nonexistent", False),
        ):
            obs = git_observed()
            obs[key] = val
            with self.subTest(key=key), self.assertRaises(PolicyError):
                preview_git_branch_publish(self.verified(), obs)
        with self.assertRaises(PolicyError):
            preview_git_branch_publish({}, git_observed())

    def test_recovery_requires_functional_failure_and_single_owner(self):
        for key, val in (
            ("service_identity", "OTHER_TUNNEL"),
            ("functional_mcp_probe_failed", False),
            ("old_process_exited", False),
            ("cooldown_elapsed", False),
            ("single_owner_lock_held", False),
            ("exact_binary_and_profile_sha_match", False),
            ("prior_attempts", 2),
            ("prior_attempts", True),
        ):
            obs = recovery_observed()
            obs[key] = val
            with self.subTest(key=key), self.assertRaises(PolicyError):
                preview_c40_recovery(self.verified(grant_payload("C40_RECOVERY")), obs)
        with self.assertRaises(PolicyError):
            preview_c40_recovery(self.verified(), recovery_observed())
        with self.assertRaises(PolicyError):
            preview_rule_shadow(self.verified())

    def test_overlong_envelopes_and_unknown_fields(self):
        raw = b"x" * 2049
        with self.assertRaises(PolicyError):
            verify_owner_operation_grant(raw, self.signer.sign(raw), self.trust,
                                         last_consumed_sequence=10, at_time=NOW)
        obs = git_observed()
        obs["shell_command"] = "git -c secret=value push"
        with self.assertRaises(PolicyError):
            preview_git_branch_publish(self.verified(), obs)


if __name__ == "__main__":
    unittest.main()
