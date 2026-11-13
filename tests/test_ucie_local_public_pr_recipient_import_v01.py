"""C3.2: ephemeral Ed25519 and real disposable UCIE recipient import/HTTP."""
from __future__ import annotations

from contextlib import closing, redirect_stdout
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from http.client import HTTPConnection
from http.server import HTTPServer
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch
import json
import unittest

from ucie_miner import local_public_pr_capsule_v01 as cap
from ucie_miner import local_public_pr_owner_auth_v01 as auth
from ucie_miner import local_public_pr_recipient_import_v01 as intake
from ucie_miner import local_public_pr_trusted_recipient_v01 as viewer
from ucie_miner.public_discovery import SOURCE_SKILL


def public_capsule() -> bytes:
    source = "git/git"
    item = {
        "source": source, "reference": "pr:45984:" + "c"*40,
        "pattern_code": "GIT_PORCELAIN_SAFE", "skill_id": SOURCE_SKILL[source],
        "evidence_sha256": "f"*64, "candidate_id_sha256": "e"*64,
        "stage6_candidate": None, "status": "UNVERIFIED_CANDIDATE_ONLY",
        "approval": False, "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
    }
    return cap.build_capsule({
        "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
        "status": "LINKED_UNVERIFIED_NO_GO", "source_revisions": 1,
        "linked_revisions": 1, "pending_source_revisions": 0,
        "tasks": [item], "auto_promoted": False,
        "production_approved": False, "deploy_allowed": False,
    })


