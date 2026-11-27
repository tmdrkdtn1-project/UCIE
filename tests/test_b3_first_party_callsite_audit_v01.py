"""Bounded actual first-party callsite audit and fake-source negative controls."""
import unittest
from unittest.mock import patch

from ucie_miner import b3_first_party_callsite_audit_v01 as audit


class UCIEFirstPartyCallsiteAuditTests(unittest.TestCase):
    def test_existing_ucie_recipe_uses_explicit_directory_not_minus_one(self):
        result = audit.audit_trusted_scandir_recipe()
        self.assertEqual(result["function_name"], "bounded_regular_file_names")
        self.assertEqual(result["direct_os_scandir_calls"], 1)
        self.assertTrue(result["expected_direct_call_shape"])
        self.assertTrue(result["explicit_directory_argument"])
        self.assertEqual(
            result["negative_fd_risk_for_this_static_callsite"],
            "NOT_INDICATED_BY_DIRECT_AST")
        self.assertEqual(result["other_callers_and_customer_code"], "NOT_INSPECTED")
        self.assertEqual(result["actual_runtime_compatibility"], "NOT_VERIFIED")
        self.assertFalse(result["automatic_fix_applied"])
        self.assertFalse(result["release_approved"])

    def test_unavailable_source_fails_closed(self):
        with patch.object(audit.inspect, "getsource", side_effect=OSError("no source")):
            with self.assertRaisesRegex(
                audit.CallsiteAuditError, "NOT_INSPECTABLE"):
                audit.audit_trusted_scandir_recipe()

    def test_unexpected_call_shape_cannot_be_misclassified_safe(self):
        from inspect import getsource
        original = getsource(audit.bounded_regular_file_names)
        # Static fake source for negative control; not executed.
        fake = original.replace("os.scandir(directory)", "os.scandir(-1)")
        self.assertNotEqual(original, fake)
        with patch.object(audit.inspect, "getsource", return_value=fake):
            result = audit.audit_trusted_scandir_recipe()
        self.assertFalse(result["explicit_directory_argument"])
        self.assertEqual(
            result["negative_fd_risk_for_this_static_callsite"], "UNKNOWN_HOLD")
        self.assertFalse(result["release_approved"])

    def test_actual_function_source_receipt_is_stable(self):
        self.assertEqual(
            audit.audit_trusted_scandir_recipe()["receipt_sha256"],
            audit.audit_trusted_scandir_recipe()["receipt_sha256"])


if __name__ == "__main__":
    unittest.main()
