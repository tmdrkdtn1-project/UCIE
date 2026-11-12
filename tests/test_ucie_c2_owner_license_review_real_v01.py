"""Owner read-only actual captured vendor license file evidence; no export."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

from ucie_miner.customer_c2_owner_license_review_packet_v01 import (
    SCHEMA, prepare_owner_rights_packet,
)
from ucie_miner.customer_offline_dependency_gate_v01 import WHEELHOUSE
from ucie_miner.customer_owner_wheelhouse_acquire_v01 import RECEIPT


class C2OwnerRealRightsPacketReadOnlyTests(unittest.TestCase):
    def test_existing_real_owner_captured_license_texts_verified(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / WHEELHOUSE).is_dir() or not (root / RECEIPT).is_file():
            self.skipTest("NO_REAL_OWNER_C1_CAPTURE_PRESENT_NOT_ATTESTED")
        packet, files = prepare_owner_rights_packet(root)
        self.assertEqual(packet["schema"], SCHEMA)
        self.assertEqual(len(packet["reviewed_packages"]), 3)
        self.assertEqual({x["distribution"] for x in packet["reviewed_packages"]},
                         {"cryptography", "cffi", "pycparser"})
        self.assertEqual(packet["license_file_count"], 5)
        self.assertEqual(len(files), 5)
        self.assertTrue(all(x.startswith("license-text/") for x in files))
        self.assertFalse(packet["customer_distribution_authorized"])
        self.assertFalse(packet["legal_redist_clearance"])
        self.assertFalse(packet["security_clearance"])
        self.assertEqual(packet["network_requests"], 0)
        self.assertEqual(packet["operating_database_writes"], 0)
        print("UCIE_C2_REAL_OWNER_LICENSE_TEXT_REVIEW=" + json.dumps({
            "schema": SCHEMA,
            "status": "REAL_CAPTURED_LICENSE_BYTES_VERIFIED_HUMAN_RIGHTS_NO_GO",
            "parent_c2_evidence_sha256": packet["parent_c2_evidence_sha256"],
            "review_entries_sha256": packet["review_entries_sha256"],
            "license_file_count": len(files),
            "license_total_bytes": packet["license_total_bytes"],
            "names_and_texts_not_printed": True,
            "owner_export_executed": False,
            "legal_redist_clearance": False,
            "customer_distribution_authorized": False,
        }, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
