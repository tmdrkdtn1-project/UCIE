"""UCIE C0/C1 whole-component census and isolated lifecycle safety tests.

All destructive test mutations target synthetic files created under a fresh
UCIE-named TemporaryDirectory. The optional real-checkout smoke only READS
exact first-party source files and stages COPIES under a disposable scratch.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import customer_component_lifecycle_v01 as pkg


class CompleteComponentLifecycleTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory(prefix="UCIE_C0_C1_TEST_")
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name) / "UCIE"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        for relative in pkg.FILES:
            p = self.root.joinpath(*relative.split("/"))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(("UCIE ONLY INERT COMPONENT " + relative + "\n")
                          .encode("utf-8"))

    def test_real_four_pillars_and_non_wheel_surface_census(self):
        snapshot = pkg.inspect_component_census(self.root)
        self.assertEqual(snapshot["schema"], pkg.SCHEMA)
        self.assertEqual(snapshot["status"], pkg.STATUS)
        self.assertEqual(snapshot["first_party_file_count"], 23)
        self.assertEqual(snapshot["four_pillars_present_in_census"],
                         list(pkg.PILLARS))
        self.assertEqual(set(snapshot["groups"]), set(pkg.GROUPS))
        self.assertEqual(set(snapshot["pillar_gap_matrix"]), set(pkg.PILLARS))
        for entry in snapshot["pillar_gap_matrix"].values():
            self.assertTrue(entry["first_party_source_present_in_census"])
            self.assertFalse(entry["independent_behavior_qa_attested_by_census"])
            self.assertFalse(entry["approved_non_draft_output_attested_by_census"])
            self.assertFalse(entry["rights_and_security_cleared"])
            self.assertFalse(entry["customer_accepted"])
        self.assertTrue(snapshot["includes_local_ui_sources"])
        self.assertFalse(snapshot["windows_owner_scripts_customer_portable"])
        self.assertFalse(snapshot["transitive_python_package_closure_attested"])
        self.assertFalse(snapshot["dependencies_included"])
        self.assertFalse(snapshot["sbom_complete"])
        self.assertFalse(snapshot["signed_by_owner"])
        self.assertFalse(snapshot["customer_distribution_authorized"])
        self.assertFalse(snapshot["customer_data_read"])
        self.assertFalse(snapshot["other_project_access"])
        self.assertEqual(snapshot["network_requests"], 0)
        self.assertEqual(snapshot["task_scheduler_changes"], 0)

    def test_disposable_actual_copy_tamper_update_rollback_uninstall(self):
        before = pkg.inspect_component_census(self.root)
        receipt = pkg.exercise_disposable_lifecycle(self.root)
        after = pkg.inspect_component_census(self.root)
        self.assertEqual(after, before, "source must not change in drill")
        self.assertEqual(receipt["source_fingerprint_sha256"],
                         before["first_party_source_fingerprint_sha256"])
        for key in (
            "install_copy_and_manifest_verified",
            "tampered_staging_rejected_before_activation",
            "update_generation_switched_and_verified",
            "rollback_generation_restored_and_verified",
            "disposable_uninstall_clean",
        ):
            self.assertTrue(receipt[key], key)
        for key in (
            "actual_code_version_changed",
            "actual_customer_installer_executed",
            "customer_release_artifact_created",
            "dependencies_included",
            "signed_by_owner",
            "customer_distribution_authorized",
            "customer_data_read",
            "other_project_access",
        ):
            self.assertFalse(receipt[key], key)
        self.assertEqual(receipt["network_requests"], 0)
        self.assertEqual(receipt["operating_database_writes"], 0)

    def test_missing_pillar_source_blocks_without_partial_pass(self):
        path = self.root / pkg.FILES[0]
        path.unlink()
        with self.assertRaises(pkg.ComponentLifecycleError):
            pkg.inspect_component_census(self.root)
        with self.assertRaises(pkg.ComponentLifecycleError):
            pkg.exercise_disposable_lifecycle(self.root)

    def test_oversized_and_empty_first_party_file_block(self):
        target = self.root / pkg.FILES[0]
        target.write_bytes(b"")
        with self.assertRaises(pkg.ComponentLifecycleError):
            pkg.inspect_component_census(self.root)
        target.write_bytes(b"1" * (pkg.MAX_FILE_BYTES + 1))
        with self.assertRaises(pkg.ComponentLifecycleError):
            pkg.inspect_component_census(self.root)

    def test_unknown_paths_cannot_extend_allowlist(self):
        for p in (
            "../../another_project/secret.txt",
            "runtime/public_miner.sqlite3",
            ".github/workflows/test.yml",
            "/etc/passwd",
            "src/ucie_miner/customer_id.json",
        ):
            with self.subTest(p=p):
                with self.assertRaises(pkg.ComponentLifecycleError):
                    pkg._allowed_path(p)

    def test_symlink_component_is_rejected(self):
        target = self.root / pkg.FILES[0]
        other = target.parent / "UCIE_SYNTHETIC_OTHER"
        other.write_bytes(b"UCIE INERT")
        target.unlink()
        try:
            target.symlink_to(other)
        except (OSError, NotImplementedError):
            self.skipTest("symlink privilege unavailable on this Windows runner")
        with self.assertRaises(pkg.ComponentLifecycleError):
            pkg.inspect_component_census(self.root)

    def test_wrong_root_or_missing_git_never_scans(self):
        wrong = self.root.parent / "NotUCIE"
        wrong.mkdir()
        with self.assertRaises(pkg.ComponentLifecycleError):
            pkg.inspect_component_census(wrong)
        (self.root / ".git").rmdir()
        with self.assertRaises(pkg.ComponentLifecycleError):
            pkg.inspect_component_census(self.root)

    def test_staging_slot_replay_and_manifest_tamper_fail_closed(self):
        payload = pkg._payload(self.root)
        manifest = pkg._manifest(payload)
        with tempfile.TemporaryDirectory(prefix="UCIE_SLOT_TEST_") as temp:
            slot = Path(temp) / "slot"
            pkg._stage(slot, payload, manifest)
            pkg._verify(slot, payload, manifest)
            with self.assertRaises(pkg.ComponentLifecycleError):
                pkg._stage(slot, payload, manifest)
            (slot / "manifest.json").write_bytes(b"UCIE FORGED APPROVAL")
            with self.assertRaises(pkg.ComponentLifecycleError):
                pkg._verify(slot, payload, manifest)

    def test_unexpected_staged_payload_and_hash_tamper_block(self):
        payload = pkg._payload(self.root)
        manifest = pkg._manifest(payload)
        with tempfile.TemporaryDirectory(prefix="UCIE_UNEXPECTED_") as temp:
            slot = Path(temp) / "slot"
            pkg._stage(slot, payload, manifest)
            (slot / "customer_licence.key").write_bytes(b"UCIE TEST ONLY")
            with self.assertRaises(pkg.ComponentLifecycleError):
                pkg._verify(slot, payload, manifest)
            (slot / "customer_licence.key").unlink()
            file = slot.joinpath(*pkg.FILES[1].split("/"))
            file.write_bytes(file.read_bytes() + b"TAMPER")
            with self.assertRaises(pkg.ComponentLifecycleError):
                pkg._verify(slot, payload, manifest)

    def test_snapshot_does_not_touch_other_project_or_network(self):
        with patch("socket.create_connection",
                   side_effect=AssertionError("network forbidden")), patch(
            "subprocess.run",
            side_effect=AssertionError("subprocess forbidden")
        ):
            snapshot = pkg.inspect_component_census(self.root)
            self.assertEqual(snapshot["network_requests"], 0)
            receipt = pkg.exercise_disposable_lifecycle(self.root)
            self.assertEqual(receipt["task_scheduler_changes"], 0)

    def test_existing_ucie_source_readonly_owner_or_clean_ci(self):
        real = Path(__file__).resolve().parents[1]
        if real.name.casefold() != "ucie" or not (real / ".git").is_dir():
            self.skipTest("not an exact UCIE checkout")
        # This is a known-source inventory, not a statement of full release.
        report = pkg.inspect_component_census(real)
        self.assertEqual(report["first_party_file_count"], 23)
        self.assertFalse(report["customer_distribution_authorized"])
        self.assertTrue(all(
            len(entry["sha256"]) == 64 for entry in report["entries"]
        ))
        receipt = pkg.exercise_disposable_lifecycle(real)
        self.assertTrue(receipt["tampered_staging_rejected_before_activation"])
        self.assertTrue(receipt["disposable_uninstall_clean"])
        self.assertFalse(receipt["actual_customer_installer_executed"])
        self.assertFalse(receipt["actual_code_version_changed"])


if __name__ == "__main__":
    unittest.main()
