"""UCIE C0+C1 offline staging capsule: synthetic four-pillar acceptance.

No customer input, external network, production runtime, scheduled tasks or
commercial distribution. Archive integrity is checked before any approval.
"""
from __future__ import annotations

import base64
from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from ucie_miner import customer_offline_capsule_v01 as kit

WHEEL = "ucie_public_only_demo-0.1.0-py3-none-any.whl"


def _wheel(root: Path, *, missing: str = "", extra: str = "",
           crlf: bool = False, forged_record: bool = False) -> None:
    names = sorted(kit.REQUIRED - {missing}) if missing else sorted(kit.REQUIRED)
    metadata = ("Metadata-Version: 2.3\nName: ucie-public-only-demo\n"
                "Version: 0.1.0\nRequires-Dist: cryptography>=50.0.2,<51\n")
    entrypoint = ("[console_scripts]\n"
                  "ucie-product-preview = ucie_miner.customer_staging_v01:main\n")
    contents = {}
    for name in names:
        if name.endswith("RECORD"):
            continue
        if name.endswith("METADATA"):
            value = metadata
        elif name.endswith("entry_points.txt"):
            value = entrypoint
        elif name.endswith("WHEEL"):
            value = "Wheel-Version: 1.0\nTag: py3-none-any\n"
        else:
            value = "# UCIE synthetic first-party wheel inventory\n"
        if crlf:
            value = value.replace("\n", "\r\n")
        contents[name] = value.encode("utf-8")
    if extra:
        contents[extra] = b"FORBIDDEN"
    if kit.DIST + "RECORD" in names:
        rows = []
        for name, data in sorted(contents.items()):
            digest = base64.urlsafe_b64encode(sha256(data).digest()).rstrip(b"=")
            rows.append(name + ",sha256=" + digest.decode("ascii") + "," +
                        str(len(data)))
        rows.append(kit.DIST + "RECORD,,")
        record = ("\r\n" if crlf else "\n").join(rows) + (
            "\r\n" if crlf else "\n")
        contents[kit.DIST + "RECORD"] = record.encode("utf-8")
    if forged_record:
        target = "ucie_miner/capability_trials.py"
        if target in contents:
            contents[target] += b"# forged payload after RECORD\n"
    with ZipFile(root / "dist" / WHEEL, "w") as package:
        for name, value in sorted(contents.items()):
            package.writestr(name, value)

