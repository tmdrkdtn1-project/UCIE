"""C1 real import closure, portable self-contained loopback and version A/B drill.

Synthetic hostile file and staging tests never examine unrelated projects.
The owner/clean-CI smoke reads only the exact UCIE public first-party sources,
copies those sources into NEW UCIE temporary roots, then launches python -I
without inheriting PYTHONPATH or touching the running owner localhost app.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucie_miner import customer_portable_preview_v01 as preview
from ucie_miner import customer_runtime_closure_v01 as closure


class UCIEPortableC1RuntimeClosureTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="UCIE_C1_IMPORT_TEST_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "UCIE"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        for package in closure.PACKAGES:
            (self.root / "src" / package).mkdir(parents=True)
            (self.root / "src" / package / "__init__.py").write_bytes(b"\n")
        for module in closure.ENTRY_MODULES:
            rel = self.root / "src" / Path(*module.split(".")).with_suffix(".py")
            rel.write_text("# UCIE isolated synthetic import stub\n",
                           encoding="utf-8")

    def test_approved_packages_entrypoints_and_unsupported_gates(self):
        snapshot = closure.inspect_static_runtime_closure(self.root)
        self.assertEqual(snapshot["schema"], closure.SCHEMA)
        self.assertEqual(snapshot["status"], closure.STATE)
        self.assertTrue(snapshot["first_party_static_scan_completed"])
        self.assertEqual(snapshot["entry_modules"], list(closure.ENTRY_MODULES))
        self.assertGreaterEqual(snapshot["statically_reachable_first_party_modules"], 6)
        self.assertFalse(snapshot["full_runtime_import_closure_attested"])
        self.assertFalse(snapshot["external_dependency_wheelhouse_included"])
        self.assertFalse(snapshot["customer_distribution_authorized"])
        self.assertEqual(snapshot["external_network_requests"], 0)
        self.assertEqual(snapshot["operating_database_writes"], 0)

    def test_transitive_internal_imports_are_included_not_executed(self):
        node = self.root / "src" / "ucie_miner" / "local_v1_app_v01.py"
        node.write_text("from . import extra\nfrom .extra import handler\n"
                        "import cryptography\n", encoding="utf-8")
        dep = self.root / "src" / "ucie_miner" / "extra.py"
        dep.write_text("handler = object()\n", encoding="utf-8")
        item = closure.inspect_static_runtime_closure(self.root)
        self.assertIn("src/ucie_miner/extra.py", item["reachable_files"])
        self.assertIn("cryptography", item["external_import_roots"])
        self.assertNotIn("ucie_miner.extra", item["missing_first_party_imports"])

    def test_missing_internal_import_surfaces_without_go(self):
        node = self.root / "src" / "ucie_miner" / "local_v1_app_v01.py"
        node.write_text("from .missing_ucie_dependency import run\n",
                        encoding="utf-8")
        snapshot = closure.inspect_static_runtime_closure(self.root)
        self.assertIn("ucie_miner.missing_ucie_dependency",
                      snapshot["missing_first_party_imports"])
        with self.assertRaises(closure.ClosurePreviewError):
            closure.exercise_real_revision_ab_preview(self.root)

    def test_dynamic_import_is_not_mislabeled_complete(self):
        node = self.root / "src" / "ucie_miner" / "local_v1_app_v01.py"
        node.write_text('import importlib\n'
                        'name = "ucie_miner.unknown"\n'
                        'importlib.import_module(name)\n', encoding="utf-8")
        snapshot = closure.inspect_static_runtime_closure(self.root)
        self.assertTrue(any("local_v1_app_v01:" in x for x in
                            snapshot["dynamic_import_sites"]))
        self.assertFalse(snapshot["full_runtime_import_closure_attested"])

    def test_other_project_root_and_external_path_rejected(self):
        wrong = self.root.parent / "NotUCIE"
        wrong.mkdir()
        with self.assertRaises(closure.ClosurePreviewError):
            closure.inspect_static_runtime_closure(wrong)
        with self.assertRaises(preview.PortablePreviewError):
            preview.probe_preview_root(self.root)
        with self.assertRaises(closure.ClosurePreviewError):
            closure._version_payload({closure.PREVIEW_SOURCE: b""},
                                     "RELEASE_GO")

    def test_symlinked_first_party_python_rejected(self):
        target = self.root / "src" / "ucie_miner" / "local_v1_app_v01.py"
        target.unlink()
        outside = self.root / "UCIE_SYNTHETIC_INERT_TEXT"
        outside.write_text("UCIE TEST\n", encoding="utf-8")
        try:
            target.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Windows symlink permission unavailable")
        with self.assertRaises(closure.ClosurePreviewError):
            closure.inspect_static_runtime_closure(self.root)

    def test_stage_rejects_unsafe_names_before_any_write(self):
        bad_names = (
            "../other_project.py",
            "src/ucie_miner/../../other_project.py",
            "src\\\\ucie_miner\\\\name.py",
            "src/ucie_miner/unknown.txt",
            ".git/config",
            "runtime/operating.sqlite3",
            "src/ucie_miner/evil\\x00name.py",
        )
        for name in bad_names:
            with self.subTest(name=repr(name)):
                with TemporaryDirectory(prefix="UCIE_C1_FAIL_PATH_") as folder:
                    root = Path(folder) / "UCIE"
                    with self.assertRaises(closure.ClosurePreviewError):
                        closure._stage(
                            root, {name: b"UCIE INERT TEXT"},
                            closure.REVISION_A
                        )
                    self.assertFalse(root.exists())

    def test_nonempty_git_history_never_accepted_as_disposable_marker(self):
        with TemporaryDirectory(prefix="UCIE_C1_GIT_MARKER_") as folder:
            root = Path(folder) / "UCIE"
            (root / ".git").mkdir(parents=True)
            (root / ".git" / "config").write_text("UCIE TEST ONLY")
            (root / preview.MARKER_NAME).write_bytes(preview.MARKER_BYTES)
            source = root / "src" / "ucie_miner" / "local_v1_app_v01.py"
            source.parent.mkdir(parents=True)
            source.write_text("# UCIE inert source")
            with self.assertRaises(preview.PortablePreviewError):
                preview.probe_preview_root(root)

    def test_same_bytes_not_mislabeled_real_revision(self):
        src = {closure.PREVIEW_SOURCE: (
            b'REVISION = "UCIE_C1_DISPOSABLE_GENERATION_A"\n')}
        original = closure._version_payload(src, closure.REVISION_A)
        amended = closure._version_payload(src, closure.REVISION_B)
        self.assertNotEqual(original[closure.PREVIEW_SOURCE],
                            amended[closure.PREVIEW_SOURCE])
        self.assertNotEqual(closure._digest(original[closure.PREVIEW_SOURCE]),
                            closure._digest(amended[closure.PREVIEW_SOURCE]))
        self.assertEqual(src[closure.PREVIEW_SOURCE],
                         original[closure.PREVIEW_SOURCE])

    def test_manifest_slot_unknown_or_forged_approval_rejected(self):
        with TemporaryDirectory(prefix="UCIE_C1_SAFE_SLOT_") as base:
            root = Path(base) / "UCIE"
            payload = {"src/ucie_miner/test_inert.py": b"UCIE STAGING ONLY"}
            manifest = closure._stage(root, payload, closure.REVISION_A)
            closure._verify(root, manifest)
            with self.assertRaises(closure.ClosurePreviewError):
                closure._stage(root, payload, closure.REVISION_A)
            manipulated = dict(manifest, customer_distribution_authorized=True)
            with self.assertRaises(closure.ClosurePreviewError):
                closure._verify(root, manipulated)
            (root / "source_customer_key.txt").write_bytes(b"NO REAL KEY")
            with self.assertRaises(closure.ClosurePreviewError):
                closure._verify(root, manifest)

    def test_source_read_never_calls_network_or_external_process(self):
        with patch("subprocess.run",
                   side_effect=AssertionError("no process during AST scan")), patch(
            "socket.create_connection",
            side_effect=AssertionError("no network during AST scan")
        ):
            report = closure.inspect_static_runtime_closure(self.root)
            self.assertEqual(report["external_network_requests"], 0)

    def test_real_ucie_checkout_portable_a_b_rollback_and_runtime_probe(self):
        real = Path(__file__).resolve().parents[1]
        if real.name.casefold() != "ucie" or not (real / ".git").is_dir():
            self.skipTest("exact UCIE checkout required")
        before = closure.inspect_static_runtime_closure(real)
        print("UCIE_C1_STATIC_CLOSURE_COUNTS=" + str({
            "indexed": before["all_python_modules_indexed"],
            "reachable": before["statically_reachable_first_party_modules"],
            "dynamic_sites": len(before["dynamic_import_sites"]),
            "missing_first_party": len(before["missing_first_party_imports"]),
            "external_roots": len(before["external_import_roots"]),
        }))
        self.assertFalse(before["customer_distribution_authorized"])
        outcome = closure.exercise_real_revision_ab_preview(real)
        self.assertEqual(outcome["schema"], closure.SCHEMA)
        self.assertNotEqual(outcome["revision_a_source_sha256"],
                            outcome["revision_b_source_sha256"])
        self.assertTrue(outcome["first_party_preview_executable_bytes_differ"])
        self.assertTrue(outcome["a_portable_loopback_probe_pass"])
        self.assertTrue(outcome["b_portable_loopback_probe_pass"])
        self.assertTrue(outcome["tampered_b_rejected"])
        self.assertTrue(outcome["rollback_to_a_portable_probe_pass"])
        self.assertTrue(outcome["staging_temp_removed"])
        self.assertFalse(outcome["full_product_code_version_upgrade_completed"])
        self.assertFalse(outcome["customer_distribution_authorized"])
        self.assertFalse(outcome["owner_resident_service_modified"])
        self.assertFalse(outcome["scheduler_modified"])
        self.assertEqual(outcome["operating_database_writes"], 0)
        after = closure.inspect_static_runtime_closure(real)
        self.assertEqual(after["reachable_files"], before["reachable_files"])


if __name__ == "__main__":
    unittest.main()