class RecipientC32EphemeralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
            from ucie_public.rulepack import key_id
        except (ImportError, OSError):
            raise unittest.SkipTest("Ed25519 native provider absent; NO crypto PASS")
        cls.ephemeral_private = Ed25519PrivateKey.generate()
        cls.public_pem = cls.ephemeral_private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        cls.key_id = key_id(cls.ephemeral_private.public_key())
        cls.issued = datetime.now(timezone.utc).replace(microsecond=0)
        cls.data = public_capsule()
        cls.pin = (sha256(cls.data).hexdigest() + "\n").encode("ascii")
        cls.signed = auth.sign_metadata_bytes(
            cls.data, cls.ephemeral_private, serial=7, issued_at=cls.issued,
            consent=auth.SIGN_CONSENT)

    def setUp(self):
        self.temp = TemporaryDirectory(prefix="UCIE_C32_PUBLIC_ONLY_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "UCIE"
        (self.root / ".git").mkdir(parents=True)
        (self.root / ".build_keys").mkdir()
        (self.root / ".build_keys" / auth.TRUST_NAME).write_bytes(self.public_pem)
        self.inbox = self.root / "downloaded"
        self.inbox.mkdir()
        (self.inbox / cap.FILE).write_bytes(self.data)
        (self.inbox / cap.PIN).write_bytes(self.pin)
        (self.inbox / auth.SIGNATURE_FILE).write_bytes(self.signed)

    def import_once(self, **updates):
        kwargs = {
            "root": self.root, "expected_owner_key_id": self.key_id,
            "min_serial": 7, "consent": intake.CONSENT,
            "apply": True, "now": self.issued + timedelta(seconds=3),
        }
        kwargs.update(updates)
        return intake.import_existing_signed_public_once(**kwargs)

    def assert_no_import(self):
        for name, _ in intake.FILES:
            self.assertFalse((self.root / name).exists(), name)

    def test_01_real_ed25519_preflight_zero_writes(self):
        r = self.import_once(apply=False)
        self.assertEqual(r["status"], intake.PREFLIGHT_STATUS)
        self.assertTrue(r["signature_cryptographically_verified"])
        self.assertEqual(r["copied_public_metadata_files"], 0)
        self.assertFalse(r["out_of_band_owner_approval_independently_proven"])
        self.assertFalse(r["customer_distribution_authorized"])
        self.assert_no_import()

    def test_02_one_time_three_exact_files_and_no_private_key(self):
        r = self.import_once()
        self.assertEqual(r["status"], intake.STATUS)
        self.assertEqual(r["copied_public_metadata_files"], 3)
        self.assertEqual(r["unverified_public_candidate_count"], 1)
        self.assertFalse(r["owner_private_key_read_or_created"])
        self.assertEqual((self.root / cap.FILE).read_bytes(), self.data)
        self.assertEqual((self.root / cap.PIN).read_bytes(), self.pin)
        self.assertEqual((self.root / auth.SIGNATURE_FILE).read_bytes(), self.signed)
        self.assertFalse((self.root / ".build_keys" / auth.PRIVATE_NAME).exists())
        snapshot, receipt = viewer.read_signed_public_review(
            self.root, expected_owner_key_id=self.key_id, min_serial=7)
        self.assertEqual(snapshot["selected_count"], 1)
        self.assertTrue(receipt["signature_cryptographically_verified"])

    def test_03_installed_style_localhost_get200_unsigned_still_denied(self):
        self.import_once()
        handler = viewer.make_trusted_handler(
            self.root, expected_owner_key_id=self.key_id, min_serial=7)
        with HTTPServer(("127.0.0.1", 0), handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for route, expected in (
                    ("/local/trusted-public?q=Git", 200),
                    ("/local/library?q=Git", 400),
                    ("/local/evolution?q=Git", 400),
                    ("/local/review?q=Git", 400),
                ):
                    with self.subTest(route=route), closing(
                            HTTPConnection("127.0.0.1", server.server_port, timeout=5)) as c:
                        c.request("GET", route, headers={
                            "Host": "127.0.0.1:" + str(server.server_port)})
                        response = c.getresponse()
                        page = response.read(400001).decode("utf-8", "replace")
                        self.assertEqual(response.status, expected)
                        if expected == 200:
                            self.assertIn('data-c31-owner-signature="verified"', page)
                            self.assertIn("UNVERIFIED_CANDIDATE_ONLY", page)
                            self.assertIn("github.com/git/git/pull/45984", page)
                            self.assertNotIn("개선 방향 살펴보기<span", page)
                with closing(HTTPConnection("127.0.0.1", server.server_port, timeout=5)) as c:
                    c.request("POST", "/local/trusted-public", headers={
                        "Host": "127.0.0.1:" + str(server.server_port)})
                    response = c.getresponse()
                    response.read(1024)
                    self.assertEqual(response.status, 405)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())

    def test_04_double_import_fails_closed_without_overwrite(self):
        self.import_once()
        before = [(self.root / p).read_bytes() for p, _ in intake.FILES]
        with self.assertRaises(ValueError):
            self.import_once()
        self.assertEqual(before, [(self.root / p).read_bytes() for p, _ in intake.FILES])
        self.assertFalse((self.root / "runtime").exists())

    def test_05_collision_denied_before_first_new_write(self):
        (self.root / cap.PIN).write_bytes(b"pre-existing-user-data")
        with self.assertRaises(ValueError):
            self.import_once()
        self.assertFalse((self.root / cap.FILE).exists())
        self.assertFalse((self.root / auth.SIGNATURE_FILE).exists())

    def test_06_wrong_consent_fingerprint_serial_and_type(self):
        for changed in (
            {"consent": "yes"}, {"consent": ""},
            {"expected_owner_key_id": "f"*32},
            {"expected_owner_key_id": "wrong-key"},
            {"min_serial": 8}, {"min_serial": True},
            {"apply": 1},
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.import_once(**changed)
            self.assert_no_import()

    def test_07_expired_or_future_ed25519_signature(self):
        for time in (self.issued + timedelta(days=31),
                     self.issued - timedelta(minutes=6)):
            with self.subTest(time=time), self.assertRaises(ValueError):
                self.import_once(now=time)
        self.assert_no_import()

    def test_08_forged_signature_and_recomputed_sha(self):
        (self.inbox / auth.SIGNATURE_FILE).write_bytes(b"forged")
        with self.assertRaises(ValueError):
            self.import_once()
        (self.inbox / auth.SIGNATURE_FILE).write_bytes(self.signed)
        data = self.data + b" "
        (self.inbox / cap.FILE).write_bytes(data)
        (self.inbox / cap.PIN).write_bytes(
            (sha256(data).hexdigest() + "\n").encode("ascii"))
        with self.assertRaises(ValueError):
            self.import_once()
        self.assert_no_import()

    def test_09_nonempty_operating_runtime_must_never_be_imported_into(self):
        runtime = self.root / "runtime"
        runtime.mkdir()
        (runtime / "public_miner.sqlite3").write_bytes(b"inert-not-real")
        with self.assertRaises(ValueError):
            self.import_once()
        self.assert_no_import()

    def test_10_untrusted_public_key_or_absent_trust(self):
        key_file = self.root / ".build_keys" / auth.TRUST_NAME
        key_file.unlink()
        with self.assertRaises(ValueError):
            self.import_once()
        key_file.write_bytes(b"bad-public-key")
        with self.assertRaises(ValueError):
            self.import_once()
        self.assert_no_import()

    def test_11_missing_public_capsule_inbox_item(self):
        (self.inbox / cap.PIN).unlink()
        with self.assertRaises(ValueError):
            self.import_once()
        self.assert_no_import()

    def test_12_symlinked_inbox_capsule_denied(self):
        target = self.inbox / cap.FILE
        original = Path.is_symlink
        with patch.object(Path, "is_symlink", autospec=True,
                          side_effect=lambda p: p == target or original(p)):
            with self.assertRaises(ValueError):
                self.import_once()
        self.assert_no_import()

    def test_13_cli_real_preview_then_commit_no_owner_key_access(self):
        common = [
            "--recipient-ucie-root", str(self.root),
            "--expected-owner-key-id", self.key_id, "--min-serial", "7",
        ]
        out = StringIO()
        with redirect_stdout(out):
            code = intake.main(common)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["copied_public_metadata_files"], 0)
        self.assert_no_import()
        out = StringIO()
        with redirect_stdout(out):
            code = intake.main(common + ["--apply-once"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["copied_public_metadata_files"], 3)


if __name__ == "__main__":
    unittest.main()
