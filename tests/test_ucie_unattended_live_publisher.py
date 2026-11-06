"""Offline signed owner+host one-shot GitHub integration acceptance.

No real GitHub token, no network, no Windows service and no Rulepack promotion.
"""
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ucie_public.policy import PolicyError
from ucie_public.rulepack import canonical_json
from ucie_public.unattended_ops import SCHEMA as GRANT_SCHEMA
from ucie_public.unattended_github import MANIFEST_SCHEMA, GH_API_REPO
from ucie_public.unattended_live_publisher import (
    TICKET_SCHEMA, verify_signed_host_ticket, publish_one_owner_signed_draft,
)

NOW = datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)
BASE = "a" * 40
BRANCH = "automation/ucie-host-safe-20261023"
FILES = {"tests/test_ucie_draft.py": b"import unittest\n\nclass Safe(unittest.TestCase):\n    pass\n"}
TOKEN = "synthetic_ucie_token_no_network_" + "d"*24


def pem(key):
    return key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


def grant():
    return {
        "schema": GRANT_SCHEMA, "project_id": "UCIE", "audience": "UCIE_OWNER_ONLY",
        "operation": "GIT_BRANCH_PUBLISH", "target": "tmdrkdtn1-project/UCIE",
        "task_id": "UCIE-P2-PUBLISH-TEST-20261023", "sequence": 1,
        "nonce": "f"*32, "revision_sha": BASE,
        "issued_at": "2026-10-23T09:59:00Z",
        "expires_at": "2026-10-23T10:09:00Z",
    }


def manifest(g):
    return {
        "schema": MANIFEST_SCHEMA, "task_id": g["task_id"],
        "grant_sha256": hashlib.sha256(canonical_json(g)).hexdigest(),
        "repository": "tmdrkdtn1-project/UCIE", "base_sha": BASE,
        "branch": BRANCH, "files_sha256": {
            name: hashlib.sha256(data).hexdigest() for name, data in FILES.items()},
        "commit_message": "ucie(automation): stage synthetic owner approved fixture",
        "pr_title": "UCIE automation: inspect synthetic owner approved fixture",
    }


def ticket(g, m):
    return {
        "schema": TICKET_SCHEMA, "project_id": "UCIE",
        "audience": "UCIE_OWNER_ONLY", "task_id": g["task_id"],
        "grant_sha256": hashlib.sha256(canonical_json(g)).hexdigest(),
        "manifest_sha256": hashlib.sha256(canonical_json(m)).hexdigest(),
        "branch": BRANCH, "base_sha": BASE,
        "external_epoch_sha256": "b"*64, "host_sid_sha256": "c"*64,
        "issued_at": "2026-10-23T09:59:30Z",
        "expires_at": "2026-10-23T10:01:00Z",
    }


class FakeGH:
    ucie_synthetic_only = True

    def __init__(self):
        self.calls = []
        self.fail_pr = False
        self.main = BASE

    def __call__(self, method, path, data=None):
        self.calls.append((method, path, data))
        if (method, path) == ("GET", GH_API_REPO + "/git/ref/heads/main"):
            return {"ref": "refs/heads/main", "object": {"sha": self.main}}
        if (method, path) == ("GET", GH_API_REPO + "/git/commits/" + BASE):
            return {"tree": {"sha": "b"*40}}
        if (method, path) == ("GET", GH_API_REPO + "/git/ref/heads/" + BRANCH):
            return {"http_status": 404}
        if (method, path) == ("POST", GH_API_REPO + "/git/blobs"):
            return {"sha": "c"*40}
        if (method, path) == ("POST", GH_API_REPO + "/git/trees"):
            return {"sha": "d"*40}
        if (method, path) == ("POST", GH_API_REPO + "/git/commits"):
            return {"sha": "e"*40}
        if (method, path) == ("POST", GH_API_REPO + "/git/refs"):
            return {"ref": "refs/heads/" + BRANCH, "object": {"sha": "e"*40}}
        if (method, path) == ("POST", GH_API_REPO + "/pulls"):
            if self.fail_pr:
                raise PolicyError("synthetic GitHub PR creation ambiguous")
            return {"number": 120, "draft": True,
                    "head": {"ref": BRANCH}, "base": {"ref": "main"}}
        raise AssertionError("foreign GitHub endpoint") 


class OwnerHostPublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ucie_p2_host_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.owner = Ed25519PrivateKey.generate()
        self.host = Ed25519PrivateKey.generate()
        self.g, self.m = grant(), manifest(grant())
        self.t = ticket(self.g, self.m)
        self.fake = FakeGH()

    def invoke(self, *, armed=True, ticket_obj=None, fake=None, owner_pub=None,
               host_pub=None, host_sig=None):
        gb, mb = canonical_json(self.g), canonical_json(self.m)
        tb = canonical_json(self.t if ticket_obj is None else ticket_obj)
        return publish_one_owner_signed_draft(
            gb, self.owner.sign(gb), mb, self.owner.sign(mb),
            pem(self.owner) if owner_pub is None else owner_pub,
            tb, self.host.sign(tb) if host_sig is None else host_sig,
            pem(self.host) if host_pub is None else host_pub, FILES,
            self.root, TOKEN, armed=armed, at_time=NOW,
            transport=self.fake if fake is None else fake)

    def test_default_disarmed_and_normal_synthetic_owner_host_once(self):
        with self.assertRaises(PolicyError):
            self.invoke(armed=False)
        self.assertEqual(self.fake.calls, [])
        result = self.invoke()
        self.assertEqual(result["status"], "UCIE_SYNTHETIC_OWNER_DRAFT_SEQUENCE_ONLY")
        self.assertTrue(result["journal_claimed"])
        self.assertFalse(result["network_calls_real"])
        self.assertFalse(result["external_anchor_independently_rechecked_here"])
        self.assertFalse(result["auto_merged"])
        self.assertFalse(result["production_approved"])
        self.assertEqual([m for m, _, _ in self.fake.calls],
                         ["GET", "GET", "GET", "POST", "POST", "POST", "POST", "POST"])
        self.assertEqual(self.fake.calls[-1][2]["draft"], True)
        self.assertEqual(self.fake.calls[-1][2]["base"], "main")
        # Never replay same signed owner grant after claiming it.
        previous_count = len(self.fake.calls)
        with self.assertRaises(PolicyError):
            self.invoke()
        self.assertEqual(len(self.fake.calls), previous_count + 3)

    def test_remote_main_changed_refuses_before_claim(self):
        self.fake.main = "d"*40
        with self.assertRaises(PolicyError):
            self.invoke()
        self.assertEqual(len(self.fake.calls), 1)
        self.fake.main = BASE
        self.assertEqual(self.invoke()["pr_number"], 120)

    def test_host_signature_must_be_distinct_and_valid(self):
        with self.assertRaises(PolicyError):
            self.invoke(host_pub=pem(self.owner))
        with self.assertRaises(PolicyError):
            self.invoke(host_sig=b"x"*64)
        tampered = dict(self.t)
        tampered["task_id"] = "UCIE-FOREIGN-TASK"
        with self.assertRaises(PolicyError):
            self.invoke(ticket_obj=tampered)
        self.assertEqual(self.fake.calls, [])

    def test_host_ticket_restricts_expiry_and_external_epoch_shape(self):
        for edit in (
            {"expires_at": "2026-10-23T10:30:00Z"},
            {"expires_at": "2026-10-23T09:59:00Z"},
            {"external_epoch_sha256": "x"*64},
            {"host_sid_sha256": "short"},
            {"audience": "SHARED"},
        ):
            t = {**self.t, **edit}
            with self.subTest(edit=edit), self.assertRaises(PolicyError):
                self.invoke(ticket_obj=t)
        self.assertEqual(self.fake.calls, [])

    def test_ambiguous_pr_failure_consumes_grant_no_blind_retry(self):
        self.fake.fail_pr = True
        with self.assertRaises(PolicyError):
            self.invoke()
        before = len(self.fake.calls)
        self.fake.fail_pr = False
        with self.assertRaises(PolicyError):
            self.invoke()
        self.assertEqual(len(self.fake.calls), before + 3)

    def test_fake_transport_marker_required(self):
        with self.assertRaises(PolicyError):
            self.invoke(fake=lambda method, path, data: {})
        self.assertEqual(self.fake.calls, [])


if __name__ == "__main__":
    unittest.main()
