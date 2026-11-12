"""C1 full-product offline rehearsal tests: source-only, inert, NO vendor runs.

Synthetic wheel ZIP fixtures are UCIE-owned inert text. Positive rehearsal
simulates ALL child subprocesses; never runs pip, installs a real third-party
package, reads customer paths, or touches the owner resident localhost.
"""
from __future__ import annotations

import base64
from contextlib import redirect_stdout
from hashlib import sha256
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from ucie_miner import customer_full_product_offline_rehearsal_v01 as full
from ucie_miner import customer_component_lifecycle_v01 as comp
from ucie_miner import customer_runtime_closure_v01 as runtime
from ucie_miner import customer_owner_wheelhouse_acquire_v01 as acquire
from ucie_miner import customer_offline_install_rehearsal_v01 as dependency
from ucie_miner.customer_staging_v01 import PILLARS


PROJECT = """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
[project]
name = "ucie-public-only-demo"
version = "0.1.0"
description = "UCIE synthetic-only owner test"
requires-python = ">=3.13"
dependencies = ["cryptography>=50.0.2,<51"]
[project.scripts]
ucie-product-preview = "ucie_miner.customer_staging_v01:main"
"""
HASHES = {"cryptography": "a"*64, "cffi": "b"*64, "pycparser": "c"*64}


def inert_product_wheel(where: Path, source: dict[str, bytes],
                        *, missing: str = "", forged: bool = False,
                        extra: str = "") -> Path:
    """Valid-looking first-party synthetic metadata; NEVER external vendor code."""
    where.mkdir(exist_ok=True, parents=True)
    folder = full.WHEEL_META
    files = {name[4:]: raw for name, raw in source.items()
             if name.startswith(("src/ucie_miner/", "src/ucie_public/"))
             and name.endswith(".py")}
    if missing:
        files.pop(missing, None)
    if extra:
        files[extra] = b"UCIE INERT FORBIDDEN MEMBER"
    files[folder + "METADATA"] = (
        b"Metadata-Version: 2.3\nName: ucie-public-only-demo\n"
        b"Version: 0.1.0\nRequires-Dist: cryptography<51,>=50.0.2\n"
    )
    files[folder + "WHEEL"] = b"Wheel-Version: 1.0\nTag: py3-none-any\n"
    files[folder + "entry_points.txt"] = (
        b"[console_scripts]\nucie-product-preview = "
        b"ucie_miner.customer_staging_v01:main\n"
    )
    rows = []
    for name, raw in sorted(files.items()):
        digest = base64.urlsafe_b64encode(
            sha256(raw).digest()).rstrip(b"=").decode("ascii")
        rows.append(name + ",sha256=" + digest + "," + str(len(raw)))
    rows.append(folder + "RECORD,,")
    files[folder + "RECORD"] = ("\n".join(rows) + "\n").encode("ascii")
    if forged:
        files["ucie_miner/customer_staging_v01.py"] += b"TAMPER_AFTER_RECORD"
    dest = where / full.FIRST_PARTY_WHEEL
    with ZipFile(dest, "w", ZIP_DEFLATED) as file:
        for name, raw in sorted(files.items()):
            file.writestr(name, raw)
    return dest


