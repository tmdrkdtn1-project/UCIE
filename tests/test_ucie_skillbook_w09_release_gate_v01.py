"""UCIE W09 receipt validation, no export/signing/auto-approval."""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from hashlib import sha256
from io import StringIO
import json
from unittest import TestCase
from unittest.mock import patch

from ucie_miner import skillbook_w09_release_gate_v01 as gate
from ucie_miner import skillbook_scandir_qa_v01 as w08
from ucie_miner.skillbook_product_v01 import build_skillbook


def resign(receipt: dict) -> dict:
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    receipt["receipt_sha256"] = sha256(json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True).encode("ascii")).hexdigest()
    return receipt


class W09SkillBookGateTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = w08.evaluate_skillbook_scandir()
        assert cls.receipt["status"] == w08.PASS_STATE

    def test_actual_w08_receipt_integrity_but_release_blocked(self):
        report = gate.assess_release_readiness(deepcopy(self.receipt))
        self.assertEqual(report["schema"], gate.SCHEMA)
        self.assertEqual(report["status"], gate.VALIDATED_STATE)
        self.assertTrue(report["first_party_synthetic_receipt_integrity_pass"])
        self.assertTrue(report["source_identity_matches_current_checkout"])
        self.assertEqual(report["synthetic_cases_reported_pass"], 9)
        self.assertEqual(
            report["validated_first_party_receipt_sha256"],
            self.receipt["receipt_sha256"])
        self.assertEqual(len(report["blocked_release_requirements"]), 6)
        self.assertEqual(report["portable_package_bytes_produced"], 0)
        for key in ("exact_head_ci_matrix_attested", "independent_qa_verified",
                    "security_review_approved", "license_redistribution_approved",
                    "owner_release_authorized", "package_signed",
                    "export_allowed", "package_created", "model_training_performed",
                    "source_code_executed_by_gate", "other_project_access"):
            self.assertIs(report[key], False, key)
        digest = report.pop("report_sha256")
        self.assertEqual(digest, sha256(json.dumps(
            report, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True).encode("ascii")).hexdigest())
        print("UCIE_W09_GATE_FIRST_PARTY="
              + json.dumps({"receipt_validated": True,
                            "blocked_gates": 6,
                            "package_bytes": 0,
                            "export_allowed": False}, sort_keys=True))

    def test_repeatable_report(self):
        self.assertEqual(
            gate.assess_release_readiness(deepcopy(self.receipt)),
            gate.assess_release_readiness(deepcopy(self.receipt)))

    def test_modified_receipt_digest_rejected(self):
        wrong = deepcopy(self.receipt)
        wrong["cases"][0]["case_id"] = "FORGED"
        with self.assertRaises(gate.SkillBookReleaseGateError):
            gate.assess_release_readiness(wrong)
        wrong = deepcopy(self.receipt)
        wrong["receipt_sha256"] = "0" * 64
        with self.assertRaises(gate.SkillBookReleaseGateError):
            gate.assess_release_readiness(wrong)

    def test_forged_approval_still_denied_even_resigned(self):
        for key in ("independent_qa_verified", "human_approved", "export_allowed",
                    "license_redistribution_approved", "signed",
                    "security_review_approved", "other_project_access"):
            fake = resign(deepcopy(self.receipt))
            fake[key] = True
            resign(fake)
            with self.subTest(key=key), self.assertRaises(
                    gate.SkillBookReleaseGateError):
                gate.assess_release_readiness(fake)

    def test_missing_extra_field_and_case_injection_rejected(self):
        for mutation in (
                lambda r: r.pop("case_count"),
                lambda r: r.update(approval_override="OWNER"),
                lambda r: r["cases"].append(r["cases"][0]),
                lambda r: r["cases"][0].update(synthetic_only=1),
                lambda r: r["cases"][0].update(status="SKIPPED"),
                lambda r: r.update(passed_count=True),
                lambda r: r.update(python_runtime="../../etc")):
            fake = deepcopy(self.receipt)
            mutation(fake)
            resign(fake)
            with self.subTest(mutation=mutation), self.assertRaises(
                    gate.SkillBookReleaseGateError):
                gate.assess_release_readiness(fake)

    def test_source_drift_even_valid_resigned_receipt_rejected(self):
        fake = deepcopy(self.receipt)
        fake["recipe_source_sha256"] = "0" * 64
        resign(fake)
        with self.assertRaises(gate.SkillBookReleaseGateError):
            gate.assess_release_readiness(fake)
        with patch.object(gate, "_source_sha256", return_value="0" * 64):
            with self.assertRaises(gate.SkillBookReleaseGateError):
                gate.assess_release_readiness(deepcopy(self.receipt))

    def test_forged_product_approval_denied(self):
        fake = build_skillbook()
        fake["proof_gates"]["signed"] = True
        with patch.object(gate, "build_skillbook", return_value=fake):
            with self.assertRaises(gate.SkillBookReleaseGateError):
                gate.assess_release_readiness(deepcopy(self.receipt))

    def test_no_receipt_preview_never_executes_test(self):
        with patch.object(w08, "evaluate_skillbook_scandir",
                          side_effect=AssertionError("unsolicited execution")):
            preview = gate.preview_release_gate()
            self.assertEqual(preview["status"], gate.PREVIEW_STATE)
            self.assertFalse(preview["package_created"])
            self.assertFalse(preview["receipt_validation_performed"])
            buf = StringIO()
            with redirect_stdout(buf):
                result = gate.main([])
            self.assertEqual(result, 0)
            self.assertFalse(json.loads(buf.getvalue())["export_allowed"])

    def test_manual_synthetic_command_no_export(self):
        buf = StringIO()
        with redirect_stdout(buf):
            result = gate.main(["--run-synthetic"])
        self.assertEqual(result, 0)
        report = json.loads(buf.getvalue())
        self.assertEqual(report["status"], gate.VALIDATED_STATE)
        self.assertFalse(report["owner_release_authorized"])
        self.assertFalse(report["export_allowed"])
        self.assertFalse(report["package_created"])

    def test_cli_corrupted_receipt_fail_closed(self):
        bad = deepcopy(self.receipt)
        bad["source_code_executed"] = True
        buf = StringIO()
        with patch.object(w08, "evaluate_skillbook_scandir", return_value=bad):
            with redirect_stdout(buf):
                result = gate.main(["--run-synthetic"])
        self.assertEqual(result, 2)
        report = json.loads(buf.getvalue())
        self.assertEqual(report["status"], gate.INVALID_STATE)
        self.assertFalse(report["package_created"])
        self.assertFalse(report["export_allowed"])


if __name__ == "__main__":
    import unittest
    unittest.main()
