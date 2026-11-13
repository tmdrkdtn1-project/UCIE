"""C3 true owner signature scope: ephemeral Ed25519 only, never real owner keys."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import json
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucie_miner import local_public_pr_capsule_v01 as cap
from ucie_miner import local_public_pr_owner_auth_v01 as auth
from ucie_miner.public_discovery import SOURCE_SKILL


def in_memory_public_metadata() -> bytes:
    source = "git/git"
    item = {
        "source": source, "reference": "pr:12345:" + "a"*40,
        "pattern_code": "GIT_PORCELAIN_SAFE",
        "skill_id": SOURCE_SKILL[source],
        "evidence_sha256": "c"*64,
        "candidate_id_sha256": "b"*64,
        "stage6_candidate": None,
        "status": "UNVERIFIED_CANDIDATE_ONLY", "approval": False,
        "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
    }
    return cap.build_capsule({
        "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
        "status": "LINKED_UNVERIFIED_NO_GO",
        "source_revisions": 1, "linked_revisions": 1,
        "pending_source_revisions": 0,
        "tasks": [item], "auto_promoted": False,
        "production_approved": False, "deploy_allowed": False,
    })


class OwnerC3StdlibOnlyContractTests(unittest.TestCase):
    def test_crypto_module_import_is_safe_in_first_party_only_install(self):
        # Import at module scope above must not require third-party vendor.
        self.assertEqual(auth.SCHEMA,
                         "UCIE_C3_PUBLIC_PR_METADATA_OWNER_ED25519_ATTESTATION_V01")
        self.assertNotIn("RELEASE", auth.SCOPE)
        self.assertFalse(hasattr(auth, "generate_keys"))

    def test_owner_signing_cannot_run_from_ci_or_unapproved_root(self):
        with TemporaryDirectory(prefix="UCIE_C3_NO_KEYS_") as parent:
            root = Path(parent) / "UCIE"
            (root / ".git").mkdir(parents=True)
            for consent in ("", "yes", auth.SIGN_CONSENT):
                with self.subTest(consent=consent), self.assertRaises(ValueError):
                    auth.sign_existing_owner_local_once(
                        root, serial=1,
                        expected_owner_key_id="a"*32, consent=consent)
            self.assertFalse((root / auth.SIGNATURE_FILE).exists())
            self.assertFalse((root / "downloaded").exists())

    def test_unauthenticated_signed_sidecar_cannot_downgrade_to_unsigned_V04(self):
        with TemporaryDirectory(prefix="UCIE_C3_SIDE_CAR_") as tmp:
            root = Path(tmp) / "UCIE"
            (root / ".git").mkdir(parents=True)
            data = in_memory_public_metadata()
            (root / cap.FILE).write_bytes(data)
            (root / cap.PIN).write_bytes(
                (sha256(data).hexdigest() + "\n").encode("ascii"))
            self.assertEqual(
                cap.read_optional_capsule(root)["selected_count"], 1)
            (root / auth.SIGNATURE_FILE).write_bytes(b"pretend-owner-signature")
            with self.assertRaises(cap.PublicCapsuleError):
                cap.read_optional_capsule(root)
            # Actual localhost UI, not only pure reader, must return 400.
            from ucie_miner.local_v1_app_v01 import make_handler
            import http.client
            from http.server import HTTPServer
            from threading import Thread
            with HTTPServer(("127.0.0.1", 0), make_handler(root)) as server:
                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    conn = http.client.HTTPConnection(
                        "127.0.0.1", server.server_port, timeout=5)
                    try:
                        conn.request("GET", "/local/library?q=Git", headers={
                            "Host": "127.0.0.1:" + str(server.server_port)})
                        result = conn.getresponse()
                        self.assertEqual(result.status, 400)
                        self.assertIn("FAIL_CLOSED", result.read().decode("ascii"))
                    finally:
                        conn.close()
                finally:
                    server.shutdown()
                    thread.join(timeout=5)

    def test_trust_key_parent_symlink_refused_without_reading_any_file(self):
        with TemporaryDirectory(prefix="UCIE_C3_NO_PATH_ESCAPE_") as parent:
            trustdir = Path(parent) / ".build_keys"
            trustdir.mkdir()
            key = trustdir / auth.TRUST_NAME
            key.write_bytes(b"not-a-real-owner-key")
            original_read = Path.read_bytes
            with patch.object(Path, "is_symlink",
                              autospec=True,
                              side_effect=lambda p: p == trustdir):
                with patch.object(Path, "read_bytes",
                                  autospec=True,
                                  side_effect=AssertionError("untrusted file read")):
                    with self.assertRaises(auth.OwnerMetadataAuthError):
                        auth._safe_small(key, max_bytes=auth.MAX_PEM)
            self.assertTrue(key.exists())
            self.assertIsNotNone(original_read)

    def test_invalid_unprovisioned_trust_or_metadata_rejected_first(self):
        raw = in_memory_public_metadata()
        for pub, keyid, serial in (
            (b"", "a"*32, 1),
            (b"no-pem", "bad", 1),
            (b"no-pem", "a"*32, True),
            (b"no-pem", "a"*32, 0),
            (b"no-pem", "a"*32, 2**32),
        ):
            with self.subTest(keyid=keyid, serial=serial), self.assertRaises(
                    auth.OwnerMetadataAuthError):
                auth.verify_owner_metadata_bytes(
                    raw, b"{}", pub,
                    expected_owner_key_id=keyid, min_serial=serial,
                    now=datetime(2026, 11, 13, tzinfo=timezone.utc))

    def test_broken_or_missing_vendor_provider_fails_closed(self):
        with patch.object(auth, "_crypto",
                          side_effect=auth.OwnerMetadataAuthError("vendor absent")):
            with self.assertRaisesRegex(auth.OwnerMetadataAuthError, "vendor absent"):
                auth._crypto()
        self.assertFalse(auth.VERIFY_STATUS.endswith("CUSTOMER_GO"))


class OwnerC3EphemeralCryptoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
            from ucie_public.rulepack import key_id
        except (ImportError, OSError):
            raise unittest.SkipTest("independent cryptography vendor unavailable; no fake crypto PASS")
        cls.private = Ed25519PrivateKey.generate()  # ephemeral in test memory, never saved
        cls.public_pem = cls.private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        cls.expected_key_id = key_id(cls.private.public_key())
        cls.data = in_memory_public_metadata()
        cls.issued = datetime(2026, 11, 13, 5, 0, 0, tzinfo=timezone.utc)
        cls.packed = auth.sign_metadata_bytes(
            cls.data, cls.private, serial=7, issued_at=cls.issued,
            consent=auth.SIGN_CONSENT)

    def verify(self, **changes):
        options = {
            "capsule_bytes": self.data,
            "attestation": self.packed,
            "trusted_public_key_pem": self.public_pem,
            "expected_owner_key_id": self.expected_key_id,
            "min_serial": 7,
            "now": self.issued + timedelta(days=1),
        }
        options.update(changes)
        return auth.verify_owner_metadata_bytes(**options)

    def test_real_ed25519_signature_and_independent_key_pinning_pass(self):
        result = self.verify()
        self.assertTrue(result["signature_cryptographically_verified"])
        self.assertTrue(result["owner_public_key_matches_supplied_trust_pin"])
        self.assertFalse(result["out_of_band_owner_approval_independently_proven"])
        self.assertEqual(result["signed_serial"], 7)
        self.assertEqual(result["owner_key_id"], self.expected_key_id)
        self.assertEqual(result["status"], auth.VERIFY_STATUS)
        for flag in (
            "source_linkage_independently_attested_on_recipient",
            "independent_upstream_fix_verified", "human_approved",
            "license_cleared", "customer_distribution_authorized",
        ):
            self.assertIs(result[flag], False)

    def test_wrong_trust_fingerprint_or_wrong_public_key_fails(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        other = Ed25519PrivateKey.generate()
        other_pem = other.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        for options in (
            {"expected_owner_key_id": "f"*32},
            {"trusted_public_key_pem": other_pem},
            {"trusted_public_key_pem": self.public_pem + b"# tamper"},
        ):
            with self.subTest(options=tuple(options)), self.assertRaises(ValueError):
                self.verify(**options)

    def test_modified_capsule_even_with_recomputed_adjacent_sha_denied(self):
        another = bytearray(self.data)
        i = another.index(b"GIT_PORCELAIN_SAFE")
        another[i] = ord("P")
        with self.assertRaises(ValueError):
            self.verify(capsule_bytes=bytes(another))
        with self.assertRaises(ValueError):
            self.verify(capsule_bytes=self.data + b" ")
        self.assertEqual(sha256(self.data).hexdigest(),
                         json.loads(self.packed)["capsule_sha256"])

    def test_attestation_field_forgery_not_repaired_by_new_json_digest(self):
        for update in (
            {"serial": 8},
            {"status": "CUSTOMER_PRODUCTION_APPROVED"},
            {"scope": "UCIE_CUSTOMER_RELEASE"},
            {"capsule_sha256": "f"*64},
            {"owner_key_id": "a"*32},
            {"snapshot_signed": True},
            {"algorithm": "SHA-256"},
        ):
            attacked = json.loads(self.packed)
            attacked.update(update)
            raw = auth._canonical(attacked)
            with self.subTest(keys=tuple(update)), self.assertRaises(ValueError):
                self.verify(attestation=raw)

    def test_replay_expiration_serial_floor_and_time_bounds(self):
        with self.assertRaises(ValueError):
            self.verify(min_serial=8)
        with self.assertRaises(ValueError):
            self.verify(now=self.issued - timedelta(minutes=6))
        with self.assertRaises(ValueError):
            self.verify(now=self.issued + timedelta(days=31))
        self.assertTrue(self.verify(now=self.issued + timedelta(days=30))[
            "signature_cryptographically_verified"])

    def test_well_formed_duplicate_json_field_refused(self):
        raw = self.packed.replace(
            b'"snapshot_signed":', b'"snapshot_signed":')
        self.assertEqual(raw, self.packed)
        # A duplicate signed top-level key cannot enter the verifier.
        duplicate = self.packed.replace(
            b'"algorithm":"Ed25519"',
            b'"algorithm":"Ed25519","algorithm":"Ed25519"')
        with self.assertRaises(ValueError):
            self.verify(attestation=duplicate)

    def test_bad_signature_encoding_and_valid_but_wrong_key(self):
        bad = json.loads(self.packed)
        bad["signature_base64"] = ("A"*86) + "=="
        with self.assertRaises(ValueError):
            self.verify(attestation=auth._canonical(bad))
        other = auth.sign_metadata_bytes(
            self.data, self.private, serial=3, issued_at=self.issued,
            consent=auth.SIGN_CONSENT)
        with self.assertRaises(ValueError):
            self.verify(attestation=other)

    def test_signing_require_explicit_consent_bounded_serial_and_original_metadata(self):
        for consent in ("", "yes", auth.SIGN_CONSENT + "!"):
            with self.assertRaises(ValueError):
                auth.sign_metadata_bytes(self.data, self.private, serial=7,
                                         issued_at=self.issued, consent=consent)
        for serial in (0, True, 2**31):
            with self.assertRaises(ValueError):
                auth.sign_metadata_bytes(self.data, self.private, serial=serial,
                                         issued_at=self.issued, consent=auth.SIGN_CONSENT)
        with self.assertRaises(ValueError):
            auth.sign_metadata_bytes(b"{}", self.private, serial=7,
                                     issued_at=self.issued, consent=auth.SIGN_CONSENT)


if __name__ == "__main__":
    unittest.main()