class UCIEFullProductOfflineRehearsalTests(unittest.TestCase):
    def setUp(self):
        t = TemporaryDirectory(prefix="UCIE_C1_FULL_PRODUCT_TEST_")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name) / "UCIE"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        (self.root / ".gitignore").write_text("downloaded/\n", encoding="utf-8")
        (self.root / "pyproject.toml").write_text(PROJECT, encoding="utf-8")
        self.source = {
            "src/ucie_miner/__init__.py": b"# UCIE synthetic\n",
            "src/ucie_miner/customer_staging_v01.py": b"# UCIE synthetic staging\n",
            "src/ucie_miner/local_v1_app_v01.py": b"# UCIE synthetic V04\n",
            "src/ucie_miner/customer_portable_preview_v01.py": b"# UCIE preview\n",
            "src/ucie_public/__init__.py": b"# UCIE synthetic\n",
        }

    def test_default_preview_is_readonly_no_install_or_network(self):
        with patch("subprocess.run", side_effect=AssertionError("NO PIP")), patch(
            "urllib.request.urlopen", side_effect=AssertionError("NO NETWORK")
        ):
            state = full.preview(self.root)
        self.assertEqual(state["schema"], full.SCHEMA)
        self.assertEqual(state["mode"], "OFFLINE_READONLY_PREVIEW")
        self.assertFalse(state["existing_verified_dependency_rehearsal"])
        self.assertFalse(state["download_or_pip_executed"])
        self.assertFalse(state["customer_distribution_authorized"])
        self.assertIn("PENDING", state["readiness"])

    def test_ready_preview_depends_on_real_verified_install_receipt(self):
        with patch.object(full, "_dependency_evidence",
                          return_value=(HASHES, "a"*64)):
            state = full.preview(self.root)
        self.assertTrue(state["existing_verified_dependency_rehearsal"])
        self.assertIn("READY_FOR_OWNER", state["readiness"])
        (self.root / "downloaded").mkdir()
        (self.root / full.RECEIPT).write_text("UCIE already accepted")
        self.assertIn("ALREADY_PRESENT", full.preview(self.root)["readiness"])

    def test_previous_dependency_receipt_hash_must_match_capture_bytes(self):
        folder = self.root / "downloaded"
        folder.mkdir()
        capture = self.root / acquire.RECEIPT
        capture.write_text("UCIE synthetic capture")
        report = {
            "schema": dependency.SCHEMA, "status": dependency.STATUS,
            "evidence": "SAME_OWNER_HOST_DISPOSABLE_VENV_ONLY",
            "pinned_versions": dict(acquire.PINNED),
            "captured_wheel_receipt_sha256": sha256(capture.read_bytes()).hexdigest(),
            "offline_pip_no_index_and_require_hashes_succeeded": True,
            "pip_dependency_check_succeeded": True,
            "installed_distribution_metadata_version_check_succeeded": True,
            "disposable_venv_removed": True,
            "full_product_installed": False,
            "customer_distribution_authorized": False,
        }
        old = self.root / dependency.RECEIPT
        old.write_text(json.dumps(report))
        with patch.object(dependency, "_wheel_receipt",
                          return_value=({}, HASHES)):
            self.assertEqual(full._dependency_evidence(self.root)[0], HASHES)
            report["captured_wheel_receipt_sha256"] = "0"*64
            old.write_text(json.dumps(report))
            with self.assertRaises(full.OfflineFullProductError):
                full._dependency_evidence(self.root)

    def test_first_party_wheel_source_and_record_exact(self):
        with TemporaryDirectory(prefix="UCIE_INERT_ZIP_") as folder:
            file = inert_product_wheel(Path(folder), self.source)
            report = full._inspect_first_party_wheel(file, self.source)
        self.assertEqual(report["file_count"], 5)
        self.assertTrue(report["wheel_record_verified"])
        self.assertTrue(report["source_code_bytes_match"])
        self.assertFalse(report["customer_distribution_authorized"])

    def test_wheel_missing_first_party_source_fails_closed(self):
        with TemporaryDirectory(prefix="UCIE_MISSING_MODULE_") as folder:
            file = inert_product_wheel(
                Path(folder), self.source,
                missing="ucie_miner/customer_staging_v01.py")
            with self.assertRaises(full.OfflineFullProductError):
                full._inspect_first_party_wheel(file, self.source)

    def test_wheel_unexpected_external_payload_fails_closed(self):
        with TemporaryDirectory(prefix="UCIE_EXTRA_PAYLOAD_") as folder:
            file = inert_product_wheel(
                Path(folder), self.source,
                extra="unexpected_vendor/module.py")
            with self.assertRaises(full.OfflineFullProductError):
                full._inspect_first_party_wheel(file, self.source)

    def test_wheel_forged_record_and_source_bytes_both_rejected(self):
        with TemporaryDirectory(prefix="UCIE_FORGED_ZIP_") as folder:
            file = inert_product_wheel(Path(folder), self.source, forged=True)
            with self.assertRaises(full.OfflineFullProductError):
                full._inspect_first_party_wheel(file, self.source)
        with TemporaryDirectory(prefix="UCIE_MODIFIED_SOURCE_") as folder:
            file = inert_product_wheel(Path(folder), self.source)
            altered = dict(self.source)
            altered["src/ucie_miner/customer_staging_v01.py"] += b"OTHER"
            with self.assertRaises(full.OfflineFullProductError):
                full._inspect_first_party_wheel(file, altered)

    def test_product_requirements_sha256_pins_are_all_four(self):
        requirements = full._requirements(HASHES, "d"*64)
        self.assertEqual(requirements.count("--hash=sha256:"), 4)
        self.assertIn("ucie-public-only-demo==0.1.0 --hash=sha256:", requirements)
        with self.assertRaises(full.OfflineFullProductError):
            full._requirements(HASHES, "NOT_SHA256")

    def test_stdlib_built_wheel_record_and_install_no_online_index(self):
        with TemporaryDirectory(prefix="UCIE_STDLIB_WHEEL_") as temp:
            wheel = full._build_first_party_wheel(Path(temp), self.source)
            self.assertEqual(wheel.name, full.FIRST_PARTY_WHEEL)
            report = full._inspect_first_party_wheel(wheel, self.source)
            self.assertTrue(report["source_code_bytes_match"])
            with self.assertRaises(full.OfflineFullProductError):
                full._build_first_party_wheel(Path(temp), self.source)
        install = full._install_cmd(
            Path("C:/UCIE_SYNTHETIC/recipient/python.exe"),
            self.root / "vendor", self.root / "product", self.root / "requirements")
        self.assertIn("--no-index", install)
        self.assertIn("--require-hashes", install)
        self.assertIn("--only-binary=:all:", install)
        self.assertEqual(install.count("--find-links"), 2)
        self.assertNotIn("--trusted-host", install)

    def test_real_native_and_four_pillar_contracts_are_fail_closed(self):
        good_native = {
            "versions": dict(acquire.PINNED),
            "cryptography_aesgcm_roundtrip": True,
            "cffi_declaration_parsed": True,
            "pycparser_c_declaration_parsed": True, "synthetic_only": True,
        }
        self.assertTrue(full._check_native(json.dumps(good_native))[
            "cryptography_aesgcm_roundtrip"])
        good_native["versions"]["cffi"] = "2.0.0"
        with self.assertRaises(full.OfflineFullProductError):
            full._check_native(json.dumps(good_native))
        pillars = {
            "schema": "UCIE_FOUR_PILLAR_INSTALLED_STAGING_V01",
            "four_pillars_exercised": True,
            "product_capabilities_worked_in_staging": True,
            "customer_distribution_authorized": False,
            "operating_ucie_database_written": False,
            "customer_data_scanned": False,
            "automatic_rule_promotion": False,
            "pillars_exercised": list(PILLARS),
            "workflows": {p: {"status": "UCIE SYNTHETIC"} for p in PILLARS},
        }
        self.assertTrue(full._check_four_pillars(
            json.dumps(pillars))["first_party_four_pillars_synthetic_worked"])
        pillars["customer_distribution_authorized"] = True
        with self.assertRaises(full.OfflineFullProductError):
            full._check_four_pillars(json.dumps(pillars))

    def test_local_ui_probe_contract_blocks_forged_approval(self):
        ui = {
            "schema": "UCIE_C1_PORTABLE_LOCALHOST_PREVIEW_V01",
            "loopback_http_routes_checked": 5,
            "negative_post_checked": True, "bound_host": "127.0.0.1",
            "task_scheduler_modified": False,
            "customer_distribution_authorized": False
        }
        self.assertEqual(full._check_ui(json.dumps(ui))[
            "installed_local_ui_loopback_routes_verified"], 5)
        ui["task_scheduler_modified"] = True
        with self.assertRaises(full.OfflineFullProductError):
            full._check_ui(json.dumps(ui))

    def test_owner_gate_denies_synthetic_root_and_wrong_consent(self):
        with patch("subprocess.run", side_effect=AssertionError("NO PIP")), patch(
            "urllib.request.urlopen", side_effect=AssertionError("NO NETWORK")
        ):
            with self.assertRaises(full.OfflineFullProductError):
                full._owner_gate(self.root)
            with patch.object(full, "_owner_gate",
                              side_effect=AssertionError("NO GATE BEFORE CONSENT")):
                with self.assertRaises(full.OfflineFullProductError):
                    full.run_owner_full_product(self.root, "DENIED")

    def test_pip_failure_does_not_emit_vendor_or_file_logs(self):
        class Fake:
            returncode = 1
            stdout = "PRIVATE_UCIE_INERT_TEST"
            stderr = "PRIVATE_UCIE_INERT_TEST"
        with patch("subprocess.run", return_value=Fake()):
            with self.assertRaises(full.OfflineFullProductError) as cm:
                full._run([sys.executable, "-I", "-B", "-m", "pip"],
                          self.root, {}, "first-party stage")
        self.assertNotIn("PRIVATE_UCIE_INERT_TEST", str(cm.exception))

    def test_mocked_full_product_install_audit_never_executes_pip_or_vendor(self):
        (self.root / "downloaded").mkdir()
        # Fixed C0 inventory + inert .py. All paths are first-party allowlisted.
        files = {
            name: b"# UCIE SYNTHETIC LOCAL REHEARSAL\n"
            for name in comp.FILES
        }
        files["src/ucie_miner/customer_portable_preview_v01.py"] = (
            b'REVISION = "UCIE_C1_DISPOSABLE_GENERATION_A"\n')
        files["src/ucie_miner/__init__.py"] = b"# UCIE synthetic init\n"
        files["src/ucie_public/__init__.py"] = b"# UCIE synthetic public\n"
        events = []
        def simulate(args, cwd, env, what):
            events.append(what)
            if what == "disposable full-product venv creation":
                child = Path(args[-1]) / "Scripts" / "python.exe"
                child.parent.mkdir(parents=True)
                child.write_bytes(b"UCIE NOT EXECUTABLE")
            if what == "hash-locked offline full-product install":
                data = Path(args[-1]).read_text(encoding="ascii")
                self.assertEqual(data.count("--hash=sha256:"), 4)
                self.assertIn("--no-index", args)
                self.assertNotIn("--index-url", args)
            if what == "native ABI trial":
                return json.dumps({
                    "versions": dict(acquire.PINNED),
                    "cryptography_aesgcm_roundtrip": True,
                    "cffi_declaration_parsed": True,
                    "pycparser_c_declaration_parsed": True,
                    "synthetic_only": True
                })
            if what == "installed four-pillar first-party CLI":
                return json.dumps({
                    "schema": "UCIE_FOUR_PILLAR_INSTALLED_STAGING_V01",
                    "four_pillars_exercised": True,
                    "product_capabilities_worked_in_staging": True,
                    "customer_distribution_authorized": False,
                    "operating_ucie_database_written": False,
                    "customer_data_scanned": False,
                    "automatic_rule_promotion": False,
                    "pillars_exercised": list(PILLARS),
                    "workflows": {p: {"status": "synthetic"} for p in PILLARS},
                })
            if what == "installed Local V04 UI":
                return json.dumps({
                    "schema": "UCIE_C1_PORTABLE_LOCALHOST_PREVIEW_V01",
                    "loopback_http_routes_checked": 5,
                    "negative_post_checked": True, "bound_host": "127.0.0.1",
                    "task_scheduler_modified": False,
                    "customer_distribution_authorized": False,
                })
            return ""
        graph = {"missing_first_party_imports": []}
        with patch.object(full, "_owner_gate", return_value=Path(sys.executable)), patch.object(
            full, "_dependency_evidence", return_value=(HASHES, "a"*64)
        ), patch.object(runtime, "inspect_static_runtime_closure",
                       return_value=graph), patch.object(
            runtime, "_copy_payload", return_value=files
        ), patch.object(full, "_run", side_effect=simulate), patch(
            "subprocess.run", side_effect=AssertionError("NO REAL PROCESS")
        ), patch("urllib.request.urlopen", side_effect=AssertionError("NO NETWORK")):
            receipt = full.run_owner_full_product(self.root, full.CONSENT)
        self.assertEqual(len(events), 6)
        self.assertTrue(receipt["temporary_first_party_wheel_and_venv_removed"])
        self.assertTrue(receipt["offline_install_requires_four_sha256_hashes"])
        self.assertFalse(receipt["second_clean_windows_host_accepted"])
        self.assertFalse(receipt["customer_distribution_authorized"])
        self.assertTrue((self.root / full.RECEIPT).is_file())
        self.assertFalse(any(p.is_dir() for p in (self.root / "downloaded").glob("ucie_c1_full_product_*")))

    def test_cli_preview_refuses_apply_without_user_prompt(self):
        fake_path = (self.root / "src" / "ucie_miner" /
                     "customer_full_product_offline_rehearsal_v01.py")
        text = io.StringIO()
        with patch.object(full, "__file__", str(fake_path)), patch(
            "subprocess.run", side_effect=AssertionError("NO PROCESS")
        ), redirect_stdout(text):
            rc = full.main([])
        self.assertEqual(rc, 0)
        self.assertFalse(json.loads(text.getvalue())["customer_distribution_authorized"])

    def test_owner_checkout_readonly_preflight_only(self):
        real = Path(__file__).resolve().parents[1]
        if real.name.casefold() != "ucie" or not (real / ".git").is_dir():
            self.skipTest("only exact UCIE checkout")
        state = full.preview(real)
        print("UCIE_C1_FULL_PRODUCT_OWNER_READINESS=" + state["readiness"])
        self.assertEqual(state["mode"], "OFFLINE_READONLY_PREVIEW")
        self.assertFalse(state["customer_distribution_authorized"])
        self.assertFalse(state["download_or_pip_executed"])


if __name__ == "__main__":
    unittest.main()
