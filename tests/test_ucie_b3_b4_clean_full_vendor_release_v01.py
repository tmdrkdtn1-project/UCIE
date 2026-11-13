"""B3/B4 full-vendor clean Windows CI scope and exact offline resolver contract."""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest
from unittest.mock import patch

# CI test runner exists as a first-party tests/ script, never invokes its main.
MODULE = Path(__file__).with_name("runtime_ucie_b3_b4_clean_full_vendor_release_v01.py")
spec = importlib.util.spec_from_file_location("_ucie_full_vendor_qa", MODULE)
assert spec is not None and spec.loader is not None
full_ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(full_ci)


class B3B4CleanVendorRecipientPolicyTests(unittest.TestCase):
    def test_no_ci_identity_cannot_access_vendor_or_install(self):
        with TemporaryDirectory(prefix="UCIE_B3_B4_SCOPE_DENY_") as folder:
            root = Path(folder) / "UCIE"
            root.mkdir()
            (root / ".git").mkdir()
            with self.assertRaises(full_ci.FullRecipientQAFailure):
                full_ci._scope(root, {})
            with patch.object(full_ci.vendor, "_pypi_index",
                              side_effect=AssertionError("network attempted")):
                with self.assertRaises(full_ci.FullRecipientQAFailure):
                    full_ci.run_clean_vendor_recipient(root, {})
            self.assertEqual(list(root.iterdir()), [root / ".git"])

    def test_owner_D_drive_literal_is_not_a_disposable_ci_checkout(self):
        root = Path("D:/UCIE")
        with self.assertRaises(full_ci.FullRecipientQAFailure):
            full_ci._scope(root, {
                "CI": "true", "GITHUB_ACTIONS": "true",
                "RUNNER_OS": "Windows", "GITHUB_REPOSITORY": "tmdrkdtn1-project/UCIE",
                full_ci.REQUIRED_ENV: "1",
            })

    def test_vendor_download_command_cannot_use_other_project_index_or_sdist(self):
        with TemporaryDirectory(prefix="UCIE_B3_B4_ARGS_") as folder:
            python = Path(folder) / "python.exe"
            dest = Path(folder) / "wheels"
            cmd = full_ci._pinned_download_command(python, dest)
            self.assertEqual(cmd[:5], [
                str(python), "-I", "-B", "-m", "pip"])
            self.assertIn("--isolated", cmd)
            self.assertIn("--only-binary=:all:", cmd)
            self.assertIn("--no-deps", cmd)
            self.assertIn("--index-url", cmd)
            self.assertIn("https://pypi.org/simple", cmd)
            self.assertEqual(cmd[-3:], [
                "cryptography==50.0.2", "cffi==2.1.1", "pycparser==3.12"])
            self.assertNotIn("--extra-index-url", cmd)
            self.assertNotIn("--pre", cmd)
            self.assertNotIn("git+https://", " ".join(cmd))

    def test_release_gate_is_not_auto_customer_license_or_approval(self):
        from ucie_miner import customer_private_entitlement_v01 as ent
        self.assertIn(b"PRIVATE_FOUR_PILLAR_CUSTOMER_ENTITLEMENT", ent.DOMAIN)
        self.assertNotEqual(ent.DOMAIN, (
            b"UCIE_C3_OWNER_PUBLIC_PR_METADATA_V01\x00"))
        self.assertEqual(full_ci.PASS.endswith("CUSTOMER_NO_GO"), True)

    def test_child_scripts_do_not_create_real_owner_key_or_accept_different_customer(self):
        src = full_ci.ENTITLEMENT_CHILD
        self.assertIn("Ed25519PrivateKey.generate()", src)
        self.assertIn("UCIE-FICTITIOUS-LICENSED-RECIPIENT-CI-ONLY", src)
        self.assertIn('"expected_recipient_token_sha256":"f"*64', src)
        self.assertIn('"expected_vendor_wheels_sha256":dict(vendor_hashes,cffi="f"*64)', src)
        self.assertIn('customer_distribution_authorized', src)
        self.assertNotIn("D:/UCIE/.build_keys", src)
        self.assertNotIn("D:\\UCIE\\.build_keys", src)

    def test_real_native_and_four_pillar_checks_reused_not_fabricated_flags(self):
        import inspect
        source = inspect.getsource(full_ci.run_clean_vendor_recipient)
        for required in (
            "vendor.validate_candidate", "full._install_cmd",
            "full._check_native", "full._check_four_pillars",
            "full._check_ui", "ab._uninstall",
            "actual_owner_c1_captured_wheels_used",
        ):
            self.assertIn(required, source)
        self.assertIn("customer_release_or_distribution_authorized", source)


if __name__ == "__main__":
    unittest.main()
