"""C1 offline wheelhouse integrity / dynamic-import review (never install code).

Synthetic ZIP/WHEEL fixtures contain only inert Python text and metadata.
Real owner/CI census reads only UCIE first-party source and fixed optional
UCIE wheelhouse directory; no pip, HTTP, signing, customer paths or DB writes.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from ucie_miner import customer_offline_dependency_gate_v01 as gate


PYPROJECT = """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "ucie-public-only-demo"
version = "0.1.0"
description = "UCIE staging only"
requires-python = ">=3.13"
dependencies = ["cryptography>=50.0.2,<51"]
"""


def _create_inert_wheel(
    wheelhouse: Path, *,
    distribution: str = "cryptography",
    version: str = "50.0.2",
    file_name: str | None = None,
    malformed_record: bool = False,
    requires_dist: str = "",
    extra_member: str | None = None,
) -> Path:
    wheelhouse.mkdir(parents=True, exist_ok=True)
    filename = file_name or (
        f"{distribution}-{version}-py3-none-any.whl"
    )
    dist = f"{distribution}-{version}.dist-info/"
    meta = (
        f"Metadata-Version: 2.3\nName: {distribution}\nVersion: {version}\n"
        + (f"Requires-Dist: {requires_dist}\n" if requires_dist else "")
    ).encode()
    contents = {
        dist + "METADATA": meta,
        dist + "WHEEL": b"Wheel-Version: 1.0\nGenerator: UCIE-inert-fixture\n",
        distribution + "/__init__.py": b"# UCIE-inert-text-NEVER-EXECUTE\n",
    }
    if extra_member is not None:
        contents[extra_member] = b"UCIE synthetic bad file\n"
    records = []
    for name, data in contents.items():
        digest = base64.urlsafe_b64encode(sha256(data).digest()).rstrip(b"=").decode()
        if malformed_record and name == dist + "METADATA":
            digest = "BAD_RECORD"
        records.append(f"{name},sha256={digest},{len(data)}")
    records.append(dist + "RECORD,,")
    contents[dist + "RECORD"] = ("\n".join(records) + "\n").encode()
    out = wheelhouse / filename
    with ZipFile(out, mode="w", compression=ZIP_DEFLATED) as archive:
        for name, content in contents.items():
            archive.writestr(name, content)
    return out


class UCIEC1OfflineDependencyAndDynamicTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="UCIE_C1_WHEEL_META_ONLY_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "UCIE"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        (self.root / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
        for package in ("ucie_miner", "ucie_public"):
            (self.root / "src" / package).mkdir(parents=True)
            (self.root / "src" / package / "__init__.py").write_text("\n")
        for module in (
            "ucie_miner.customer_portable_preview_v01",
            "ucie_miner.local_v1_app_v01",
            "ucie_miner.customer_staging_v01",
            "ucie_public.cli",
        ):
            target = self.root / "src" / Path(*module.split(".")).with_suffix(".py")
            target.write_text("# UCIE synthetic static code only\n")

    def test_no_wheelhouse_blocks_but_metadata_inventory_safe(self):
        out = gate.inspect_offline_dependency_gate(self.root)
        self.assertEqual(out["schema"], gate.SCHEMA)
        self.assertFalse(out["wheelhouse_present"])
        self.assertFalse(out["declared_requirement_wheel_observed"])
        self.assertIn("NO_OFFLINE_WHEELHOUSE_BUNDLED", out["blockers"])
        self.assertFalse(out["complete_transitive_dependency_closure_attested"])
        self.assertFalse(out["dependency_wheels_executed_or_installed"])
        self.assertFalse(out["customer_release_authorized"])
        self.assertEqual(out["project"]["declared_runtime_requirements"],
                         ["cryptography>=50.0.2,<51"])

    def test_valid_inert_wheel_record_integrity_is_metadata_only(self):
        folder = self.root / gate.WHEELHOUSE
        wheel = _create_inert_wheel(folder)
        evidence = gate._inspect_wheel(wheel)
        self.assertEqual(evidence["name"], "cryptography")
        self.assertEqual(evidence["version"], "50.0.2")
        self.assertTrue(evidence["metadata_record_sha256_verified"])
        self.assertFalse(evidence["package_code_executed"])
        self.assertFalse(evidence["publisher_signature_verified"])
        result = gate.inspect_offline_dependency_gate(self.root)
        self.assertTrue(result["declared_requirement_wheel_observed"])
        self.assertTrue(result["wheelhouse_present"])
        self.assertFalse(result["complete_transitive_dependency_closure_attested"])
        self.assertFalse(result["customer_release_authorized"])
        self.assertIn("THIRD_PARTY_LICENSE_SECURITY_SBOM_REVIEW_PENDING",
                      result["blockers"])

    def test_untrusted_record_digest_mismatch_rejected(self):
        wheel = _create_inert_wheel(self.root / gate.WHEELHOUSE,
                                   malformed_record=True)
        with self.assertRaises(gate.OfflineDependencyError):
            gate._inspect_wheel(wheel)

    def test_untrusted_archive_path_traversal_rejected(self):
        wheel = _create_inert_wheel(self.root / gate.WHEELHOUSE,
                                   extra_member="../another_project/secret.txt")
        with self.assertRaises(gate.OfflineDependencyError):
            gate._inspect_wheel(wheel)

    def test_filename_metadata_identity_spoofing_rejected(self):
        wheel = _create_inert_wheel(
            self.root / gate.WHEELHOUSE, distribution="cryptography",
            file_name="unexpected-50.0.2-py3-none-any.whl"
        )
        with self.assertRaises(gate.OfflineDependencyError):
            gate._inspect_wheel(wheel)

    def test_unknown_and_linked_wheelhouse_rejected(self):
        folder = self.root / gate.WHEELHOUSE
        folder.mkdir(parents=True)
        (folder / "unexpected.txt").write_text("DO NOT INSTALL")
        with self.assertRaises(gate.OfflineDependencyError):
            gate.inspect_offline_dependency_gate(self.root)

    def test_duplicate_distribution_wheels_rejected(self):
        folder = self.root / gate.WHEELHOUSE
        _create_inert_wheel(folder, version="50.0.2")
        _create_inert_wheel(folder, version="50.0.3")
        with self.assertRaises(gate.OfflineDependencyError):
            gate.inspect_offline_dependency_gate(self.root)

    def test_changed_pyproject_declared_dependency_fails_closed(self):
        (self.root / "pyproject.toml").write_text(
            PYPROJECT.replace("cryptography>=50.0.2,<51",
                              "cryptography>=1.0.0"), encoding="utf-8")
        with self.assertRaises(gate.OfflineDependencyError):
            gate.inspect_offline_dependency_gate(self.root)

    def test_bounded_dynamic_literal_and_variable_targets_flagged(self):
        target = (self.root / "src" / "ucie_miner" / "local_v1_app_v01.py")
        (self.root / "src" / "ucie_miner" / "extra.py").write_text(
            "# UCIE inert dynamic target\n")
        target.write_text(
            "import importlib\n"
            "importlib.import_module('ucie_miner.extra')\n"
            "target = 'ucie_miner.extra'\n"
            "importlib.import_module(target)\n", encoding="utf-8")
        result = gate.dynamic_import_risks(self.root)
        self.assertEqual(result["source_site_count"], 2)
        self.assertEqual(result["variable_sites"], 1)
        self.assertTrue(result["sites"][0]["static_target_known_in_ucie"])
        self.assertFalse(result["runtime_dynamic_imports_fully_resolved"])
        self.assertTrue(all(not x["dynamic_approval"] for x in result["sites"]))

    def test_incompatible_cryptography_version_is_not_accepted(self):
        folder = self.root / gate.WHEELHOUSE
        _create_inert_wheel(folder, version="49.0.0")
        result = gate.inspect_offline_dependency_gate(self.root)
        self.assertFalse(result["declared_requirement_wheel_observed"])
        self.assertIn("DECLARED_CRYPTOGRAPHY_VERSION_UNSATISFIED",
                      result["blockers"])
        self.assertFalse(result["customer_release_authorized"])

    def test_exact_fixed_stdlib_import_calls_are_classified_but_not_approved(self):
        target = self.root / "src" / "ucie_miner" / "local_v1_app_v01.py"
        target.write_text(chr(10).join([
            'x = __import__("os")',
            'y = __import__("argparse")',
            '',
        ]), encoding="utf-8")
        report = gate.dynamic_import_risks(self.root)
        self.assertEqual(report["source_site_count"], 2)
        self.assertEqual(report["unresolved_dynamic_targets"], 0)
        self.assertTrue(report["fixed_stdlib_import_sites_only"])
        self.assertFalse(report["runtime_dynamic_imports_fully_resolved"])

    def test_no_network_pip_process_or_other_project_read(self):
        with patch("subprocess.run", side_effect=AssertionError("no subprocess")), patch(
            "socket.create_connection", side_effect=AssertionError("no network")
        ):
            out = gate.inspect_offline_dependency_gate(self.root)
            self.assertEqual(out["network_requests"], 0)
            self.assertFalse(out["pip_no_index_install_executed"])
            self.assertFalse(out["other_project_access"])

    def test_source_bound_cli_never_calls_pip_or_returns_release_go(self):
        from contextlib import redirect_stdout
        from unittest.mock import patch
        log = io.StringIO()
        mock_src = self.root / "src" / "ucie_miner" / "customer_offline_dependency_gate_v01.py"
        with patch.object(gate, "__file__", str(mock_src)), redirect_stdout(log):
            code = gate.main(["--inspect"])
        self.assertEqual(code, 2)
        result = __import__("json").loads(log.getvalue())
        self.assertEqual(result["schema"], gate.SCHEMA)
        self.assertFalse(result["customer_release_authorized"])
        self.assertFalse(result["dependency_wheels_executed_or_installed"])
        self.assertFalse(result["pip_no_index_install_executed"])

    def test_real_ucie_checkout_annotates_pending_dynamic_and_wheels(self):
        real = Path(__file__).resolve().parents[1]
        if real.name.casefold() != "ucie" or not (real / ".git").is_dir():
            self.skipTest("exact UCIE checkout only")
        result = gate.inspect_offline_dependency_gate(real)
        print("UCIE_C1_OWNER_DEPENDENCY_SUMMARY=" + str({
            "dynamic_sites": [x["source_module"] + ":" + str(x["line"])
                              for x in result["dynamic_import_risk"]["sites"]],
            "dynamic_variable_sites": result["dynamic_import_risk"]["variable_sites"],
            "external_import_roots": result["external_import_roots"],
            "wheelhouse_present": result["wheelhouse_present"],
            "observed_wheels": len(result["wheel_metadata"]),
        }))
        self.assertIn("cryptography>=50.0.2,<51",
                      result["project"]["declared_runtime_requirements"])
        self.assertFalse(result["customer_release_authorized"])
        self.assertFalse(result["complete_transitive_dependency_closure_attested"])
        self.assertTrue(result["dynamic_import_risk"]["fixed_stdlib_import_sites_only"])
        self.assertEqual(result["dynamic_import_risk"]["unresolved_dynamic_targets"], 0)
        self.assertFalse(result["dependency_wheels_executed_or_installed"])
        self.assertFalse(result["pip_no_index_install_executed"])
        self.assertEqual(result["operating_database_writes"], 0)


if __name__ == "__main__":
    unittest.main()
