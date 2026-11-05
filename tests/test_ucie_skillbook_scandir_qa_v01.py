"""First-party synthetic receipt and fail-closed tests for SkillBook W08."""
from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from ucie_miner import skillbook_scandir_qa_v01 as qa
from ucie_miner.skillbook_product_v01 import build_skillbook


class SkillBookScandirQATests(unittest.TestCase):
    def test_real_synthetic_experiment_and_hash(self):
        actual = qa.evaluate_skillbook_scandir()
        self.assertEqual(actual["schema"], qa.SCHEMA)
        self.assertEqual(actual["status"], qa.PASS_STATE)
        self.assertEqual(actual["case_count"], 9)
        self.assertEqual(actual["passed_count"], 9)
        self.assertEqual(actual["failed_count"], 0)
        self.assertEqual(
            [c["case_id"] for c in actual["cases"]],
            [case_id for case_id, _ in qa.CASES])
        self.assertTrue(all(c["status"] == "PASS" for c in actual["cases"]))
        self.assertFalse(actual["export_allowed"])
        self.assertFalse(actual["independent_qa_verified"])
        self.assertFalse(actual["actual_owner_directory_scanned"])
        self.assertFalse(actual["other_project_access"])
        self.assertEqual(actual["operating_database_writes"], 0)
        self.assertEqual(actual["public_network_requests"], 0)
        source = Path(qa.__file__).with_name(qa.SOURCE_FILE).read_bytes()
        self.assertEqual(
            actual["recipe_source_sha256"],
            hashlib.sha256(source).hexdigest())
        receipt = dict(actual)
        checksum = receipt.pop("receipt_sha256")
        self.assertEqual(checksum, hashlib.sha256(json.dumps(
            receipt, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True).encode("ascii")).hexdigest())
        print("UCIE_W08_SKILLBOOK_SYNTHETIC_QA="
              + json.dumps({
                  "cases": actual["case_count"],
                  "passed": actual["passed_count"],
                  "failed": actual["failed_count"],
                  "receipt_sha256": actual["receipt_sha256"],
                  "owner_data_scanned": False,
              }, separators=(",", ":"), sort_keys=True))

    def test_same_source_same_interpreter_deterministic_receipt(self):
        a = qa.evaluate_skillbook_scandir()
        b = qa.evaluate_skillbook_scandir()
        self.assertEqual(a, b)

    def test_broken_recipe_cannot_be_reported_pass(self):
        with patch.object(
                qa, "bounded_regular_file_names",
                return_value=("FORGED_OUTPUT.txt",)):
            r = qa.evaluate_skillbook_scandir()
        self.assertEqual(r["status"], qa.FAIL_STATE)
        self.assertGreater(r["failed_count"], 0)
        self.assertLess(r["passed_count"], r["case_count"])
        self.assertFalse(r["export_allowed"])
        self.assertFalse(r["independent_qa_verified"])

    def test_forged_approval_or_evidence_identity_denied(self):
        for mutate in (
                lambda r: r.update(export_allowed=True),
                lambda r: r["proof_gates"].update(independent_test_verified=True),
                lambda r: r["source_evidence"].update(
                    source_document_sha256="0" * 64),
                lambda r: r.update(skillbook_id="../UNSAFE")):
            fake = build_skillbook()
            mutate(fake)
            with self.subTest(mutate=mutate), patch.object(
                    qa, "build_skillbook", return_value=fake):
                with self.assertRaises(qa.SkillBookQAError):
                    qa.evaluate_skillbook_scandir()

    def test_cli_prints_one_readonly_json_receipt(self):
        out = StringIO()
        with redirect_stdout(out):
            rc = qa.main()
        self.assertEqual(rc, 0)
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        receipt = json.loads(lines[0])
        self.assertEqual(receipt["status"], qa.PASS_STATE)
        self.assertFalse(receipt["signed"])
        self.assertFalse(receipt["license_redistribution_approved"])
        self.assertTrue(receipt["temporary_synthetic_fixture_writes"])

    def test_cli_fail_closed_if_source_identity_breaks(self):
        fake = build_skillbook()
        fake["source_evidence"]["source_document_sha256"] = "0" * 64
        out = StringIO()
        with patch.object(qa, "build_skillbook", return_value=fake), \
                redirect_stdout(out):
            rc = qa.main()
        self.assertEqual(rc, 2)
        parsed = json.loads(out.getvalue())
        self.assertEqual(parsed["status"], qa.FAIL_STATE)
        self.assertFalse(parsed["receipt_created"])
        self.assertFalse(parsed["export_allowed"])


if __name__ == "__main__":
    unittest.main()
