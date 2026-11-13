"""Owner ONLY: no-file-write source-linked public metadata export preflight.

This test contains no APIs for generic user files, other projects or network.
It refuses to treat GitHub-hosted CI's empty source ledger as owner acceptance.
"""
from pathlib import Path
import re
import unittest

from ucie_miner import local_public_pr_capsule_v01 as cap


class OwnerPortablePublicMetadataReadOnlyPreflight(unittest.TestCase):
    def test_existing_UCIE_owner_source_linkage_readonly_no_capsule_output(self):
        root = Path(__file__).resolve().parents[1]
        intended = Path("D:/UCIE")
        if (root.resolve() != intended.resolve()
                or not (root / "runtime").is_dir()):
            self.skipTest("only existing owner D:/UCIE runtime, never CI")
        before = (
            (root / cap.FILE).exists(),
            (root / cap.PIN).exists(),
        )
        result = cap.capture_preview(root)  # Stage10/15 -> Stage12 read-only
        after = (
            (root / cap.FILE).exists(),
            (root / cap.PIN).exists(),
        )
        self.assertEqual(before, after)
        self.assertEqual(result["schema"], cap.SCHEMA)
        self.assertEqual(
            result["status"], "OWNER_READONLY_PUBLIC_METADATA_PREVIEW_NO_GO")
        self.assertLessEqual(result["candidate_metadata_rows"], cap.MAX_ITEMS)
        self.assertGreater(result["candidate_metadata_rows"], 0)
        self.assertRegex(result["local_snapshot_sha256_if_owner_consents"],
                         r"^[0-9a-f]{64}$")
        self.assertFalse(result["local_capsule_written"])
        self.assertFalse(result["customer_distribution_authorized"])
        self.assertEqual(result["operating_database_writes"], 0)
        # No raw public-source titles, review notes or user paths are emitted.
        print("UCIE_PUBLIC_METADATA_OWNER_READONLY_PREVIEW_READY",
              "SELECTED", result["candidate_metadata_rows"],
              "OMITTED", result["unselected_source_revisions"],
              "NO_EXPORT_TRUE")


if __name__ == "__main__":
    unittest.main()
