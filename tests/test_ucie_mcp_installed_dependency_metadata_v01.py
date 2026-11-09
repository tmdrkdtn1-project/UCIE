"""Offline UCIE-only tests for SDK dependency metadata evidence; no package install."""
from __future__ import annotations

from email.message import Message
import importlib.util
from pathlib import Path
from unittest.mock import patch
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ucie_mcp_installed_dependency_metadata_v01.py"
spec = importlib.util.spec_from_file_location("ucie_mcp_dep_metadata", SCRIPT)
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

LOCK = (
    'version = 1\n'
    '[[package]]\nname = "mcp"\nsource = {editable = "."}\n'
    '[[package]]\nname = "mcp-types"\n'
    'source = {editable = "src/mcp-types"}\n'
    '[[package]]\nname = "anyio"\nversion = "4.14.2"\n'
    'source = {registry = "https://pypi.org/simple"}\n'
).encode("utf-8")


def row(name, version, status="SPDX_EXPRESSION_DECLARED", expression="MIT"):
    return {
        "name": name, "version": version,
        "license_status": status, "spdx_expression": expression,
        "license_file_count": 1, "metadata_sha256": "a" * 64,
    }


def fixture_lock():
    return {
        "mcp": [{"name": "mcp", "source": {"editable": "."}}],
        "mcp-types": [{"name": "mcp-types", "source": {"editable": "src/mcp-types"}}],
        "anyio": [{"name": "anyio", "version": "4.14.2",
                   "source": {"registry": m.REGISTRY}}],
    }


class InstalledDependencyMetadataTests(unittest.TestCase):
    def test_exact_approved_sdk_commits_and_lock_git_objects(self):
        self.assertEqual(m.COMMIT_BY_STAGE["before"],
                         "2118f14f8a19bc158d8a1cf90af58d85d187f849")
        self.assertEqual(m.COMMIT_BY_STAGE["after"],
                         "754254c08fe1c3eda18b69da3d336106fe8d72d6")
        self.assertEqual(m.LOCK_BLOB_BY_STAGE["before"],
                         "73fcc3331a93fc9442d8c2b2f85312d7cb389fbd")
        self.assertEqual(m.LOCK_BLOB_BY_STAGE["after"],
                         "fd2dcb85f9923798334ea6259522ae4ae84185f8")

    def test_git_sha_uses_git_blob_header(self):
        self.assertEqual(m.git_blob_sha(b"hello\n"),
                         "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_source_lock_requires_exact_sha_and_workspace_pins(self):
        sha = m.git_blob_sha(LOCK)
        with patch.dict(m.LOCK_BLOB_BY_STAGE, {"before": sha}):
            result = m.parse_lock(LOCK, "before")
            self.assertEqual(len(result), 3)
            with self.assertRaisesRegex(m.MetadataAuditError, "PINNED_LOCK_BLOB_MISMATCH"):
                m.parse_lock(LOCK + b"\n", "before")
        with patch.dict(m.LOCK_BLOB_BY_STAGE, {"before": m.git_blob_sha(
            LOCK.replace(b'src/mcp-types', b'other-directory')
        )}):
            with self.assertRaisesRegex(m.MetadataAuditError, "WORKSPACE_SOURCE_NOT_PINNED"):
                m.parse_lock(LOCK.replace(b'src/mcp-types', b'other-directory'), "before")

    def test_wrong_pypi_version_or_registry_fails_closed(self):
        for bad in (
            row("anyio", "0.1"),
            row("anyio", "4.14.2"),
        ):
            if bad["version"] == "4.14.2":
                lock = fixture_lock()
                lock["anyio"][0]["source"] = {"registry": "https://unapproved.example/simple"}
            else:
                lock = fixture_lock()
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(m.MetadataAuditError,
                                            "INSTALLED_VERSION_OR_REGISTRY_NOT_IN_LOCK"):
                    m.validate_inventory(lock, [row("mcp", "2.3.0"),
                                                row("mcp-types", "2.3.0"), bad])

    def test_valid_locked_versions_still_never_approve_license(self):
        result = m.validate_inventory(fixture_lock(), [
            row("mcp", "2.3.1.dev9+754254c"),
            row("mcp-types", "2.3.1.dev9+754254c"),
            row("anyio", "4.14.2"),
        ])
        self.assertEqual(len(result), 3)
        self.assertTrue(all(x["legal_approval"] is False for x in result))
        self.assertTrue(all(x["security_advisories_checked"] is False for x in result))
        self.assertEqual(result[0]["source_marker"], "PYPI_REGISTRY_PINNED_IN_UPSTREAM_LOCK")

    def test_unknown_package_and_duplicate_packages_rejected(self):
        valid = [row("mcp", "2.3.0"), row("mcp-types", "2.3.0")]
        with self.assertRaisesRegex(m.MetadataAuditError, "INSTALLED_DISTRIBUTION_ABSENT"):
            m.validate_inventory(fixture_lock(), valid + [row("unreviewed", "1.0")])
        with self.assertRaisesRegex(m.MetadataAuditError, "DUPLICATE_OR_INVALID"):
            m.validate_inventory(fixture_lock(), valid + [row("mcp", "2.3.0")])

    def test_license_expression_marker_is_not_legal_approval(self):
        fields = Message()
        fields["License-Expression"] = "Apache-2.0 OR MIT"
        fields["License-File"] = "LICENSE"
        self.assertEqual(m.read_license_marker(fields),
                         ("SPDX_EXPRESSION_DECLARED", "Apache-2.0 OR MIT", 1))
        fields = Message()
        fields["License"] = "X" * 200
        self.assertEqual(m.read_license_marker(fields)[0],
                         "LONG_LICENSE_TEXT_UNREVIEWED")

    def test_missing_or_classifier_only_license_markers_are_not_approved(self):
        fields = Message()
        self.assertEqual(m.read_license_marker(fields)[0],
                         "NO_LICENSE_DECLARATION_IN_METADATA")
        fields.add_header("Classifier", "License :: OSI Approved :: MIT License")
        self.assertEqual(m.read_license_marker(fields)[0], "LICENSE_CLASSIFIER_ONLY")
        fields = Message()
        fields["License-Expression"] = "UNTRUSTED^SPDX"
        self.assertEqual(m.read_license_marker(fields)[0],
                         "MALFORMED_OR_UNREVIEWED_SPDX")

    def test_malformed_dependency_metadata_does_not_pass(self):
        broken = row("mcp", "2.3.0")
        broken["metadata_sha256"] = "not-a-hash"
        with self.assertRaisesRegex(m.MetadataAuditError, "METADATA_HASH_REQUIRED"):
            m.validate_inventory(fixture_lock(), [broken, row("mcp-types", "2.3.0")])
        with self.assertRaisesRegex(m.MetadataAuditError, "INVALID_DISTRIBUTION_NAME"):
            m.normalized("../another")

    def test_owner_host_cannot_run_research_dependency_audit(self):
        with patch.dict("os.environ", {"UCIE_DISPOSABLE_SDK_GATE": ""}):
            with self.assertRaisesRegex(m.MetadataAuditError,
                                        "DISPOSABLE_EXACT_COMMIT_RUNNER_REQUIRED"):
                m.audit_installed("before", Path("."))


if __name__ == "__main__":
    unittest.main()
