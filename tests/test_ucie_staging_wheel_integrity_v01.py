"""Synthetic tamper tests for UCIE-only staging wheel integrity policy."""
from __future__ import annotations

import base64
import csv
from hashlib import sha256
import io
import stat
import unittest
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from ucie_miner.staging_wheel_integrity_v01 import (
    DIST, WheelAttestationError, verify_staging_wheel,
)

ORIGINAL = {
    "ucie_miner/__init__.py": b"source_a=1\n",
    "ucie_public/__init__.py": b"source_b=2\n",
}
META = {
    DIST + "METADATA": (
        b"Metadata-Version: 2.4\nName: ucie-public-only-demo\n"
        b"Version: 0.1.0\nRequires-Python: >=3.13\n"
    ),
    DIST + "WHEEL": (
        b"Wheel-Version: 1.0\nGenerator: synthetic-only\n"
        b"Root-Is-Purelib: true\nTag: py3-none-any\n"
    ),
    DIST + "top_level.txt": b"ucie_miner\nucie_public\n",
}


def source_sha_map():
    return {k: sha256(v).hexdigest() for k, v in ORIGINAL.items()}


def fake_wheel(*, extra=None, broken_record=False, symlink_name=None):
    entries = {**ORIGINAL, **META}
    if extra:
        entries.update(extra)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    for name, raw in entries.items():
        digest = base64.urlsafe_b64encode(sha256(raw).digest()).rstrip(b"=")
        if broken_record and name == "ucie_miner/__init__.py":
            digest = b"A" * len(digest)
        writer.writerow((name, "sha256=" + digest.decode("ascii"), len(raw)))
    writer.writerow((DIST + "RECORD", "", ""))
    entries[DIST + "RECORD"] = output.getvalue().encode("utf-8")
    target = io.BytesIO()
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for name, raw in entries.items():
            if name == symlink_name:
                link = ZipInfo(name)
                link.create_system = 3
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                link.compress_type = ZIP_DEFLATED
                archive.writestr(link, raw)
            else:
                archive.writestr(name, raw)
    return target.getvalue()


