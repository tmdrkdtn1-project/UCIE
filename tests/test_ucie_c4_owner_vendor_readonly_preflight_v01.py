"""Owner real C1 evidence preflight only; never install vendor or run pip.

On GitHub CI this deliberately skips; it cannot claim owner wheels observed.
On D:/UCIE prints only boolean gates and pinned *public* source IDs.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest

from ucie_miner.customer_c4_owner_vendor_inplace_aba_v01 import (
    inspect_readonly, RECEIPT, ROOT, SCHEMA,
)
from ucie_miner.customer_owner_wheelhouse_acquire_v01 import RECEIPT as C1_RECEIPT


class C4OwnerExistingVendorBytePreflightTests(unittest.TestCase):
    def test_owner_three_captured_wheels_and_pinned_sources_without_exec(self):
        root = Path(__file__).resolve().parents[1]
        if (sys.platform != "win32"
                or root.resolve() != ROOT.resolve()
                or not (root / C1_RECEIPT).is_file()):
            self.skipTest("NOT_OWNER_WINDOWS_C1_CAPTURED_BYTES_UNAVAILABLE")
        capture = root / C1_RECEIPT
        original = sha256(capture.read_bytes()).hexdigest()
        destination = root / RECEIPT
        before_exists = destination.exists() or destination.is_symlink()
        result = inspect_readonly(root)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(sha256(capture.read_bytes()).hexdigest(), original)
        self.assertEqual(destination.exists() or destination.is_symlink(), before_exists)
        self.assertFalse(result["one_recipient_inplace_A_B_A_actual_vendor_test_executed"])
        self.assertFalse(result["third_party_code_executed"])
        self.assertFalse(result["third_party_legal_or_security_approved"])
        self.assertFalse(result["customer_distribution_authorized"])
        self.assertEqual(result["external_network_calls"], 0)
        self.assertEqual(result["operating_database_writes"], 0)
        print("UCIE_C4_OWNER_PINNED_WHEELHOUSE_READONLY_PREFLIGHT=" + json.dumps({
            "schema": SCHEMA,
            "readiness": result["readiness"],
            "gates": result["gates"],
            "source_commit_A": result["pinned_source_commits"]["A"],
            "source_commit_B": result["pinned_source_commits"]["B"],
            "actual_vendor_install_executed": False,
            "owner_resident_service_modified": False,
            "customer_distribution_authorized": False,
        }, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