class OfflineCapsuleAcceptance(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="UCIE_CAPSULE_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "UCIE"
        (self.root / ".git").mkdir(parents=True)
        (self.root / "dist").mkdir()
        _wheel(self.root)

    def build(self):
        return kit.build_staging_capsule(self.root, WHEEL)

    @staticmethod
    def mutate(path: Path, target: str, replace):
        with ZipFile(path) as source:
            rows = [(name, source.read(name)) for name in source.namelist()]
        with ZipFile(path, "w") as output:
            for name, data in rows:
                output.writestr(name, replace(data) if name == target else data)

    def test_four_actual_synthetic_pillars_and_manifest(self):
        report = self.build()
        self.assertEqual(report["status"], kit.STATUS)
        self.assertTrue(report["payload_sha256_verified"])
        self.assertTrue(report["four_pillars_synthetically_exercised"])
        self.assertFalse(report["customer_distribution_authorized"])
        self.assertFalse(report["private_signatures_verified"])
        self.assertFalse(report["third_party_dependencies_bundled"])
        self.assertEqual(report["operating_database_writes"], 0)
        archive = self.root / "dist" / "staging" / report["capsule_name"]
        with ZipFile(archive) as source:
            self.assertEqual(len(source.namelist()), 4)
            receipt = json.loads(source.read("four_pillar_receipt.json"))
            manifest = json.loads(source.read("manifest.json"))
            self.assertEqual(set(receipt["workflows"]), set(kit.PILLARS))
            self.assertEqual(len(manifest["files"]), 3)
            self.assertEqual(manifest["blockers"], list(kit.BLOCKERS))
            self.assertIs(manifest["signature_verified"], False)
            self.assertIs(manifest["dependencies_bundled"], False)
        self.assertEqual(kit.verify_staging_capsule(
            self.root, report["capsule_name"])["capsule_sha256"],
            report["capsule_sha256"])

    def test_nonoverwrite_on_repeat(self):
        first = self.build()
        target = self.root / "dist" / "staging" / first["capsule_name"]
        original = target.read_bytes()
        with self.assertRaises(FileExistsError):
            self.build()
        self.assertEqual(target.read_bytes(), original)

    def test_manifest_forged_signed_flag_fails(self):
        r = self.build()
        target = self.root / "dist" / "staging" / r["capsule_name"]
        self.mutate(target, "manifest.json",
                    lambda d: d.replace(b'"signature_verified":false',
                                        b'"signature_verified":true'))
        with self.assertRaises(kit.OfflineCapsuleError):
            kit.verify_staging_capsule(self.root, r["capsule_name"])

    def test_receipt_forged_release_flag_fails(self):
        r = self.build()
        target = self.root / "dist" / "staging" / r["capsule_name"]
        self.mutate(target, "four_pillar_receipt.json",
                    lambda d: d.replace(
                        b'"customer_distribution_authorized":false',
                        b'"customer_distribution_authorized":true'))
        with self.assertRaises(kit.OfflineCapsuleError):
            kit.verify_staging_capsule(self.root, r["capsule_name"])

    def test_missing_wheel_module_fails(self):
        _wheel(self.root, missing="ucie_miner/experience_evolution.py")
        with self.assertRaises(kit.OfflineCapsuleError):
            self.build()

    def test_windows_crlf_metadata_and_record_are_accepted(self):
        _wheel(self.root, crlf=True)
        result = self.build()
        self.assertTrue(result["payload_sha256_verified"])
        self.assertEqual(result["status"], kit.STATUS)

    def test_forged_wheel_record_digest_rejected(self):
        _wheel(self.root, forged_record=True)
        with self.assertRaises(kit.OfflineCapsuleError):
            self.build()

    def test_archive_traversal_fails(self):
        _wheel(self.root, extra="../other-project/file")
        with self.assertRaises(kit.OfflineCapsuleError):
            self.build()

    def test_unauthorized_wheel_names_fail(self):
        for name in ("../customer.whl", "other.whl", "", "wheels/malicious.whl"):
            with self.subTest(name=name), self.assertRaises(
                    kit.OfflineCapsuleError):
                kit.build_staging_capsule(self.root, name)

    def test_forged_functional_pass_cannot_be_bundled(self):
        with patch.object(kit, "run_four_pillar_staging", return_value={
                "schema": kit.FOUR_PILLAR_SCHEMA,
                "pillars_exercised": list(kit.PILLARS),
                "four_pillars_exercised": True,
                "product_capabilities_worked_in_staging": True,
                "workflows": dict.fromkeys(kit.PILLARS, {}),
                "customer_distribution_authorized": True}):
            with self.assertRaises(kit.OfflineCapsuleError):
                self.build()
        self.assertFalse((self.root / "dist" / "staging").exists())

    def test_no_customer_identifiers_in_manifest(self):
        r = self.build()
        with ZipFile(self.root / "dist" / "staging" / r["capsule_name"]) as source:
            manifest = json.loads(source.read("manifest.json"))
            self.assertNotIn("customer_id", manifest)
            self.assertNotIn("license_key", manifest)
            self.assertNotIn("owner_path", manifest)

    def test_cli_fail_closed_on_traversal(self):
        r = self.build()
        with redirect_stdout(StringIO()) as out:
            status = kit.main(["--root", str(self.root), "--verify",
                               r["capsule_name"]])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(out.getvalue())["status"], kit.STATUS)
        with redirect_stdout(StringIO()) as out:
            status = kit.main(["--root", str(self.root), "--verify", "../secret"])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(out.getvalue())["status"],
                         "UCIE_OFFLINE_STAGING_CAPSULE_FAIL_CLOSED")

    def test_other_project_root_rejected(self):
        with self.assertRaises(kit.OfflineCapsuleError):
            kit.build_staging_capsule(self.root.parent, WHEEL)


if __name__ == "__main__":
    unittest.main()
