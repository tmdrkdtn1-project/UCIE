"""Owner-only read-only C2 acceptance on already captured official PyPI wheel bytes.

CI without owner-captured C1 wheels reports SKIP, never "live vendor PASS".
The owner test touches no network, subprocess, DB, services or third-party code.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from ucie_miner.customer_c2_supply_chain_review_v01 import inspect_c2, SCHEMA, STATUS
from ucie_miner.customer_offline_dependency_gate_v01 import WHEELHOUSE
from ucie_miner.customer_owner_wheelhouse_acquire_v01 import RECEIPT


class C2OwnerVendorMetadataTests(unittest.TestCase):
    def test_existing_owner_captured_three_vendor_wheels_read_only(self):
        root = Path(__file__).resolve().parents[1]
        wheel_dir, receipt_file = root / WHEELHOUSE, root / RECEIPT
        if not wheel_dir.is_dir() or not receipt_file.is_file():
            self.skipTest("NO_EXISTING_C1_CAPTURED_OWNER_VENDOR_BYTES_NOT_TESTED")
        report = inspect_c2(root)
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["status"], STATUS)
        self.assertEqual(report["package_count"], 3)
        self.assertEqual(
            {(p["name"], p["version"]) for p in report["packages"]},
            {("cryptography", "50.0.2"), ("cffi", "2.1.1"), ("pycparser", "3.12")},
        )
        self.assertTrue(all(not x["rights_cleared"] for x in report["packages"]))
        for flag in (
            "vendor_code_executed_or_installed", "other_project_access",
            "signing_or_release_performed", "customer_distribution_authorized",
            "c2_approved",
        ):
            self.assertIs(report[flag], False, flag)
        self.assertEqual(report["operating_database_writes"], 0)
        self.assertEqual(report["network_requests"], 0)
        receipt = {
            "schema": "UCIE_C2_OWNER_CAPTURED_VENDOR_METADATA_ONLY_V01",
            "status": "C2_REAL_CAPTURED_WHEEL_METADATA_OBSERVED_RIGHTS_NO_GO",
            "evidence_sha256": report["evidence_sha256"],
            "packages": [
                {
                    "name": p["name"],
                    "version": p["version"],
                    "wheel_sha256": p["sha256"],
                    "license_expression_claim_only":
                        p["license_evidence"]["license_expression_claim_only"],
                    "legacy_license_claim_only":
                        p["license_evidence"]["legacy_license_claim_only"],
                    "license_file_count": len(p["license_evidence"]["license_files"]),
                    "missing_license_file_count":
                        len(p["license_evidence"]["license_files_missing"]),
                    "notice_file_count": len(p["license_evidence"]["notice_files"]),
                }
                for p in report["packages"]
            ],
            "rights_approved": False,
            "security_approved": False,
            "customer_release_authorized": False,
            "network_requests": 0,
            "operating_database_writes": 0,
        }
        print("UCIE_C2_OWNER_METADATA_RECEIPT=" +
              json.dumps(receipt, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    unittest.main()
