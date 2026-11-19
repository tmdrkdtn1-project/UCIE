"""UCIE signed GitHub publisher wire contract; synthetic only."""
from datetime import datetime, timezone
import hashlib
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ucie_public.policy import PolicyError
from ucie_public.rulepack import canonical_json
from ucie_public.unattended_github import (
    MANIFEST_SCHEMA, verify_signed_publish_bundle,
    plan_github_publish, simulate_github_publish, GH_API_REPO,
)
from ucie_public.unattended_ops import SCHEMA, REPO

NOW = datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)
BASE = "a" * 40
TREE = "b" * 40
BRANCH = "automation/ucie-safe-patch-20261023"
FILES = {
    "src/ucie_public/safe_module.py": b'"""A bounded UCIE sample."""\nOK = True\n',
    "tests/test_safe_module.py": b'import unittest\n\nclass Test(unittest.TestCase):\n    pass\n',
}


def grant():
    return {
        "schema": SCHEMA, "project_id": "UCIE",
        "audience": "UCIE_OWNER_ONLY", "operation": "GIT_BRANCH_PUBLISH",
        "target": REPO, "task_id": "UCIE-PUBLISH-TEST-20261023",
        "sequence": 23, "nonce": "c" * 32, "revision_sha": BASE,
        "issued_at": "2026-10-23T09:59:00Z",
        "expires_at": "2026-10-23T10:09:00Z",
    }


def manifest(g, files=FILES):
    return {
        "schema": MANIFEST_SCHEMA, "task_id": g["task_id"],
        "grant_sha256": hashlib.sha256(canonical_json(g)).hexdigest(),
        "repository": REPO, "base_sha": BASE, "branch": BRANCH,
        "files_sha256": {p: hashlib.sha256(b).hexdigest() for p, b in files.items()},
        "commit_message": "ucie(automation): stage synthetic bounded safe source",
        "pr_title": "UCIE automation: synthetic safe code review",
    }


class FakeTransport:
    ucie_synthetic_only = True

    def __init__(self):
        self.calls = []
        self.collision = False
        self.main_sha = BASE
        self.malformed = None

    def __call__(self, method, path, body):
        self.calls.append((method, path, body))
        if self.malformed == (method, path):
            return {"invalid": True}
        if method == "GET" and path == GH_API_REPO + "/git/ref/heads/main":
            return {"ref": "refs/heads/main", "object": {"sha": self.main_sha}}
        if method == "GET" and path == GH_API_REPO + "/git/commits/" + BASE:
            return {"tree": {"sha": TREE}}
        if method == "GET" and path == GH_API_REPO + "/git/ref/heads/" + BRANCH:
            return {"http_status": 200 if self.collision else 404}
        if method == "POST" and path == GH_API_REPO + "/git/blobs":
            return {"sha": "d" * 40}
        if method == "POST" and path == GH_API_REPO + "/git/trees":
            return {"sha": "e" * 40}
        if method == "POST" and path == GH_API_REPO + "/git/commits":
            return {"sha": "f" * 40}
        if method == "POST" and path == GH_API_REPO + "/git/refs":
            return {"ref": "refs/heads/" + BRANCH, "object": {"sha": "f" * 40}}
        if method == "POST" and path == GH_API_REPO + "/pulls":
            return {
                "number": 101, "draft": True,
                "base": {"ref": "main"}, "head": {"ref": BRANCH},
            }
        raise AssertionError("not an approved UCIE GitHub endpoint: " + path)