class StagingWheelIntegrityTests(unittest.TestCase):
    def test_accepts_bounded_pure_python_wheel_with_matching_record(self):
        receipt = verify_staging_wheel(fake_wheel(), source_sha_map())
        self.assertEqual(receipt["status"], "STAGING_CONTENT_VERIFIED_RELEASE_NO_GO")
        self.assertEqual(receipt["first_party_source_modules"], 2)
        self.assertTrue(receipt["wheel_record_verified"])
        self.assertTrue(receipt["source_files_match_checkout"])
        self.assertFalse(receipt["external_release_authorized"])
        self.assertFalse(receipt["independent_security_or_license_attested"])

    def test_fails_source_tamper_even_if_record_recomputed(self):
        modified = fake_wheel(extra={"ucie_public/__init__.py": b"changed=1\n"})
        with self.assertRaises(WheelAttestationError):
            verify_staging_wheel(modified, source_sha_map())

    def test_fails_missing_source_even_with_valid_remaining_wheel(self):
        source = source_sha_map()
        del source["ucie_miner/__init__.py"]
        with self.assertRaises(WheelAttestationError):
            verify_staging_wheel(fake_wheel(), source)

    def test_fails_hidden_database_or_executable_payload(self):
        for filename in ("runtime/miner.sqlite3", "ucie_miner/evil.exe",
                         "../escape.py", "ucie_public/keys.pem"):
            with self.subTest(filename=filename):
                raw = fake_wheel(extra={filename: b"not-real-content\n"})
                with self.assertRaises(WheelAttestationError):
                    verify_staging_wheel(raw, source_sha_map())

    def test_fails_mismatched_record_digest(self):
        with self.assertRaises(WheelAttestationError):
            verify_staging_wheel(fake_wheel(broken_record=True), source_sha_map())

    def test_fails_symlinked_source_member(self):
        with self.assertRaises(WheelAttestationError):
            verify_staging_wheel(fake_wheel(
                symlink_name="ucie_miner/__init__.py"), source_sha_map())

    def test_fails_unexpected_metadata_or_runtime_version(self):
        for name, data in (
            (DIST + "METADATA", b"Name: ucie-public-only-demo\nVersion: 0.2.0\n"),
            (DIST + "WHEEL", b"Root-Is-Purelib: false\nTag: cp315-win_amd64\n"),
        ):
            with self.subTest(name=name):
                with self.assertRaises(WheelAttestationError):
                    verify_staging_wheel(fake_wheel(extra={name: data}),
                                         source_sha_map())

    def test_fails_truncated_wheel_and_invalid_source_hash(self):
        with self.assertRaises(WheelAttestationError):
            verify_staging_wheel(b"PK" * 10, source_sha_map())
        bad = source_sha_map()
        bad["ucie_miner/__init__.py"] = "NOT_A_SHA"
        with self.assertRaises(WheelAttestationError):
            verify_staging_wheel(fake_wheel(), bad)

    def test_fails_when_archive_contains_duplicate_members(self):
        entries = fake_wheel()
        target = io.BytesIO(entries)
        # Appending a second source entry creates a duplicate zip member.
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(target, "a") as archive:
                archive.writestr("ucie_miner/__init__.py", ORIGINAL[
                    "ucie_miner/__init__.py"])
        with self.assertRaises(WheelAttestationError):
            verify_staging_wheel(target.getvalue(), source_sha_map())


    def test_exact_first_party_customer_preview_entrypoint_is_allowed(self):
        from ucie_miner.staging_wheel_integrity_v01 import ENTRY_POINT
        source = b'"""UCIE staging synthetic module"""\n'
        manifest = {
            "ucie_miner/customer_staging_v01.py": source,
            ENTRY_POINT: (
                b"[console_scripts]\n"
                b"ucie-product-preview = ucie_miner.customer_staging_v01:main\n"
            ),
        }
        digests = source_sha_map()
        digests["ucie_miner/customer_staging_v01.py"] = sha256(
            source).hexdigest()
        report = verify_staging_wheel(
            fake_wheel(extra=manifest), digests)
        self.assertTrue(report["customer_preview_entrypoint_verified"])
        self.assertFalse(report["external_release_authorized"])

    def test_extra_or_wrong_console_scripts_are_refused(self):
        from ucie_miner.staging_wheel_integrity_v01 import ENTRY_POINT
        source = b'"""UCIE staging synthetic module"""\n'
        digests = source_sha_map()
        digests["ucie_miner/customer_staging_v01.py"] = sha256(
            source).hexdigest()
        for content in (
            b"[console_scripts]\nucie-product-preview = os:system\n",
            b"[console_scripts]\n"
            b"ucie-product-preview = ucie_miner.customer_staging_v01:main\n"
            b"extra-install = os:system\n",
            b"[other_scripts]\n"
            b"ucie-product-preview = ucie_miner.customer_staging_v01:main\n",
        ):
            with self.subTest(content=content), self.assertRaises(
                WheelAttestationError
            ):
                verify_staging_wheel(fake_wheel(extra={
                    "ucie_miner/customer_staging_v01.py": source,
                    ENTRY_POINT: content,
                }), digests)

    def test_missing_entrypoint_with_staging_cli_source_is_refused(self):
        source = b'"""UCIE staging synthetic module"""\n'
        digests = source_sha_map()
        digests["ucie_miner/customer_staging_v01.py"] = sha256(
            source).hexdigest()
        with self.assertRaises(WheelAttestationError):
            verify_staging_wheel(fake_wheel(extra={
                "ucie_miner/customer_staging_v01.py": source,
            }), digests)

    def test_entrypoint_without_staging_cli_source_is_refused(self):
        from ucie_miner.staging_wheel_integrity_v01 import ENTRY_POINT
        with self.assertRaises(WheelAttestationError):
            verify_staging_wheel(fake_wheel(extra={
                ENTRY_POINT: (
                    b"[console_scripts]\nucie-product-preview = "
                    b"ucie_miner.customer_staging_v01:main\n"
                ),
            }), source_sha_map())


if __name__ == "__main__":
    unittest.main()
