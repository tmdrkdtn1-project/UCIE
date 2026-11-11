"""UCIE C1 owner wheelhouse preview and offline hash validation regressions.

Every wheel is generated from inert UCIE-owned strings in temp/UCIE. Tests
must NEVER invoke pip, install wheels, fetch the web or alter an owner task.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from ucie_miner import customer_owner_wheelhouse_acquire_v01 as owner


PYPROJECT = """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "ucie-public-only-demo"
version = "0.1.0"
description = "UCIE-only inert synthetic project"
requires-python = ">=3.13"
dependencies = ["cryptography>=50.0.2,<51"]
"""


def inert_wheel(folder: Path, name: str, version: str) -> Path:
    """First-party fixture is NOT an actual vendor/redistributable wheel."""
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{name}-{version}-py3-none-any.whl"
    info = f"{name}-{version}.dist-info/"
    files = {
        info + "METADATA": (
            "Metadata-Version: 2.3\nName: " + name +
            "\nVersion: " + version + "\n"
        ).encode(),
        info + "WHEEL": b"Wheel-Version: 1.0\nGenerator: UCIE-test-only\n",
        name + "/__init__.py": b"# UCIE fixture, never imported\n",
    }
    lines = []
    for file, payload in files.items():
        digest = base64.urlsafe_b64encode(sha256(payload).digest()).rstrip(
            b"=").decode("ascii")
        lines.append(f"{file},sha256={digest},{len(payload)}")
    lines.append(info + "RECORD,,")
    files[info + "RECORD"] = ("\n".join(lines) + "\n").encode()
    wheel = folder / filename
    with ZipFile(wheel, "w", ZIP_DEFLATED) as archive:
        for file, content in files.items():
            archive.writestr(file, content)
    return wheel


class UCIEOwnerWheelAcquisitionV01Tests(unittest.TestCase):
    def setUp(self):
        scratch = TemporaryDirectory(prefix="UCIE_OWNER_WHEEL_ACQUIRE_TEST_")
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name) / "UCIE"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        (self.root / "pyproject.toml").write_text(
            PYPROJECT, encoding="utf-8")

    def _wheels(self):
        stage = self.root / "staged"
        for name, version in owner.PINNED:
            inert_wheel(stage, name, version)
        official = {}
        for name, version in owner.PINNED:
            target = stage / f"{name}-{version}-py3-none-any.whl"
            official[name] = {target.name: sha256(target.read_bytes()).hexdigest()}
        return stage, official

    def test_preview_does_not_download_or_touch_network(self):
        with patch("subprocess.run",
                   side_effect=AssertionError("pip forbidden during preview")), patch(
            "urllib.request.urlopen",
            side_effect=AssertionError("network forbidden during preview")
        ):
            plan = owner.plan(self.root)
        self.assertEqual(plan["schema"], owner.SCHEMA)
        self.assertEqual(plan["mode"], "OFFLINE_PREVIEW")
        self.assertFalse(plan["wheelhouse_exists"])
        self.assertFalse(plan["downloads_executed"])
        self.assertFalse(plan["customer_distribution_authorized"])
        self.assertEqual(plan["pinned_packages"],
                         ["cryptography==50.0.2", "cffi==2.1.1",
                          "pycparser==3.12"])

    def test_exact_pip_command_is_isolated_binary_only_and_no_install(self):
        args = owner._command(Path("D:/UCIE/.venv/Scripts/python.exe"),
                              self.root / "staging")
        self.assertEqual(args[1:6],
                         ["-I", "-B", "-m", "pip", "--isolated"])
        self.assertEqual(args[6], "download")
        for required in (
            "--only-binary=:all:", "--no-cache-dir", "--no-input",
            "--platform", "win_amd64", "--python-version", "3.15",
            "--implementation", "cp", "--abi",
            "https://pypi.org/simple", "cryptography==50.0.2",
            "cffi==2.1.1", "pycparser==3.12"
        ):
            self.assertIn(required, args)
        self.assertNotIn("install", args)
        self.assertNotIn("--extra-index-url", args)
        self.assertNotIn("--trusted-host", args)
        self.assertNotIn("--no-deps", args)

    def test_candidate_validates_all_three_synthetic_internal_records_and_hashes(self):
        stage, official = self._wheels()
        result = owner.validate_candidate(stage, official)
        self.assertEqual(len(result["files"]), 3)
        self.assertTrue(result["all_wheel_sha256_equal_official_pypi_metadata"])
        self.assertFalse(result["wheel_content_installed_or_executed"])
        self.assertFalse(result["license_and_SPDX_approved"])
        self.assertFalse(result["customer_release_authorized"])
        for file in result["files"]:
            self.assertTrue(file["wheel_RECORD_verified"])
            self.assertFalse(file["third_party_rights_approved"])

    def test_wrong_downloaded_wheel_digest_fail_closed(self):
        stage, official = self._wheels()
        official["cryptography"] = {
            list(official["cryptography"])[0]: "0" * 64
        }
        with self.assertRaises(owner.WheelAcquisitionError):
            owner.validate_candidate(stage, official)

    def test_missing_package_cannot_pass(self):
        stage, official = self._wheels()
        (stage / "pycparser-3.12-py3-none-any.whl").unlink()
        with self.assertRaises(owner.WheelAcquisitionError):
            owner.validate_candidate(stage, official)

    def test_unexpected_wheel_cannot_pass(self):
        stage, official = self._wheels()
        inert_wheel(stage, "unknownvendor", "1.0.0")
        with self.assertRaises(owner.WheelAcquisitionError):
            owner.validate_candidate(stage, official)

    def test_changed_version_cannot_pass(self):
        stage, official = self._wheels()
        (stage / "cryptography-50.0.2-py3-none-any.whl").unlink()
        inert_wheel(stage, "cryptography", "50.0.1")
        with self.assertRaises(owner.WheelAcquisitionError):
            owner.validate_candidate(stage, official)

    def test_offline_receipt_verifies_without_any_network(self):
        stage, official = self._wheels()
        receipt = owner.validate_candidate(stage, official)
        store = self.root / owner.WHEELHOUSE
        stage.rename(store)
        (self.root / owner.RECEIPT).write_text(
            json.dumps(receipt, sort_keys=True), encoding="ascii")
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("verify must be offline")), patch(
            "subprocess.run", side_effect=AssertionError("verify never installs")
        ):
            result = owner.verify_local(self.root)
        self.assertEqual(result["wheel_count"], 3)
        self.assertTrue(result["all_local_bytes_match_captured_pypi_digests"])
        self.assertFalse(result["customer_distribution_authorized"])

    def test_offline_tamper_after_receipt_cannot_pass(self):
        stage, official = self._wheels()
        receipt = owner.validate_candidate(stage, official)
        stage.rename(self.root / owner.WHEELHOUSE)
        (self.root / owner.RECEIPT).write_text(
            json.dumps(receipt), encoding="ascii")
        target = self.root / owner.WHEELHOUSE / "pycparser-3.12-py3-none-any.whl"
        target.write_bytes(target.read_bytes() + b"UCIE TAMPER")
        with self.assertRaises(owner.WheelAcquisitionError):
            owner.verify_local(self.root)

    def test_pypi_release_json_constrained_to_exact_identity(self):
        class FakeResponse:
            status = 200
            def geturl(self):
                return "https://pypi.org/pypi/cffi/2.1.1/json"
            def read(self, n):
                return json.dumps({
                    "info": {"name": "cffi", "version": "2.1.1"},
                    "urls": [{
                        "packagetype": "bdist_wheel",
                        "filename": "cffi-2.1.1-py3-none-any.whl",
                        "digests": {"sha256": "a" * 64}
                    }]
                }).encode()
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return None
        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            record = owner._pypi_index("cffi", "2.1.1")
        self.assertEqual(
            record["cffi-2.1.1-py3-none-any.whl"], "a" * 64
        )
        with self.assertRaises(owner.WheelAcquisitionError):
            owner._pypi_index("unapproved", "1.0")

    def test_owner_apply_denied_on_synthetic_checkout_even_with_consent(self):
        with patch("subprocess.run",
                   side_effect=AssertionError("no pip on synthetic root")), patch(
            "urllib.request.urlopen",
            side_effect=AssertionError("no network on synthetic root")
        ):
            with self.assertRaises(owner.WheelAcquisitionError):
                owner.acquire_once(self.root, typed=owner.CONSENT)

    def test_wrong_consent_denied_before_all_owner_checks(self):
        with patch("subprocess.run",
                   side_effect=AssertionError("never download")):
            with self.assertRaises(owner.WheelAcquisitionError):
                owner.acquire_once(self.root, typed="DO_NOT_APPLY")

    def test_pyproject_unapproved_drift_denied(self):
        path = self.root / "pyproject.toml"
        path.write_text(PYPROJECT.replace(
            "cryptography>=50.0.2,<51", "cryptography>=0.0.0"))
        with self.assertRaises(owner.WheelAcquisitionError):
            owner.plan(self.root)

    def test_owner_current_checkout_preview_is_no_go(self):
        real = Path(__file__).resolve().parents[1]
        if real.name.casefold() != "ucie" or not (real / ".git").is_dir():
            self.skipTest("only exact UCIE owner or public CI checkout")
        state = owner.plan(real)
        self.assertFalse(state["customer_distribution_authorized"])
        self.assertFalse(state["downloads_executed"])
        self.assertEqual(state["pinned_packages"], list(owner._requirements()))


if __name__ == "__main__":
    unittest.main()
