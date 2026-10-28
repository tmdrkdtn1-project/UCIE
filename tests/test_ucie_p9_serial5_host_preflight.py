"""Host-focused P9 release gate preflight: real original UCIE Serial5 imports.

This is a *read-only source integration check*, NOT verification of a real
owner-signed pack, independent QA, licensing or production release.
Uses only installed UCIE Python modules and a dedicated synthetic temp UCIE
root. No network, signing, production data, external project or pack access.
"""
from __future__ import annotations

import contextlib
import importlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import product_v1


class P9Serial5HostPreflight(unittest.TestCase):
    def test_actual_original_serial5_and_signed_library_imports(self):
        """Catch missing fifth_owner_addendum on the *actual* Python host."""
        module = importlib.import_module("ucie_public.fifth_owner_addendum")
        signed = importlib.import_module("ucie_miner.signed_rule_library")
        resource = importlib.import_module("ucie_miner.static_asyncio_resource")
        self.assertTrue(callable(module.verify_fifth_addendum))
        self.assertTrue(callable(signed.inspect_signed_library))
        self.assertTrue(callable(resource.inspect_asyncio_protocol_factory_source))
        self.assertEqual(module.RULE_ID, resource.RULE_ID)
        self.assertIn(module.RULE_ID, signed.ALLOWED_RULES)
        self.assertTrue(Path(module.__file__).is_file())
        self.assertTrue(Path(signed.__file__).is_file())
        self.assertTrue(Path(resource.__file__).is_file())
        # A module being available proves NOTHING about a real owner's pack.
        print("UCIE_SERIAL5_HOST_PREFLIGHT=" + json.dumps({
            "status": "EXISTING_SERIAL5_MODULE_IMPORTABLE_ONLY",
            "ucie_original_verifier_imported": True,
            "ucie_original_source_inspector_imported": True,
            "actual_owner_pack_present_or_verified": False,
            "independent_qa_attested": False,
            "license_signoff": False,
            "network_requests": 0,
            "production_database_writes": 0,
            "new_signatures_created": 0,
            "v1_accepted": False,
        }, sort_keys=True))

    def test_original_signed_verifier_fails_closed_on_missing_pack(self):
        """Only synthetic missing paths; no owner's real signed files touched."""
        signed = importlib.import_module("ucie_miner.signed_rule_library")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UCIE"
            root.mkdir()
            with self.assertRaises(signed.SignedLibraryError):
                signed.inspect_signed_library(
                    root, serial4_pack=root / "MISSING_serial4.zip",
                    owner_public_trust=root / "MISSING_public_trust.pem",
                    serial5_pack=root / "MISSING_serial5.zip")

    def test_p9_preview_is_usable_without_signed_pack_and_is_no_go(self):
        """P9 must work without owner files and never claim signatures."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UCIE"
            (root / "runtime").mkdir(parents=True)
            with patch("urllib.request.urlopen",
                       side_effect=AssertionError("P9 preflight must not GET")):
                out = product_v1.integrated_product_preview(root, include_demo=True)
            self.assertEqual(out["status"],
                             "P9_INTEGRATED_READ_ONLY_PRODUCT_PREVIEW_NO_GO")
            self.assertEqual(out["signed_rules"]["status"], "NOT_INSPECTED_NO_GO")
            self.assertEqual(out["signed_rules"]["verified_signed_rule_count"], 0)
            self.assertFalse(out["v1_accepted"])
            self.assertFalse(out["package_released"])
            self.assertTrue(out["portable_first_party_consumer_demo"][
                "all_queries_equivalent"])
            self.assertEqual(out["network_requests"], 0)
            self.assertEqual(out["operating_database_writes"], 0)
            self.assertEqual(out["new_experience_writes"], 0)
            self.assertEqual(out["new_signatures_created"], 0)
            self.assertEqual(list((root / "runtime").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
