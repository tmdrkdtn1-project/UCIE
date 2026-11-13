"""One real Win-only installed lifecycle; strict read-only/unit checks everywhere."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

from ucie_miner import customer_private_offline_lifecycle_v01 as life
from ucie_miner import customer_private_entitlement_v01 as c3
from ucie_miner import local_public_pr_owner_auth_v01 as auth
from ucie_miner.customer_staging_v01 import PILLARS


class CustomerOfflineLifecycleSafetyTests(unittest.TestCase):
    def test_01_no_implicit_commercial_release_from_spdx_or_manifest(self):
        rows = [
            {"distribution": "ucie-public-only-demo", "version": "0.1.0", "sha256": "a"*64},
            {"distribution": "cryptography", "version": "50.0.2", "sha256": "b"*64},
        ]
        document=life._sbom(rows,"a"*64)
        self.assertEqual(document["spdxVersion"], "SPDX-2.3")
        self.assertEqual(document["packages"][0]["licenseDeclared"], "NOASSERTION")
        self.assertEqual(document["packages"][1]["licenseConcluded"], "NOASSERTION")
        self.assertIn("NOT CUSTOMER APPROVED", life.NOTICE)
        self.assertIn("NO_GO", life.NO_GO)

    def test_02_recipient_path_and_checkout_ownership_boundaries(self):
        with TemporaryDirectory(prefix="UCIE_B3B4_INERT_ROOT_") as tmp:
            root=Path(tmp)/life.RECIPIENT_NAME
            self.assertEqual(life._recipient(root),root)
            root.mkdir()
            (root/".git").mkdir()
            with self.assertRaises(ValueError):
                life._recipient(root)
            (root/".git").rmdir()
            (root/"unexpected-user-data.txt").write_text("no overwrite")
            with self.assertRaises(ValueError):
                life._recipient(root)
            self.assertTrue((root/"unexpected-user-data.txt").exists())
            with self.assertRaises(ValueError):
                life._recipient(Path(tmp)/"UCIE")

    def test_03_pointer_rejects_malformed_and_duplicate_authority(self):
        with TemporaryDirectory(prefix="UCIE_B3B4_PTR_") as tmp:
            root=Path(tmp)/life.RECIPIENT_NAME
            root.mkdir()
            self.assertIsNone(life._active(root))
            with (root/"active.json").open("wb") as f:
                f.write(b'{"schema":"x","schema":"y"}\n')
            with self.assertRaises(ValueError):
                life._active(root)
            (root/"active.json").write_bytes(life._canon({
                "schema":life.SCHEMA,"active_slot":"../other",
                "previous_slot":None,"customer_distribution_authorized":False}))
            with self.assertRaises(ValueError):
                life._active(root)

    def test_04_atomic_first_select_then_rollback_pointer(self):
        with TemporaryDirectory(prefix="UCIE_B3B4_SELECT_") as tmp:
            root=Path(tmp)/life.RECIPIENT_NAME
            root.mkdir()
            life._pointer(root,"a"*16,None)
            self.assertEqual(life._active(root)["active_slot"],"a"*16)
            life._pointer(root,"b"*16,"a"*16)
            self.assertEqual(life._active(root)["previous_slot"],"a"*16)
            self.assertFalse((root/"active.pending.json").exists())
            self.assertFalse(life._active(root)["customer_distribution_authorized"])

    def test_05_pending_switch_never_overwritten_after_crash(self):
        with TemporaryDirectory(prefix="UCIE_B3B4_PENDING_") as tmp:
            root=Path(tmp)/life.RECIPIENT_NAME
            root.mkdir()
            (root/"active.pending.json").write_text("manual reconciliation", "utf-8")
            with self.assertRaises(ValueError):
                life._pointer(root,"a"*16,None)
            self.assertFalse((root/"active.json").exists())

    def test_06_versioned_candidate_only_two_expected_versions(self):
        self.assertEqual(set(life.PRODUCT_NAMES),set(c3.SUPPORTED_VERSIONS))
        self.assertEqual(set(life.PRODUCT_NAMES.values()),{
            "ucie_public_only_demo-0.1.0-py3-none-any.whl",
            "ucie_public_only_demo-0.1.1-py3-none-any.whl",
        })

    def test_07_install_and_uninstall_require_exact_consent_before_write(self):
        with TemporaryDirectory(prefix="UCIE_B3B4_NO_APPROVAL_") as tmp:
            root=Path(tmp)/life.RECIPIENT_NAME
            with self.assertRaises(ValueError):
                life.install_or_update(
                    root,Path(tmp)/life.RELEASE_NAME,python=Path("/none/python"),
                    public_pem=b"",expected_owner_key_id="a"*32,
                    expected_recipient_token_sha256="b"*64,
                    expected_rights_packet_sha256="c"*64,
                    min_serial=1,consent="no")
            self.assertFalse(root.exists())
            with self.assertRaises(ValueError):
                life.remove_technical_install(root,consent="yes")
            self.assertFalse(root.exists())

    def test_08_rollback_requires_valid_prior_slot_and_consent(self):
        with TemporaryDirectory(prefix="UCIE_B3B4_ROLLBACK_") as tmp:
            root=Path(tmp)/life.RECIPIENT_NAME
            with self.assertRaises(ValueError):
                life.rollback(root,public_pem=b"",
                              expected_owner_key_id="a"*32,
                              expected_recipient_token_sha256="b"*64,
                              expected_rights_packet_sha256="c"*64,
                              min_serial=1,consent="no")
            self.assertFalse(root.exists())

    def test_09_duplicate_fields_noncanonical_nan_and_oversize_fail(self):
        for data in (
            b'{"schema":"a","schema":"b"}\n', b'{"bad": NaN}\n',
            b"{}\nextra", b"{}\n "*2000, b"{}\r\n",
        ):
            with self.subTest(data=data[:40]),self.assertRaises(ValueError):
                life._parse(data,2000)

    def test_10_forged_bundle_absent_cannot_infer_signed_customer(self):
        with TemporaryDirectory(prefix="UCIE_B3B4_EMPTY_") as tmp:
            root=Path(tmp)/life.RELEASE_NAME
            root.mkdir()
            (root/"wheels").mkdir()
            with self.assertRaises(ValueError):
                life.verify_private_qa_bundle(
                    root,public_pem=b"not trusted",expected_owner_key_id="a"*32,
                    expected_recipient_token_sha256="b"*64,
                    expected_rights_packet_sha256="c"*64,min_serial=1)

    def test_11_no_unapproved_wheel_dirs_or_extra_contents(self):
        with TemporaryDirectory(prefix="UCIE_B3B4_WHEEL_") as tmp:
            root=Path(tmp)/"wheels"
            root.mkdir()
            for other in (None, "bad.whl"):
                with self.subTest(other=other):
                    if other:
                        (root/other).write_bytes(b"not a valid wheel")
                    with self.assertRaises(ValueError):
                        life._inventory(root)
                    if other:
                        (root/other).unlink()

    def test_12_outside_project_never_operated_by_uninstall(self):
        with TemporaryDirectory(prefix="UCIE_B3B4_NO_DELETE_") as tmp:
            root=Path(tmp)/life.RECIPIENT_NAME
            root.mkdir()
            (root/"keep-owner-data").write_text("DO NOT TOUCH","utf-8")
            with self.assertRaises(ValueError):
                life.remove_technical_install(root,consent=life.REMOVE_CONSENT)
            self.assertEqual((root/"keep-owner-data").read_text(),"DO NOT TOUCH")


class GenuineSignedUpgradeVersionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
            from ucie_public.rulepack import key_id
        except ImportError:
            raise unittest.SkipTest("Ed25519 unavailable; NOT production crypto PASS")
        cls.private=Ed25519PrivateKey.generate()
        cls.key_id=key_id(cls.private.public_key())
        cls.public=cls.private.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        cls.now=datetime.now(timezone.utc).replace(microsecond=0)

    def signed_version(self,version):
        record={
            "schema":c3.SCHEMA,"scope":c3.SCOPE,"product":c3.DIST,
            "product_version":version,
            "product_wheel_sha256":"a"*64,
            "vendor_wheels_sha256":{
                "cryptography":"b"*64,"cffi":"c"*64,"pycparser":"d"*64},
            "recipient_token_sha256":"e"*64,
            "rights_packet_sha256":"f"*64,
            "four_pillars":list(PILLARS),
            "serial":30,"owner_key_id":self.key_id,
            "issued_utc":auth._stamp(self.now),
            "expires_utc":auth._stamp(self.now+timedelta(days=30)),
        }
        a,b=c3.synthetic_fixture_signing_bytes(record,self.private)
        return a,b,dict(
            independently_provisioned_public_pem=self.public,
            expected_owner_key_id=self.key_id,min_serial=30,
            expected_recipient_token_sha256="e"*64,
            expected_product_wheel_sha256="a"*64,
            expected_vendor_wheels_sha256=record["vendor_wheels_sha256"],
            expected_rights_packet_sha256="f"*64,now=self.now)

    def test_13_two_real_cryptographic_signed_product_versions_exactly(self):
        for version in c3.SUPPORTED_VERSIONS:
            with self.subTest(version=version):
                body,sig,opts=self.signed_version(version)
                v=c3.verify_private_entitlement(
                    body,sig,expected_product_version=version,**opts)
                self.assertTrue(v["private_product_ed25519_signature_verified"])
                self.assertEqual(v["product_version"],version)
                self.assertFalse(v["customer_entitlement_issued"])

    def test_14_cross_version_substitution_denied(self):
        for version in c3.SUPPORTED_VERSIONS:
            body,sig,opts=self.signed_version(version)
            wrong="0.1.0" if version=="0.1.1" else "0.1.1"
            with self.assertRaises(ValueError):
                c3.verify_private_entitlement(
                    body,sig,expected_product_version=wrong,**opts)

    def test_15_unapproved_product_version_denied_even_if_signed(self):
        body,sig,opts=self.signed_version("0.1.2")
        with self.assertRaises(ValueError):
            c3.verify_private_entitlement(
                body,sig,expected_product_version="0.1.2",**opts)

    def test_16_wrong_signer_and_old_serial_bypass_denied(self):
        body,sig,opts=self.signed_version("0.1.1")
        with self.assertRaises(ValueError):
            c3.verify_private_entitlement(
                body,sig,expected_product_version="0.1.1",
                **dict(opts,min_serial=31))
        with self.assertRaises(ValueError):
            c3.verify_private_entitlement(
                body,sig,expected_product_version="0.1.1",
                **dict(opts,expected_owner_key_id="0"*32))


if __name__=="__main__":
    unittest.main()
