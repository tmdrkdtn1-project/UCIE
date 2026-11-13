"""C3.1 self-authored ephemeral trust fixtures; never touch real owner keys/DB."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from contextlib import closing
import json
import unittest

from ucie_miner import local_public_pr_owner_auth_v01 as auth
from ucie_miner import local_public_pr_capsule_v01 as capsule
from ucie_miner import local_public_pr_trusted_recipient_v01 as receiver
from ucie_miner import local_v1_app_v01 as local
from ucie_miner.public_discovery import SOURCE_SKILL


def synthetic_capsule() -> bytes:
    source = "git/git"
    row = {
        "source": source, "reference": "pr:45984:" + "c"*40,
        "pattern_code": "GIT_PORCELAIN_SAFE",
        "skill_id": SOURCE_SKILL[source],
        "evidence_sha256": "d"*64,
        "candidate_id_sha256": "e"*64,
        "stage6_candidate": None,
        "status": "UNVERIFIED_CANDIDATE_ONLY", "approval": False,
        "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
    }
    return capsule.build_capsule({
        "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
        "status": "LINKED_UNVERIFIED_NO_GO",
        "source_revisions": 1, "linked_revisions": 1,
        "pending_source_revisions": 0, "tasks": [row],
        "auto_promoted": False, "production_approved": False,
        "deploy_allowed": False,
    })


class C31NoVendorTests(unittest.TestCase):
    def test_invalid_trust_policy_rejected_before_private_or_vendor_access(self):
        with TemporaryDirectory(prefix="UCIE_C31_NOT_APPROVED_") as tmp:
            root = Path(tmp) / "UCIE"
            root.mkdir()
            (root / ".git").mkdir()
            for keyid, floor in (
                ("", 1), ("x"*32, 1), ("a"*32, 0),
                ("a"*32, True), ("a"*32, 2**31),
            ):
                with self.subTest(keyid=keyid, floor=floor):
                    with self.assertRaises(ValueError):
                        receiver.read_signed_public_review(
                            root, expected_owner_key_id=keyid, min_serial=floor)
            self.assertFalse((root / ".build_keys").exists())

    def test_unprovisioned_signed_preview_is_not_unsigned_downgrade(self):
        with TemporaryDirectory(prefix="UCIE_C31_EMPTY_") as tmp:
            root = Path(tmp) / "UCIE"
            root.mkdir()
            (root / ".git").mkdir()
            with self.assertRaises(ValueError):
                receiver.read_signed_public_review(
                    root, expected_owner_key_id="a"*32, min_serial=1)
            self.assertIsNone(capsule.read_optional_capsule(root))
            self.assertFalse((root / "downloaded").exists())

    def test_module_separate_from_owner_key_generation(self):
        self.assertFalse(hasattr(receiver, "generate_owner_key"))
        self.assertFalse(hasattr(auth, "generate_keys"))
        self.assertIn("NO_GO", receiver.STATUS)


class C31EphemeralEd25519Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
            from ucie_public.rulepack import key_id
        except (ImportError, OSError):
            raise unittest.SkipTest("independent Ed25519 vendor missing; never claim crypto PASS")
        cls.private = Ed25519PrivateKey.generate()
        cls.public = cls.private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo)
        cls.keyid = key_id(cls.private.public_key())
        cls.now = datetime(2026, 11, 13, 5, 0, tzinfo=timezone.utc)
        cls.data = synthetic_capsule()
        cls.attestation = auth.sign_metadata_bytes(
            cls.data, cls.private, serial=7,
            issued_at=cls.now, consent=auth.SIGN_CONSENT)

    def setUp(self):
        self.temp = TemporaryDirectory(prefix="UCIE_C31_TEST_ONLY_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "UCIE"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        trust = self.root / ".build_keys"
        trust.mkdir()
        (trust / auth.TRUST_NAME).write_bytes(self.public)
        (self.root / capsule.FILE).write_bytes(self.data)
        (self.root / capsule.PIN).write_bytes(
            (sha256(self.data).hexdigest() + "\n").encode("ascii"))
        (self.root / auth.SIGNATURE_FILE).write_bytes(self.attestation)

    def verify(self, **changes):
        options = dict(root=self.root, expected_owner_key_id=self.keyid,
                       min_serial=7, now=self.now + timedelta(days=1))
        options.update(changes)
        return receiver.read_signed_public_review(**options)

    def request(self, route: str, *, method: str = "GET",
                host_override: str | None = None) -> tuple[int, str]:
        handler = receiver.make_trusted_handler(
            self.root, expected_owner_key_id=self.keyid, min_serial=7)
        with HTTPServer(("127.0.0.1", 0), handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                host = host_override or "127.0.0.1:" + str(server.server_port)
                with closing(HTTPConnection("127.0.0.1", server.server_port,
                                            timeout=5)) as conn:
                    conn.request(method, route, headers={"Host": host})
                    response = conn.getresponse()
                    return response.status, response.read(400001).decode(
                        "utf-8", "replace")
            finally:
                server.shutdown()
                thread.join(timeout=5)
                if thread.is_alive():
                    raise AssertionError("UCIE synthetic HTTP server leaked")

    def test_genuine_signature_can_read_unapproved_metadata(self):
        public, receipt = self.verify()
        self.assertEqual(public["selected_count"], 1)
        self.assertTrue(receipt["signature_cryptographically_verified"])
        self.assertFalse(receipt["out_of_band_owner_approval_independently_proven"])
        self.assertFalse(receipt["customer_distribution_authorized"])
        self.assertFalse(receipt["human_approved"])

    def test_local_readonly_browser_and_existing_unsigned_gate(self):
        # Pure rendering acceptance first: preserve exact exception diagnostic
        # for synthetic fixtures, rather than hiding it behind HTTP400.
        html_direct = receiver.render_signed_public_review(
            self.root, expected_owner_key_id=self.keyid, min_serial=7,
            raw_query="q=Git")
        self.assertIn('data-c31-owner-signature="verified"', html_direct)
        code, html = self.request("/local/trusted-public?q=Git")
        self.assertEqual(code, 200)
        self.assertIn('data-c31-owner-signature="verified"', html)
        self.assertIn("github.com/git/git/pull/45984", html)
        self.assertIn("UNVERIFIED_CANDIDATE_ONLY", html)
        self.assertNotIn("개선 방향 살펴보기<span", html)
        for route in ("/local/library?q=Git", "/local/evolution?q=Git",
                      "/local/review?q=Git"):
            with self.subTest(route=route):
                code, _ = self.request(route)
                self.assertEqual(code, 400)
        code, body = self.request("/local/trusted-public", method="POST")
        self.assertEqual(code, 405)
        self.assertIn("READ_ONLY", body)

    def test_attacker_key_and_tampered_metadata_are_denied(self):
        for change in ("keyid", "signature", "payload"):
            with self.subTest(change=change):
                if change == "keyid":
                    with self.assertRaises(ValueError):
                        self.verify(expected_owner_key_id="f"*32)
                elif change == "signature":
                    (self.root / auth.SIGNATURE_FILE).write_bytes(b"forged")
                    with self.assertRaises(ValueError):
                        self.verify()
                    (self.root / auth.SIGNATURE_FILE).write_bytes(self.attestation)
                else:
                    data = self.data + b" "
                    (self.root / capsule.FILE).write_bytes(data)
                    (self.root / capsule.PIN).write_bytes(
                        (sha256(data).hexdigest() + "\n").encode("ascii"))
                    with self.assertRaises(ValueError):
                        self.verify()
                    (self.root / capsule.FILE).write_bytes(self.data)
                    (self.root / capsule.PIN).write_bytes(
                        (sha256(self.data).hexdigest() + "\n").encode("ascii"))

    def test_replay_and_expired_signature_fail(self):
        with self.assertRaises(ValueError):
            self.verify(min_serial=8)
        with self.assertRaises(ValueError):
            self.verify(now=self.now + timedelta(days=31))
        with self.assertRaises(ValueError):
            self.verify(now=self.now - timedelta(minutes=6))

    def test_symlink_parent_and_operating_runtime_denied(self):
        (self.root / "runtime").mkdir()
        (self.root / "runtime" / "not-owner-DB").write_text("unexpected", "utf-8")
        with self.assertRaises(ValueError):
            self.verify()
        (self.root / "runtime" / "not-owner-DB").unlink()
        (self.root / "runtime").rmdir()

    def test_http_injection_and_network_host_denied(self):
        for route in (
            "/local/trusted-public?q=Git&q=Git",
            "/local/trusted-public?q=..%2fetc",
            "/local/trusted-public?page=2",
        ):
            with self.subTest(route=route):
                code, _ = self.request(route)
                self.assertEqual(code, 400)
        code, _ = self.request(
            "/local/trusted-public", host_override="attacker.example")
        self.assertEqual(code, 403)

    def test_cannot_show_signature_after_attestation_removed(self):
        (self.root / auth.SIGNATURE_FILE).unlink()
        code, body = self.request("/local/trusted-public?q=Git")
        self.assertEqual(code, 400)
        self.assertIn("FAIL_CLOSED", body)

    def test_query_is_not_a_new_approval_channel(self):
        code, body = self.request("/local/trusted-public?q=Git")
        self.assertEqual(code, 200)
        self.assertIn("독립적으로 입증되지 않았습니다", body)
        self.assertNotIn("customer_distribution_authorized=true", body)
        self.assertNotIn("owner_approved=true", body)


if __name__ == "__main__":
    unittest.main()
