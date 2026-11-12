"""UCIE C1 disposable offline install: NO real vendor wheel installation in tests.

All mutable fixtures live under a synthetic temp/UCIE. Positive child
process behavior is MOCKED, never executed. Real checkout probe is read-only.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucie_miner import customer_offline_install_rehearsal_v01 as install
from ucie_miner import customer_owner_wheelhouse_acquire_v01 as acquire


PROJECT = """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
[project]
name = "ucie-public-only-demo"
version = "0.1.0"
description = "UCIE first-party synthetic only"
requires-python = ">=3.13"
dependencies = ["cryptography>=50.0.2,<51"]
"""
HASHES = {
    "cryptography": "a" * 64,
    "cffi": "b" * 64,
    "pycparser": "c" * 64,
}


class UCIEC1OfflineInstallRehearsalTests(unittest.TestCase):
    def setUp(self):
        t = TemporaryDirectory(prefix="UCIE_C1_OFFLINE_INSTALL_TEST_")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name) / "UCIE"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        (self.root / ".gitignore").write_text("downloaded/\n", encoding="utf-8")
        (self.root / "pyproject.toml").write_text(PROJECT, encoding="utf-8")

    def test_preview_without_wheels_is_no_network_and_not_go(self):
        with patch("subprocess.run", side_effect=AssertionError("no process")), patch(
            "urllib.request.urlopen", side_effect=AssertionError("no network")
        ):
            result = install.preview(self.root)
        self.assertEqual(result["schema"], install.SCHEMA)
        self.assertEqual(result["mode"], "OFFLINE_PREVIEW")
        self.assertEqual(result["readiness"], "WAITING_FOR_OWNER_WHEEL_ACQUISITION")
        self.assertFalse(result["local_wheelhouse_sha_receipt_verified"])
        self.assertFalse(result["external_packages_installed_or_imported"])
        self.assertFalse(result["customer_release_authorized"])
        self.assertEqual(result["subprocesses_executed"], 0)

    def test_corrupt_capture_is_closed_not_marked_ready(self):
        folder = self.root / "downloaded"
        folder.mkdir()
        (folder / "ucie_c1_wheelhouse_receipt_preview.json").write_text(
            "forged first-party-only negative fixture")
        p = install.preview(self.root)
        self.assertEqual(p["readiness"], "WHEELHOUSE_OR_RECEIPT_INVALID_FAIL_CLOSED")
        self.assertFalse(p["local_wheelhouse_sha_receipt_verified"])

    def test_previous_install_receipt_prevents_repeat(self):
        f = self.root / install.RECEIPT
        f.parent.mkdir()
        f.write_text("{}")
        p = install.preview(self.root)
        self.assertIn("PREVIOUS", p["readiness"])
        self.assertFalse(p["local_wheelhouse_sha_receipt_verified"])

    def test_explicit_sha256_pins_for_every_locked_wheel(self):
        requirements = install._requirements_lines(HASHES)
        lines = requirements.strip().splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], "cryptography==50.0.2 --hash=sha256:" + "a"*64)
        self.assertEqual(lines[1], "cffi==2.1.1 --hash=sha256:" + "b"*64)
        self.assertEqual(lines[2], "pycparser==3.12 --hash=sha256:" + "c"*64)
        self.assertNotIn("http", requirements.lower())

    def test_hash_list_incomplete_or_bad_digest_blocks(self):
        for bad in (
            {}, {"cryptography": "a"*64},
            dict(HASHES, cffi="x"*64),
            dict(HASHES, unknown="a"*64),
        ):
            with self.subTest(bad=repr(bad)[:30]):
                with self.assertRaises(install.OfflineInstallRehearsalError):
                    install._requirements_lines(bad)

    def test_pip_command_cannot_contact_index_or_build_sdist(self):
        cmd = install._pip_command(
            Path("C:/UCIE-SYNTHETIC/Scripts/python.exe"),
            Path("C:/UCIE-SYNTHETIC/wheelhouse"),
            Path("C:/UCIE-SYNTHETIC/requirements.txt"),
        )
        self.assertEqual(cmd[1:6], ["-I", "-B", "-m", "pip", "--isolated"])
        self.assertEqual(cmd[6], "install")
        for required in ("--no-index", "--find-links",
                         "--require-hashes", "--only-binary=:all:",
                         "--no-cache-dir", "--no-input", "--no-compile"):
            self.assertIn(required, cmd)
        for banned in ("--index-url", "--extra-index-url", "--trusted-host",
                       "--no-deps", "--upgrade", "--pre", "--force-reinstall"):
            self.assertNotIn(banned, cmd)
        self.assertNotIn("https://", " ".join(cmd))

    def test_owner_gate_denies_synthetic_windows_root_before_any_run(self):
        with patch("subprocess.run", side_effect=AssertionError("no run")), patch(
            "urllib.request.urlopen", side_effect=AssertionError("no network")
        ):
            with self.assertRaises(install.OfflineInstallRehearsalError):
                install._owner_gate(self.root)

    def test_invalid_consent_denied_before_any_owner_check(self):
        with patch.object(install, "_owner_gate",
                          side_effect=AssertionError("must not check owner")):
            with self.assertRaises(install.OfflineInstallRehearsalError):
                install.run_owner_rehearsal(self.root, "WRONG_OR_ABSENT_CONSENT")

    def test_forced_pip_failure_does_not_include_vendor_logs(self):
        class Failing:
            returncode = 1
            stdout = ""
            stderr = "UCIE synthetic SECRET_TEST_FIXTURE should not leak"
        with patch("subprocess.run", return_value=Failing()):
            with self.assertRaises(install.OfflineInstallRehearsalError) as cm:
                install._run_exact([sys.executable, "-I", "-B", "-m", "pip"],
                                   self.root, install._environment(), "hashlocked pip")
        self.assertNotIn("SECRET_TEST_FIXTURE", str(cm.exception))
        self.assertIn("failed closed", str(cm.exception))

    def test_environment_strips_inherited_pip_index_and_pythonpath(self):
        with patch.dict("os.environ", {
            "PYTHONPATH": "UCIE_INERT_BUT_FORBIDDEN",
            "PIP_INDEX_URL": "https://unapproved.invalid",
            "PIP_EXTRA_INDEX_URL": "https://unapproved.invalid",
        }):
            e = install._environment()
        self.assertNotIn("PYTHONPATH", e)
        self.assertNotIn("PIP_INDEX_URL", e)
        self.assertNotIn("PIP_EXTRA_INDEX_URL", e)
        self.assertEqual(e["PIP_NO_INDEX"], "1")

    def test_version_receipt_checks_isolated_prefix_and_three_exact_versions(self):
        path = self.root / "downloaded" / "test_venv"
        versions = dict(acquire.PINNED)
        content = json.dumps({
            "prefix": str(path), "base_prefix": str(self.root),
            "versions": versions, "major": 3, "minor": 15, "bits": 64
        })
        self.assertEqual(install._check_versions(content, path), versions)
        with self.assertRaises(install.OfflineInstallRehearsalError):
            install._check_versions(content.replace('"minor": 15', '"minor": 14'),
                                    path)
        with self.assertRaises(install.OfflineInstallRehearsalError):
            install._check_versions(content, self.root / "different")

    def test_forged_pypi_capture_receipt_disallowed(self):
        capture = self.root / acquire.RECEIPT
        capture.parent.mkdir(parents=True)
        fake = {
            "schema": acquire.SCHEMA,
            "status": acquire.STATUS,
            "customer_release_authorized": False,
            "files": [
                {"distribution": n, "version": v, "sha256": "e"*64}
                for n, v in acquire.PINNED
            ]
        }
        fake["files"][0]["version"] = "49.0.0"
        capture.write_text(json.dumps(fake))
        with patch.object(acquire, "verify_local", return_value={
            "wheel_count": 3, "customer_distribution_authorized": False
        }):
            with self.assertRaises(install.OfflineInstallRehearsalError):
                install._wheel_receipt(self.root)

    def test_linked_download_parent_rejected(self):
        target = self.root / "UCIE_EMPTY_INERT"
        target.mkdir()
        linked = self.root / "downloaded"
        try:
            linked.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Windows symlink creation not granted")
        with self.assertRaises(install.OfflineInstallRehearsalError):
            install.preview(self.root)

    def test_synthetic_positive_pipeline_never_runs_real_pip_or_vendor_wheel(self):
        (self.root / "downloaded").mkdir()
        captured = self.root / acquire.RECEIPT
        captured.write_text("UCIE_SYNTHETIC_CAPTURE_ONLY")
        calls = []
        def simulated_process(args, cwd, env, purpose):
            calls.append((purpose, tuple(args)))
            if purpose == "offline venv creation":
                target = Path(args[-1]) / "Scripts" / "python.exe"
                target.parent.mkdir(parents=True)
                target.write_bytes(b"UCIE INERT NOT EXECUTABLE")
                return ""
            if purpose == "installed distribution metadata check":
                return json.dumps({
                    "prefix": str(Path(cwd) / "recipient_venv"),
                    "base_prefix": "UCIE SYNTHETIC BASE",
                    "versions": dict(acquire.PINNED),
                    "major": 3, "minor": 15, "bits": 64
                })
            if purpose == "no-index hashlocked pip":
                self.assertIn("--no-index", args)
                self.assertIn("--require-hashes", args)
                self.assertNotIn("--index-url", args)
                self.assertTrue(Path(args[-1]).read_text().count("--hash=sha256:") == 3)
            return ""
        with patch.object(install, "_owner_gate", return_value=Path(sys.executable)), patch.object(
            install, "_wheel_receipt", return_value=({}, HASHES)
        ), patch.object(install, "_run_exact", side_effect=simulated_process), patch(
            "subprocess.run", side_effect=AssertionError("actual process prohibited")
        ), patch("urllib.request.urlopen", side_effect=AssertionError("network prohibited")):
            receipt = install.run_owner_rehearsal(self.root, install.CONSENT)
        self.assertEqual(len(calls), 4)
        self.assertTrue(receipt["offline_pip_no_index_and_require_hashes_succeeded"])
        self.assertTrue(receipt["disposable_venv_removed"])
        self.assertFalse(receipt["customer_distribution_authorized"])
        self.assertFalse(receipt["clean_second_windows_recipient_attested"])
        self.assertEqual(list((self.root / "downloaded").glob(
            "ucie_c1_offline_install_*")), [])
        self.assertTrue((self.root / install.RECEIPT).is_file())

    def test_main_is_safe_offline_preview_and_failed_apply(self):
        fake_source = self.root / "src" / "ucie_miner" / "customer_offline_install_rehearsal_v01.py"
        log = io.StringIO()
        with patch.object(install, "__file__", str(fake_source)), patch(
            "subprocess.run", side_effect=AssertionError("no process")
        ), patch("urllib.request.urlopen", side_effect=AssertionError("no network")
        ), redirect_stdout(log):
            status = install.main([])
        self.assertEqual(status, 0)
        output = json.loads(log.getvalue())
        self.assertFalse(output["customer_release_authorized"])
        self.assertEqual(output["mode"], "OFFLINE_PREVIEW")

    def test_real_ucie_checkout_read_only_presence_report(self):
        root = Path(__file__).resolve().parents[1]
        if root.name.casefold() != "ucie" or not (root / ".git").is_dir():
            self.skipTest("exact UCIE checkout only")
        state = install.preview(root)
        print("UCIE_C1_WHEELHOUSE_READONLY_OWNER_STATE=" +
              state["readiness"])
        self.assertEqual(state["subprocesses_executed"], 0)
        self.assertFalse(state["customer_release_authorized"])


if __name__ == "__main__":
    unittest.main()
