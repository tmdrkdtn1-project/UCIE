"""W07/W09 first-party signed-Rulepack Library, with real synthetic signatures.

Tests only use disposable UCIE-named synthetic directories and UCIE-owned
keys created in that temporary test root. No private host data, project scan,
external source execution, production signing or external GETs.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_ucie_owner_risk_release import RUN, SHA, fake_api
from ucie_public.rulepack import generate_keys
from ucie_public.mixed_release import (
    publish_mixed_owner_release, RULE_ORDER, CONFIRM, ELIGIBLE, FOURTH_CI,
)
from ucie_public.selected_release import EXPECTED_SECOND_CI, EXPECTED_THIRD_CI
from ucie_public.fifth_owner_addendum import RULE_ID
from ucie_miner.signed_rule_library import (
    SCHEMA, SignedLibraryError, inspect_signed_library,
    build_existing_pack_consumer_descriptor, main,
)


class W07W09SignedLibraryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "UCIE"
        (self.root / "build").mkdir(parents=True)
        self.private, self.trust = generate_keys(
            self.root / "owner-test-key", purpose="production")
        self.serial4 = self.root / "build" / "serial4-synthetic.zip"
        self.main_run, self.jobs = fake_api()

    def _publish_serial4(self):
        ids = list(RULE_ORDER)
        with (
            patch("ucie_public.mixed_release._local_clean_sha",
                  return_value=SHA),
            patch("ucie_public.owner_release._public_json",
                  side_effect=[self.main_run, self.jobs]),
            patch("ucie_public.mixed_release._postfix_ci",
                  return_value=EXPECTED_SECOND_CI),
            patch("ucie_public.mixed_release._third_ci",
                  return_value=EXPECTED_THIRD_CI),
            patch("ucie_public.mixed_release._fourth_ci",
                  return_value=FOURTH_CI),
        ):
            publish_mixed_owner_release(
                self.root, self.private, self.serial4, run_id=RUN, serial=4,
                rule_ids=ids, confirmation=CONFIRM,
                risk_acceptances={rule: ELIGIBLE[rule][2] for rule in ids})

    def test_genuine_cryptographic_serial4_produces_only_signed_rule_shelf(self):
        self._publish_serial4()
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("W07 must not GET")):
            result = inspect_signed_library(
                self.root, serial4_pack=self.serial4,
                owner_public_trust=self.trust)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["signed_rule_count"], 4)
        self.assertEqual([r["rule_id"] for r in result["items"]],
                         list(RULE_ORDER))
        self.assertEqual(len({r["item_id"] for r in result["items"]}), 4)
        self.assertEqual(result["unsigned_candidate_records_imported"], 0)
        self.assertTrue(all(r["verification"] ==
                            "OWNER_SIGNED_VERIFIED_AT_INSPECTION_TIME"
                            and r["approval_basis"] == "OWNER_RISK_ACCEPTED_CI_ONLY"
                            and r["independent_qa_approved"] is False
                            and r["license_signoff"] is False
                            and r["new_package_export_allowed"] is False
                            for r in result["items"]))
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["database_writes"], 0)
        self.assertFalse(result["new_release_approved"])
        self.assertFalse(result["v1_library_accepted"])

    def test_w09_descriptor_is_bound_to_same_genuine_signed_pack(self):
        self._publish_serial4()
        original = self.serial4.read_bytes()
        descriptor = build_existing_pack_consumer_descriptor(
            self.root, serial4_pack=self.serial4,
            owner_public_trust=self.trust)
        self.assertEqual(self.serial4.read_bytes(), original)
        self.assertEqual(descriptor["package_type"],
                         "REFERENCE_TO_EXISTING_SIGNED_RULEPACKS_ONLY")
        self.assertEqual(len(descriptor["rules"]), 4)
        self.assertEqual(len(descriptor["descriptor_sha256"]), 64)
        self.assertFalse(descriptor["new_package_export_allowed"])
        self.assertFalse(descriptor["new_signature_or_approval_created"])
        self.assertFalse(descriptor["w09_generic_skill_engine_packaging_complete"])
        self.assertEqual(descriptor["database_writes"], 0)
        self.assertNotIn(str(self.root), json.dumps(descriptor))

    def test_unsigned_or_tampered_zip_never_reaches_shelf_or_w09(self):
        self._publish_serial4()
        tampered = self.root / "build" / "unsigned-four.zip"
        tampered.write_bytes(b"THIS IS NOT A SIGNED UCIE RULEPACK")
        for path in (tampered,):
            with self.subTest(path=path):
                with self.assertRaises(SignedLibraryError):
                    inspect_signed_library(
                        self.root, serial4_pack=path,
                        owner_public_trust=self.trust)
                with self.assertRaises(SignedLibraryError):
                    build_existing_pack_consumer_descriptor(
                        self.root, serial4_pack=path,
                        owner_public_trust=self.trust)

    def test_bad_public_key_or_expired_signed_pack_fail_closed(self):
        self._publish_serial4()
        _, untrusted = generate_keys(
            self.root / "other-synthetic-trust", purpose="production")
        with self.assertRaises(SignedLibraryError):
            inspect_signed_library(
                self.root, serial4_pack=self.serial4,
                owner_public_trust=untrusted)
        with self.assertRaises(SignedLibraryError):
            inspect_signed_library(
                self.root, serial4_pack=self.serial4,
                owner_public_trust=self.trust,
                at_time=datetime.now(timezone.utc) + timedelta(days=8))

    def test_no_arbitrary_project_paths_and_no_private_key_input(self):
        self._publish_serial4()
        other_temp = tempfile.TemporaryDirectory()
        self.addCleanup(other_temp.cleanup)
        outsider = Path(other_temp.name) / "some-other-project.zip"
        outsider.write_bytes(b"NOT UCIE")
        with self.assertRaises(SignedLibraryError):
            inspect_signed_library(
                self.root, serial4_pack=outsider,
                owner_public_trust=self.trust)
        with self.assertRaises(SignedLibraryError):
            inspect_signed_library(
                self.root, serial4_pack=self.serial4,
                owner_public_trust=outsider)
        # Supplying a private PEM instead of an owner PUBLIC trust file must
        # fail at the original public-key cryptographic verifier.
        with self.assertRaises(SignedLibraryError):
            inspect_signed_library(
                self.root, serial4_pack=self.serial4,
                owner_public_trust=self.private)

    def test_serial5_requires_fresh_original_crypto_verifier_and_parent(self):
        self._publish_serial4()
        synthetic_addendum = self.root / "build" / "fifth-unsigned.zip"
        synthetic_addendum.write_bytes(b"NOT A VALID SIGNED ADDENDUM")
        with self.assertRaises(SignedLibraryError):
            inspect_signed_library(
                self.root, serial4_pack=self.serial4,
                owner_public_trust=self.trust,
                serial5_pack=synthetic_addendum)
        # Dependency injection here tests *the W07 call boundary only*;
        # all genuine Serial5 crypto paths are separately tested in the
        # existing test_ucie_fifth_owner_addendum.py.
        good_base = {
            "result": "MIXED_OWNER_PUBLIC_MANUAL_PACK_VERIFIED",
            "owner_signature": "VALID", "serial": 4,
            "rule_ids": list(RULE_ORDER), "rule_count": 4,
            "scope": "PUBLIC_ONLY_MANUAL_STATIC_SCAN",
            "auto_apply": False,
            "independent_human_qa_approved": False,
            "legal_license_signoff": False,
        }
        good_fifth = {
            "result": "FIFTH_OWNER_RISK_ADDENDUM_VERIFIED",
            "serial": 5, "parent_serial": 4, "parent_rule_count": 4,
            "additional_signed_rules": 1, "rule_id": RULE_ID,
            "scope": "PUBLIC_ONLY_MANUAL_STATIC_SCAN",
            "owner_signature": "VALID", "auto_apply": False,
            "independent_human_qa_approved": False,
            "legal_license_signoff": False,
        }
        with (
            patch("ucie_miner.signed_rule_library.verify_mixed_owner_release",
                  return_value=good_base) as base_verify,
            patch("ucie_miner.signed_rule_library.verify_fifth_addendum",
                  return_value=good_fifth) as addendum_verify,
        ):
            result = inspect_signed_library(
                self.root, serial4_pack=self.serial4,
                owner_public_trust=self.trust,
                serial5_pack=synthetic_addendum)
        self.assertEqual(result["signed_rule_count"], 5)
        self.assertEqual(result["items"][-1]["rule_id"], RULE_ID)
        self.assertEqual(result["items"][-1]["parent_package_sha256"],
                         result["source_pack_sha256s"]["serial4"])
        base_verify.assert_called_once()
        addendum_verify.assert_called_once()
        self.assertEqual(addendum_verify.call_args.args[:3],
                         (synthetic_addendum, self.serial4, self.trust))

    def test_signed_verifier_receipt_shape_drift_does_not_promote(self):
        self._publish_serial4()
        fake = {
            "result": "MIXED_OWNER_PUBLIC_MANUAL_PACK_VERIFIED",
            "owner_signature": "VALID", "serial": 4,
            "rule_ids": list(RULE_ORDER), "rule_count": 4,
            "scope": "PUBLIC_ONLY_MANUAL_STATIC_SCAN",
            "auto_apply": False,
            "independent_human_qa_approved": False,
            "legal_license_signoff": False,
        }
        fake["independent_human_qa_approved"] = True
        with patch("ucie_miner.signed_rule_library.verify_mixed_owner_release",
                   return_value=fake):
            with self.assertRaises(SignedLibraryError):
                inspect_signed_library(
                    self.root, serial4_pack=self.serial4,
                    owner_public_trust=self.trust)

    def test_cli_requires_explicit_paths_and_real_signature(self):
        self._publish_serial4()
        args = ["signed_rule_library", "--ucie-root", str(self.root),
                "--serial4-pack", str(self.serial4),
                "--owner-public-trust", str(self.trust),
                "--descriptor"]
        with patch("sys.argv", args), patch("builtins.print") as render:
            self.assertEqual(main(), 0)
        result = json.loads(render.call_args.args[0])
        self.assertFalse(result["new_package_export_allowed"])
        with patch("sys.argv", args + ["--serial5-pack",
                                      str(self.root / "nonexistent.zip")]):
            with patch("builtins.print") as render:
                self.assertEqual(main(), 2)
        self.assertEqual(
            json.loads(render.call_args.args[0])["status"],
            "SIGNED_LIBRARY_VERIFICATION_REQUIRED_NO_GO")


if __name__ == "__main__":
    unittest.main()