class GitHubPublisherTests(unittest.TestCase):
    def setUp(self):
        self.owner = Ed25519PrivateKey.generate()
        self.pub = self.owner.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)

    def bound(self, g=None, m=None, files=FILES):
        g = grant() if g is None else g
        m = manifest(g, files) if m is None else m
        gb = canonical_json(g)
        mb = canonical_json(m)
        return verify_signed_publish_bundle(
            gb, self.owner.sign(gb), mb, self.owner.sign(mb),
            self.pub, files, last_consumed_sequence=22, at_time=NOW)

    def test_exact_signed_bundle_and_staged_wire_contract(self):
        verified = self.bound()
        obs = {
            "repository": REPO, "remote_main_sha": BASE,
            "remote_main_tree_sha": TREE, "branch_exists": False,
            "ci_matrix_green": True, "owner_credentials_scoped": True,
            "secrets_scan_clean": True, "protected_paths_unchanged": True,
        }
        plan = plan_github_publish(verified, observed=obs)
        self.assertEqual(plan["status"], "UCIE_GITHUB_PUBLISH_PLAN_ONLY_NO_REMOTE_MUTATION")
        self.assertFalse(plan["remote_write_performed"])
        t = FakeTransport()
        result = simulate_github_publish(verified, FILES, t)
        self.assertEqual(result["status"], "UCIE_SYNTHETIC_GITHUB_PUBLISH_SEQUENCE_ONLY")
        self.assertFalse(result["remote_write_verified"])
        self.assertEqual([x[0] for x in t.calls], ["GET"] * 3 + ["POST"] * 6)
        ref = next(x[2] for x in t.calls if x[1].endswith("/git/refs"))
        self.assertEqual(ref["ref"], "refs/heads/" + BRANCH)
        post_pr = t.calls[-1][2]
        self.assertEqual(post_pr["base"], "main")
        self.assertTrue(post_pr["draft"])
        self.assertNotIn("token", str(t.calls).casefold())

    def test_manifest_tamper_and_grant_change_blocked(self):
        for change in (
            {"branch": "main"},
            {"branch": "automation/ucie-../../foreign"},
            {"repository": "other/repo"},
            {"base_sha": "b" * 40},
            {"task_id": "UCIE-FAKE-TASK"},
            {"grant_sha256": "e" * 64},
            {"pr_title": "External PR"},
            {"commit_message": "arbitrary shell\ncode"},
            {"files_sha256": {}},
        ):
            m = manifest(grant())
            m.update(change)
            with self.subTest(change=change), self.assertRaises(PolicyError):
                self.bound(m=m)

    def test_content_hash_and_filename_restrictions(self):
        with self.assertRaises(PolicyError):
            self.bound(m=manifest(grant()), files={**FILES, "src/ucie_public/safe_module.py": b"modified"})
        for path in ("../secret.py", ".github/workflows/ci.yml",
                     "src/ucie_public/.env", "src/ucie_public/x.exe",
                     "src/ucie_public/private_token.py",
                     "src\\ucie_public\\bad.py"):
            files = {path: b"harmless"}
            with self.subTest(path=path), self.assertRaises(PolicyError):
                self.bound(files=files)
        with self.assertRaises(PolicyError):
            self.bound(files={"src/ucie_public/a.py": b"a" * 65537})
        with self.assertRaises(PolicyError):
            self.bound(files={"src/ucie_public/a.py": b"\xff"})

    def test_expired_owner_approval_no_publisher_rights(self):
        gb = canonical_json(grant())
        mb = canonical_json(manifest(grant()))
        with self.assertRaises(PolicyError):
            verify_signed_publish_bundle(
                gb, self.owner.sign(gb), mb, self.owner.sign(mb), self.pub, FILES,
                last_consumed_sequence=23, at_time=NOW)
        with self.assertRaises(PolicyError):
            verify_signed_publish_bundle(
                gb, self.owner.sign(gb), mb, b"x" * 64, self.pub, FILES,
                last_consumed_sequence=22, at_time=NOW)

    def test_remote_race_and_collision_never_create_blob(self):
        v = self.bound()
        for key in ("main_sha", "collision"):
            t = FakeTransport()
            if key == "main_sha":
                t.main_sha = "b" * 40
            else:
                t.collision = True
            with self.assertRaises(PolicyError):
                simulate_github_publish(v, FILES, t)
            self.assertFalse(any(method == "POST" for method, _, _ in t.calls))

    def test_publisher_refuses_modified_bytes_before_transport(self):
        v = self.bound()
        fake = FakeTransport()
        altered = {**FILES, "tests/test_safe_module.py": b"changed"}
        with self.assertRaises(PolicyError):
            simulate_github_publish(v, altered, fake)
        self.assertEqual(fake.calls, [])
        with self.assertRaises(PolicyError):
            simulate_github_publish(v, FILES, lambda m,p,b: {})

    def test_publisher_does_not_claim_live_ci_or_actual_git_push(self):
        v = self.bound()
        self.assertFalse(v["remote_branch_published"])
        self.assertFalse(v["owner_host_credential_verified"])
        self.assertFalse(v["external_rollback_anchor_verified"])
        t = FakeTransport()
        simulate_github_publish(v, FILES, t)
        self.assertTrue(all(p.startswith(GH_API_REPO + "/") for _, p, _ in t.calls))


if __name__ == "__main__":
    unittest.main()
