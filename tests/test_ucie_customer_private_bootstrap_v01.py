"""Standalone Windows offline bootstrap - no user files/keys without consent."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from ucie_miner import customer_private_offline_bootstrap_v01 as boot


class StandaloneOfflineBootstrapSafetyTests(unittest.TestCase):
    def args(self,dir:Path,**changes):
        raw=dict(
            bundle=dir/boot.BUNDLE_NAME,
            recipient_root=dir/boot.RECIPIENT_NAME,
            product_version="0.1.0",
            expected_product_sha256="a"*64,
            expected_cryptography_sha256="b"*64,
            expected_cffi_sha256="c"*64,
            expected_pycparser_sha256="d"*64,
            public_trust_pem=dir/"trust.pem",
            expected_owner_key_id="e"*32,
            recipient_token_sha256="f"*64,
            rights_packet_sha256="1"*64,
            min_serial=1,
            consent=boot.CONSENT,
        )
        raw.update(changes)
        return SimpleNamespace(**raw)

    def test_01_default_wrong_consent_blocks_before_writes(self):
        with TemporaryDirectory(prefix="UCIE_BOOT_") as tmp:
            root=Path(tmp)
            (root/boot.BUNDLE_NAME).mkdir()
            for wrong in ("", "yes", "UCIE_OWNER_PRIVATE_KEY_READ"):
                with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                    boot._preflight(self.args(root,consent=wrong))
            self.assertFalse((root/boot.RECIPIENT_NAME).exists())

    def test_02_rejects_wrong_target_names_and_owner_checkout(self):
        with TemporaryDirectory(prefix="UCIE_BOOT_") as tmp:
            root=Path(tmp)
            (root/boot.BUNDLE_NAME).mkdir()
            for changed in (
                {"recipient_root":root/"UCIE"},
                {"bundle":root/"another_project"},
                {"recipient_root":root/"nested"/boot.RECIPIENT_NAME},
                {"product_version":"9.9.9"},
                {"min_serial":0},
            ):
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    boot._preflight(self.args(root,**changed))

    def test_03_full_product_and_three_vendor_hashes_are_explicit_required(self):
        with TemporaryDirectory(prefix="UCIE_BOOT_") as tmp:
            for changed in (
                {"expected_product_sha256":"A"*64},
                {"expected_cryptography_sha256":"bad"},
                {"expected_cffi_sha256":"00"},
                {"expected_pycparser_sha256":"*"*64},
                {"recipient_token_sha256":"invalid"},
                {"rights_packet_sha256":"invalid"},
                {"expected_owner_key_id":"bad"},
            ):
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    boot._preflight(self.args(Path(tmp),**changed))

    def test_04_inert_fake_wheel_is_not_approved_or_imported(self):
        with TemporaryDirectory(prefix="UCIE_BOOT_") as tmp:
            file=Path(tmp)/"not_a_real.whl"
            file.write_bytes(b"untrusted")
            with self.assertRaises(ValueError):
                boot._size_hash(file)
            self.assertEqual(file.read_bytes(),b"untrusted")

    def test_05_real_sha256_of_only_expected_fixed_file(self):
        with TemporaryDirectory(prefix="UCIE_BOOT_") as tmp:
            file=Path(tmp)/"approved_candidate.whl"
            file.write_bytes(b"A"*400)
            self.assertEqual(boot._size_hash(file),sha256(b"A"*400).hexdigest())
            self.assertFalse((Path(tmp)/boot.RECIPIENT_NAME).exists())

    def test_06_no_owner_key_generation_or_external_url_import(self):
        self.assertFalse(hasattr(boot,"create_private_key"))
        self.assertFalse(hasattr(boot,"issue_customer_license"))
        self.assertNotIn("https://",boot.VERIFY_AND_STAGE)
        self.assertIn("--action","stage "+boot.VERIFY_AND_STAGE)
        self.assertIn("PIP_NO_INDEX",open(boot.__file__,encoding="utf-8").read())

    def test_07_unsigned_noncanonical_bundle_denied_before_verifier(self):
        with TemporaryDirectory(prefix="UCIE_BOOT_") as tmp:
            root=Path(tmp)
            wheel=root/boot.BUNDLE_NAME/"wheels"
            wheel.mkdir(parents=True)
            with self.assertRaises(ValueError):
                boot._preflight(self.args(root))
            self.assertFalse((root/boot.RECIPIENT_NAME).exists())

    def test_08_python3_runtime_no_preexisting_crypto_needed_to_parse(self):
        self.assertTrue(boot.STATUS.endswith("CUSTOMER_NO_GO"))
        self.assertIn(("cryptography","50.0.2"),boot.VENDORS)
        self.assertIn(("cffi","2.1.1"),boot.VENDORS)
        self.assertIn(("pycparser","3.12"),boot.VENDORS)
        self.assertEqual(boot.SUPPORTED_VERSIONS,("0.1.0","0.1.1"))
        self.assertNotIn("customer_distribution_authorized\":True",boot.VERIFY_AND_STAGE)

    def test_09_bad_bootstrap_consent_does_not_touch_operating_data(self):
        with TemporaryDirectory(prefix="UCIE_BOOT_") as tmp:
            root=Path(tmp)
            data=root/"operating_owner_data.txt"
            data.write_text("PRESERVE","utf-8")
            with self.assertRaises(ValueError):
                boot._preflight(self.args(root,consent="WRONG"))
            self.assertEqual(data.read_text(),"PRESERVE")


if __name__=="__main__":
    unittest.main()
