"""UCIE-only five-original LICENSE copy integration: synthetic fixtures, no vendor binaries."""
from __future__ import annotations

from hashlib import sha256
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucie_miner import customer_c2_license_copy_bundle_v01 as copy
from ucie_miner import customer_private_offline_lifecycle_v01 as life
from test_ucie_c2_existing_owner_license_integrity_v01 import (
    ExistingOwnerC2FiveLicenseTextAuditTests,
)


class C2PrivateBundleLicenseCopiesTests(unittest.TestCase):
    def fixture(self, directory: Path):
        packet, pin, _ = ExistingOwnerC2FiveLicenseTextAuditTests().build(directory)
        technical_bundle = directory / "UCIE" / "qa" / "UCIE_PRIVATE_BUNDLE"
        technical_bundle.mkdir(parents=True)
        return packet, pin, technical_bundle

    def build_review(self, directory: Path):
        packet, pin, bundle = self.fixture(directory)
        originals = copy.prepare_originals(packet, independent_sha256=pin)
        receipt = copy.stage_originals_into_technical_bundle(bundle, originals, pin)
        return packet, pin, bundle, receipt

    def test_01_verified_originals_five_and_no_private_source_write(self):
        with TemporaryDirectory() as tmp:
            packet, pin, bundle = self.fixture(Path(tmp))
            before = {p.relative_to(packet).as_posix(): sha256(p.read_bytes()).hexdigest()
                      for p in packet.rglob("*") if p.is_file()}
            originals = copy.prepare_originals(packet, independent_sha256=pin)
            result = copy.stage_originals_into_technical_bundle(bundle, originals, pin)
            after = {p.relative_to(packet).as_posix(): sha256(p.read_bytes()).hexdigest()
                     for p in packet.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(result["license_file_count"], 5)
            self.assertFalse(result["customer_distribution_authorized"])
            self.assertFalse(result["openssl_embedded_license_and_notice_completed"])

    def test_02_real_bytes_copied_and_exact_hash_checked(self):
        with TemporaryDirectory() as tmp:
            packet, pin, bundle, receipt = self.build_review(Path(tmp))
            result = copy.verify_staged_originals(bundle/copy.DIR, receipt)
            self.assertEqual(result["original_license_files_verified"], 5)
            self.assertTrue(result["source_hash_bound_to_existing_owner_receipt"])
            self.assertFalse(result["human_license_notice_approved"])

    def test_03_exact_open_ssl_legal_notice_cannot_be_faked(self):
        with TemporaryDirectory() as tmp:
            _, _, bundle, receipt = self.build_review(Path(tmp))
            self.assertFalse(receipt["openssl_embedded_license_and_notice_completed"])
            document = bundle/copy.DIR/"original_license_manifest.json"
            j = json.loads(document.read_text())
            j["openssl_embedded_license_and_notice_completed"] = True
            document.write_bytes(copy._canonical(j))
            with self.assertRaises(ValueError):
                copy.verify_staged_originals(bundle/copy.DIR, receipt)

    def test_04_wrong_independent_owner_receipt_rejected_before_write(self):
        with TemporaryDirectory() as tmp:
            packet, _, bundle = self.fixture(Path(tmp))
            with self.assertRaises(ValueError):
                copy.prepare_originals(packet, independent_sha256="f"*64)
            self.assertFalse((bundle/copy.DIR).exists())

    def test_05_corrupted_existing_original_rejected_before_write(self):
        with TemporaryDirectory() as tmp:
            packet, pin, bundle = self.fixture(Path(tmp))
            license_path = next((packet/"license-text").rglob("*LICENSE*"))
            license_path.write_bytes(b"tampered license")
            with self.assertRaises(ValueError):
                copy.prepare_originals(packet, independent_sha256=pin)
            self.assertFalse((bundle/copy.DIR).exists())

    def test_06_tampered_bundle_copy_sha_rejected(self):
        with TemporaryDirectory() as tmp:
            _, _, bundle, receipt = self.build_review(Path(tmp))
            file = bundle/copy.DIR/"ORIGINAL_LICENSE_01.txt"
            file.write_bytes(b"X" + file.read_bytes()[1:])
            with self.assertRaises(ValueError):
                copy.verify_staged_originals(bundle/copy.DIR, receipt)

    def test_07_no_repeat_overwrite_existing_review(self):
        with TemporaryDirectory() as tmp:
            _, pin, bundle, receipt = self.build_review(Path(tmp))
            originals = [(f"license-text/synthetic/{i}", b"test") for i in range(5)]
            with self.assertRaises(ValueError):
                copy.stage_originals_into_technical_bundle(bundle, originals, pin)
            self.assertEqual(copy.verify_staged_originals(
                bundle/copy.DIR, receipt)["original_license_files_verified"],5)

    def test_08_extra_and_missing_files_rejected(self):
        with TemporaryDirectory() as tmp:
            _, _, bundle, receipt = self.build_review(Path(tmp))
            folder=bundle/copy.DIR
            added=folder/"CUSTOMER_APPROVED.txt"
            added.write_text("YES")
            with self.assertRaises(ValueError):
                copy.verify_staged_originals(folder, receipt)
            added.unlink()
            (folder/"ORIGINAL_LICENSE_05.txt").unlink()
            with self.assertRaises(ValueError):
                copy.verify_staged_originals(folder, receipt)

    def test_09_review_not_laundered_by_modified_receipt(self):
        with TemporaryDirectory() as tmp:
            _, _, bundle, receipt = self.build_review(Path(tmp))
            altered={**receipt,"human_license_notice_approved":True}
            with self.assertRaises(ValueError):
                copy.verify_staged_originals(bundle/copy.DIR, altered)
            altered={**receipt,"customer_distribution_authorized":True}
            with self.assertRaises(ValueError):
                copy.verify_staged_originals(bundle/copy.DIR, altered)

    def test_10_duplicate_manifest_fields_rejected(self):
        with TemporaryDirectory() as tmp:
            _, _, bundle, receipt = self.build_review(Path(tmp))
            file=bundle/copy.DIR/"original_license_manifest.json"
            file.write_bytes(b'{"schema":"a","schema":"b"}\n')
            with self.assertRaises(ValueError):
                copy.verify_staged_originals(bundle/copy.DIR, receipt)

    def test_11_only_private_technical_bundle_root_allowed(self):
        with TemporaryDirectory() as tmp:
            packet, pin, bundle = self.fixture(Path(tmp))
            originals=copy.prepare_originals(packet, independent_sha256=pin)
            for root in (packet, bundle.parent):
                with self.subTest(root=root), self.assertRaises(ValueError):
                    copy.stage_originals_into_technical_bundle(root,originals,pin)

    def test_12_no_network_or_download_during_source_copy(self):
        with TemporaryDirectory() as tmp:
            packet, pin, bundle = self.fixture(Path(tmp))
            with patch("urllib.request.urlopen",side_effect=AssertionError("not allowed")):
                originals=copy.prepare_originals(packet, independent_sha256=pin)
                result=copy.stage_originals_into_technical_bundle(bundle,originals,pin)
            self.assertFalse(result["customer_distribution_authorized"])

    def test_13_real_product_bundle_has_scoped_optional_license_hook(self):
        params=inspect.signature(life.build_private_qa_bundle).parameters
        self.assertIn("existing_owner_license_packet", params)
        self.assertIn("expected_owner_review_sha256", params)
        self.assertIsNone(params["existing_owner_license_packet"].default)
        self.assertIsNone(params["expected_owner_review_sha256"].default)


if __name__ == "__main__":
    unittest.main()
