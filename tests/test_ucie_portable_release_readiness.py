"""Release technical/rights gate for UCIE first-party draft only."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import product_v1 as product
from ucie_miner import portable_release_readiness as readiness


class UCIEPortableReleaseReadinessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)

    def test_real_checkout_security_and_missing_license_are_explicit_no_go(self):
        start = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        result = readiness.inspect_first_party_release(self.root)
        self.assertEqual(result["status"],
                         "FIRST_PARTY_RELEASE_TECHNICAL_READINESS_REVIEWED_NO_GO")
        self.assertEqual(result["candidate_version"], "1.3.0")
        self.assertEqual(result["consumer_api_version"], "1.1.0")
        self.assertTrue(result["twice_built_bytes_identical"])
        self.assertTrue(result["zip_headers_normalized_for_windows_linux"])
        self.assertEqual(result["zip_layout_entries"], list(readiness.ENTRIES))
        self.assertEqual(result["portable_zip_third_party_runtime_packages"], 0)
        self.assertEqual(result["source_checkout_security_policy_present"], True)
        self.assertEqual(result["source_checkout_ignore_runtime_and_keys"], True)
        self.assertEqual(result["repository_license_declaration_status"],
                         "NO_REPOSITORY_LICENSE_DECLARATION")
        self.assertEqual(result["repository_license_declaration_filenames"], [])
        self.assertIn("REPOSITORY_LICENSE_DECLARATION_REQUIRES_OWNER_DECISION",
                      result["blocked_release_requirements"])
        self.assertFalse(result["owner_license_signoff"])
        self.assertFalse(result["external_independent_security_qa"])
        self.assertFalse(result["owner_release_authorized"])
        self.assertFalse(result["package_signed"])
        self.assertFalse(result["package_released"])
        self.assertFalse(result["v1_accepted"])
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertEqual(sorted(str(p.relative_to(self.root))
                                for p in self.root.rglob("*")), start)
        expected_zip, manifest = product.build_draft_package_bytes()
        self.assertEqual(result["canonical_zip_sha256"],
                         sha256(expected_zip).hexdigest())
        self.assertEqual(result["included_rights_security_notice_sha256"],
                         manifest["rights_security_sha256"])
        self.assertEqual(result["zip_executable_code_import_review"][0]["imports"],
                         ["__future__", "typing"])

    def test_license_file_not_auto_approved_even_when_present(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "UCIE"
            source.mkdir()
            original = readiness._source_checkout()
            (source / "SECURITY.md").write_bytes(
                (original / "SECURITY.md").read_bytes())
            (source / ".gitignore").write_bytes(
                (original / ".gitignore").read_bytes())
            (source / "LICENSE").write_text(
                "UNREVIEWED UCIE SYNTHETIC LICENSE PLACEHOLDER\n",
                encoding="utf-8")
            with patch.object(readiness, "_source_checkout", return_value=source):
                r = readiness.inspect_first_party_release(self.root)
            self.assertEqual(r["repository_license_declaration_status"],
                             "DECLARATION_PRESENT_NOT_LEGALLY_CLEARED")
            self.assertEqual(r["repository_license_declaration_filenames"],
                             ["LICENSE"])
            self.assertIn("SOURCE_LICENSE_DECLARATION_REQUIRES_OWNER_REVIEW",
                          r["blocked_release_requirements"])
            self.assertFalse(r["owner_license_signoff"])
            self.assertFalse(r["owner_release_authorized"])
            self.assertFalse(r["package_released"])

    def test_scope_and_execution_import_drift_are_fail_closed(self):
        for text in (
            b"import os\n",
            b"from subprocess import Popen\n",
            b"exec('bad')\n",
            b"open('local')\n",
            b"import requests\n",
            b"from pathlib import Path\nPath('x').write_text('x')\n",
            b"def broken(:\n",
        ):
            with self.subTest(text=text):
                with self.assertRaises(product.ProductIntegrationError):
                    readiness._first_party_static_review(text, "bad.py")
        with self.assertRaises(product.ProductIntegrationError):
            readiness.inspect_first_party_release(self.root.parent)

    def test_current_review_cli_returns_one_bounded_json_and_never_signs(self):
        with patch("sys.argv", [
            "portable_release_readiness", "--ucie-root", str(self.root),
        ]):
            with patch("builtins.print") as printed:
                self.assertEqual(readiness.main(), 0)
        result = json.loads(printed.call_args.args[0])
        self.assertEqual(result["status"],
                         "FIRST_PARTY_RELEASE_TECHNICAL_READINESS_REVIEWED_NO_GO")
        self.assertFalse(result["package_released"])
        self.assertFalse(result["owner_release_authorized"])
        with patch("sys.argv", [
            "portable_release_readiness", "--ucie-root", str(self.root.parent),
        ]):
            with patch("builtins.print") as printed:
                self.assertEqual(readiness.main(), 2)
        self.assertEqual(json.loads(printed.call_args.args[0])["status"],
                         "FIRST_PARTY_RELEASE_REVIEW_FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
