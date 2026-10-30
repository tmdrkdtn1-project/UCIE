"""W07/W09 first-party signed-Rulepack Library, with real synthetic signatures.

Tests only use disposable UCIE-named synthetic directories and UCIE-owned
keys created in that temporary test root. No private host data, project scan,
external source execution, production signing or external GETs.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
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
from ucie_miner import product_v1 as product
from ucie_miner.product_v1 import integrated_product_preview
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

    def test_product_selection_requires_actual_signed_pack_and_limits_manual_scope(self):
        self._publish_serial4()
        (self.root / "runtime").mkdir(exist_ok=True)
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("UCIE preview must not fetch")):
            first = integrated_product_preview(
                self.root, limit=20,
                signed_serial4=self.serial4,
                owner_public_trust=self.trust)
            choices = first["reuse_eligibility"]["items"]
            signed = [x for x in choices if x["shelf"] == "SIGNED_MANUAL_RULE"]
            self.assertEqual(len(signed), 4)
            self.assertEqual(
                first["reuse_eligibility"]["manual_reference_count_in_loaded_window"],
                4)
            self.assertEqual(
                first["reuse_eligibility"]["new_generic_package_exportable_count"],
                0)
            for item in signed:
                self.assertEqual(item["selection_status"],
                                 "EXISTING_OWNER_SIGNED_MANUAL_REFERENCE_ONLY")
                self.assertEqual(
                    item["permitted_action"],
                    "REFERENCE_EXISTING_VERIFIED_PACK_MANUALLY")
                self.assertTrue(
                    item["manual_reference_to_existing_pack_allowed"])
                self.assertFalse(item["new_generic_package_export_allowed"])
                self.assertEqual(item["source_package_sha256"],
                                 first["signed_rules"]
                                      ["source_pack_metadata"]["serial4"])
                self.assertEqual(item["approval_basis"],
                                 "OWNER_RISK_ACCEPTED_CI_ONLY")
            selected = integrated_product_preview(
                self.root, limit=20,
                signed_serial4=self.serial4,
                owner_public_trust=self.trust,
                select_item_id=signed[0]["library_item_id"])
            self.assertEqual(
                selected["reuse_eligibility"]["selected_item"]
                ["library_item_id"], signed[0]["library_item_id"])
            self.assertFalse(selected["package_released"])
            self.assertFalse(selected["v1_accepted"])
            self.assertEqual(selected["operating_database_writes"], 0)
            absent = integrated_product_preview(
                self.root, limit=20,
                select_item_id=signed[0]["library_item_id"])
        self.assertEqual(
            absent["reuse_eligibility"]["selected_item"]["selection_status"],
            "NOT_IN_CURRENT_BOUNDED_QUERY_WINDOW_NO_GO")
        self.assertEqual(
            absent["reuse_eligibility"]["manual_reference_count_in_loaded_window"],
            0)

    def test_selected_signed_rule_gets_fresh_w09_readonly_consumer_reference(self):
        self._publish_serial4()
        (self.root / "runtime").mkdir(exist_ok=True)
        original = self.serial4.read_bytes()
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("selected W09 reference must not fetch")):
            catalog = integrated_product_preview(
                self.root, limit=20,
                signed_serial4=self.serial4,
                owner_public_trust=self.trust)
            choice = next(x for x in catalog["reuse_eligibility"]["items"]
                          if x["shelf"] == "SIGNED_MANUAL_RULE")
            selected = integrated_product_preview(
                self.root, limit=20,
                signed_serial4=self.serial4,
                owner_public_trust=self.trust,
                select_item_id=choice["library_item_id"],
                include_consumer_reference=True)
        handoff = selected["selected_existing_w09_consumer_reference"]
        self.assertEqual(handoff["status"],
                         "EXISTING_SIGNED_MANUAL_REFERENCE_VERIFIED_NOT_RELEASED")
        self.assertEqual(handoff["selected_library_item_id"],
                         choice["library_item_id"])
        self.assertEqual(handoff["rule_id"], choice["rule_id"])
        self.assertEqual(handoff["pack_serial"], 4)
        self.assertEqual(handoff["source_package_sha256"],
                         choice["source_package_sha256"])
        self.assertEqual(handoff["parent_serial4_sha256"],
                         choice["source_package_sha256"])
        # Compare with the actual original W09 descriptor, not an
        # independently invented product-level descriptor or signing scheme.
        original_w09 = build_existing_pack_consumer_descriptor(
            self.root, serial4_pack=self.serial4,
            owner_public_trust=self.trust)
        self.assertEqual(handoff["existing_w09_descriptor_sha256"],
                         original_w09["descriptor_sha256"])
        self.assertTrue(handoff["original_pack_reverified_at_handoff"])
        self.assertEqual(handoff["consumer_instruction"],
                         original_w09["consumer_instructions"])
        self.assertFalse(handoff["consumer_signature_verified_after_handoff"])
        self.assertFalse(handoff["new_generic_package_export_allowed"])
        self.assertFalse(handoff["automatic_rule_application_allowed"])
        self.assertFalse(handoff["pack_bytes_copied"])
        self.assertFalse(handoff["package_released"])
        self.assertFalse(selected["v1_accepted"])
        self.assertEqual(selected["operating_database_writes"], 0)
        self.assertEqual(self.serial4.read_bytes(), original)

        # Exercise the actual user-facing single command, not only the API.
        with patch("sys.argv", [
            "product_v1", "--ucie-root", str(self.root),
            "--limit", "20", "--serial4-pack", str(self.serial4),
            "--owner-public-trust", str(self.trust),
            "--select-item", choice["library_item_id"],
            "--consumer-reference",
        ]):
            with patch("builtins.print") as printed:
                self.assertEqual(product.main(), 0)
        cli = json.loads(printed.call_args.args[0])
        self.assertEqual(
            cli["selected_existing_w09_consumer_reference"],
            handoff)
        self.assertFalse(cli["package_released"])
        self.assertFalse(cli["v1_accepted"])
        self.assertEqual(self.serial4.read_bytes(), original)

        # Forged old W09 receipt is not sufficient at the new handoff.
        for change in (
            {"descriptor_sha256": "f" * 64},
            {"new_package_export_allowed": True},
            {"rules": [{**original_w09["rules"][0],
                        "rule_id": "FORGED_WRONG_RULE"}]},
        ):
            with self.subTest(change=change):
                forged = {**original_w09, **change}
                with patch(
                    "ucie_miner.signed_rule_library."
                    "build_existing_pack_consumer_descriptor",
                    return_value=forged,
                ):
                    with self.assertRaisesRegex(
                            ValueError, "descriptor|identity"):
                        integrated_product_preview(
                            self.root, limit=20,
                            signed_serial4=self.serial4,
                            owner_public_trust=self.trust,
                            select_item_id=choice["library_item_id"],
                            include_consumer_reference=True)

        # Once the signed original changes, the next lookup does not
        # reuse its earlier successful verification.
        self.serial4.write_bytes(b"UNSIGNED_TAMPERED_PACK")
        with self.assertRaises(ValueError):
            integrated_product_preview(
                self.root, limit=20,
                signed_serial4=self.serial4,
                owner_public_trust=self.trust,
                select_item_id=choice["library_item_id"],
                include_consumer_reference=True)

    def test_real_consumer_reverifies_original_signed_manual_reference(self):
        from ucie_miner.manual_consumer_v1 import (
            consume_existing_manual_reference, SCHEMA as CONSUMER_SCHEMA,
        )
        self._publish_serial4()
        (self.root / "runtime").mkdir(exist_ok=True)
        original = self.serial4.read_bytes()
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("manual consumer must not fetch")):
            catalog = integrated_product_preview(
                self.root, limit=20, signed_serial4=self.serial4,
                owner_public_trust=self.trust)
            first_id = next(row["library_item_id"]
                            for row in catalog["reuse_eligibility"]["items"]
                            if row["shelf"] == "SIGNED_MANUAL_RULE")
            producer = integrated_product_preview(
                self.root, limit=20, signed_serial4=self.serial4,
                owner_public_trust=self.trust, select_item_id=first_id,
                include_consumer_reference=True)
            ref = producer["selected_existing_w09_consumer_reference"]
            consumed = consume_existing_manual_reference(
                self.root, reference=ref,
                serial4_pack=self.serial4, owner_public_trust=self.trust)
        self.assertEqual(consumed["schema"], CONSUMER_SCHEMA)
        self.assertEqual(consumed["status"],
                         "ORIGINAL_SIGNED_RULE_REVERIFIED_MANUAL_REFERENCE_ONLY")
        self.assertTrue(
            consumed["original_signature_trust_and_expiry_reverified_in_consumer"])
        self.assertEqual(consumed["selected_library_item_id"], first_id)
        self.assertEqual(consumed["source_pack_sha256"],
                         ref["source_package_sha256"])
        self.assertEqual(consumed["w09_descriptor_sha256"],
                         ref["existing_w09_descriptor_sha256"])
        self.assertFalse(consumed["actual_rule_scan_executed"])
        self.assertFalse(consumed["new_generic_package_export_allowed"])
        self.assertFalse(consumed["automatic_rule_application_allowed"])
        self.assertFalse(consumed["pack_bytes_copied"])
        self.assertFalse(consumed["package_released"])
        self.assertFalse(consumed["v1_accepted"])
        self.assertEqual(consumed["network_requests"], 0)
        self.assertEqual(consumed["operating_database_writes"], 0)
        self.assertEqual(self.serial4.read_bytes(), original)

        # The independent consumer has its own Python process, input JSON
        # and fresh cryptographic verification; not a producer function call.
        runner = (
            "import runpy,sys\n"
            "sys.path.insert(0,sys.argv[1])\n"
            "sys.argv=['manual_consumer_v1',*sys.argv[2:]]\n"
            "runpy.run_module('ucie_miner.manual_consumer_v1',"
            "run_name='__main__')\n"
        )
        command = [
            sys.executable, "-I", "-B", "-c", runner,
            str(Path(__file__).resolve().parents[1] / "src"),
            "--ucie-root", str(self.root),
            "--serial4-pack", str(self.serial4),
            "--owner-public-trust", str(self.trust),
        ]
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        payload = json.dumps(ref, ensure_ascii=True, sort_keys=True)
        def run_consumer(raw: str, args: list[str] | None = None):
            return subprocess.run(
                command if args is None else args, input=raw,
                capture_output=True, encoding="utf-8", errors="replace",
                env=env, cwd=self.root, check=False, timeout=45)
        process = run_consumer(payload)
        self.assertEqual(process.returncode, 0, process.stderr[-800:])
        child = json.loads(process.stdout)
        self.assertEqual(child, consumed)
        self.assertNotIn(str(self.root), process.stdout)
        self.assertEqual(self.serial4.read_bytes(), original)

        # Every replayed/forged version and approval flag must fail closed.
        changes = (
            {"rule_id": "FORGED_RULE"},
            {"pack_serial": 5},
            {"source_package_sha256": "a" * 64},
            {"parent_serial4_sha256": "b" * 64},
            {"existing_w09_descriptor_sha256": "c" * 64},
            {"new_generic_package_export_allowed": True},
            {"automatic_rule_application_allowed": True},
            {"consumer_signature_verified_after_handoff": True},
            {"manual_scope": "ANY_PROJECT"},
            {"unexpected_authorization": True},
        )
        from ucie_miner.manual_consumer_v1 import ManualConsumerError
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(ManualConsumerError):
                    consume_existing_manual_reference(
                        self.root, reference={**ref, **change},
                        serial4_pack=self.serial4, owner_public_trust=self.trust)
        for bad in (
            payload.replace('"status":', '"status":"X","status":', 1),
            "{not-json", " " * 4097,
            json.dumps({**ref, "new_generic_package_export_allowed": True}),
        ):
            process = run_consumer(bad)
            self.assertEqual(process.returncode, 2, process.stdout[-800:])
            self.assertEqual(
                json.loads(process.stdout)["status"],
                "MANUAL_CONSUMER_FAIL_CLOSED")
            self.assertNotIn(str(self.root), process.stdout)

        _, outsider_trust = generate_keys(
            self.root / "invalid-consumer-trust", purpose="production")
        with self.assertRaises(ManualConsumerError):
            consume_existing_manual_reference(
                self.root, reference=ref,
                serial4_pack=self.serial4, owner_public_trust=outsider_trust)
        bad_trust_cmd = command[:-1] + [str(outsider_trust)]
        process = run_consumer(payload, args=bad_trust_cmd)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(
            json.loads(process.stdout)["status"], "MANUAL_CONSUMER_FAIL_CLOSED")

        self.serial4.write_bytes(b"TAMPERED_AFTER_PRODUCER")
        with self.assertRaises(ManualConsumerError):
            consume_existing_manual_reference(
                self.root, reference=ref,
                serial4_pack=self.serial4, owner_public_trust=self.trust)
        process = run_consumer(payload)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(
            json.loads(process.stdout)["status"], "MANUAL_CONSUMER_FAIL_CLOSED")

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
