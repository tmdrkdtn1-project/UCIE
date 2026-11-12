"""C2 offline SPDX review: synthetic wheel ZIP/RECORD only, no third-party execution."""
from __future__ import annotations

import base64
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile, ZIP_STORED

from ucie_miner.customer_c2_supply_chain_review_v01 import (
    C2ReviewError, SCHEMA, STATUS, inspect_c2, inspect_license_evidence,
    _licensed_path,
)
from ucie_miner.customer_owner_wheelhouse_acquire_v01 import (
    PINNED, RECEIPT, SCHEMA as C1_SCHEMA, STATUS as C1_STATUS, _requirements,
)
from ucie_miner.customer_offline_dependency_gate_v01 import (
    WHEELHOUSE, _inspect_wheel,
)

PYPROJECT = """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
[project]
name = "ucie-public-only-demo"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["cryptography>=50.0.2,<51"]
"""


def synthetic_wheel(folder: Path, name: str, version: str,
                    *, license_file: bool = True, expression: str = "MIT") -> Path:
    prefix = name.replace("-", "_") + "-" + version + ".dist-info/"
    filename = name + "-" + version + "-py3-none-any.whl"
    data = {
        prefix + "METADATA": (
            "Metadata-Version: 2.4\nName: " + name + "\nVersion: " + version
            + "\nLicense-Expression: " + expression + "\nLicense-File: LICENSE\n"
        ).encode(),
        prefix + "WHEEL": b"Wheel-Version: 1.0\nGenerator: ucietest\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        name + "/__init__.py": b"# UCIE synthetic-only inert fixture\n",
    }
    if license_file:
        data[prefix + "licenses/LICENSE"] = b"UCIE authored synthetic test license fixture\n"
    out = StringIO()
    rows = []
    for file, payload in sorted(data.items()):
        digest = base64.urlsafe_b64encode(sha256(payload).digest()).rstrip(b"=").decode()
        rows.append([file, "sha256=" + digest, str(len(payload))])
    rows.append([prefix + "RECORD", "", ""])
    csv.writer(out, lineterminator="\n").writerows(rows)
    data[prefix + "RECORD"] = out.getvalue().encode()
    target = folder / filename
    with ZipFile(target, "w", compression=ZIP_STORED) as zf:
        for member, payload in sorted(data.items()):
            zf.writestr(member, payload)
    return target


class C2SupplyChainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / ".git").mkdir(parents=True)
        (self.root / "pyproject.toml").write_text(PYPROJECT)
        self.wheels = self.root / WHEELHOUSE
        self.wheels.mkdir(parents=True)
        files = []
        self.locations = {}
        for name, version in PINNED:
            wheel = synthetic_wheel(self.wheels, name, version)
            self.locations[name] = wheel
            files.append({
                "distribution": name, "version": version,
                "filename": wheel.name, "sha256": sha256(wheel.read_bytes()).hexdigest(),
            })
        (self.root / RECEIPT).write_text(json.dumps({
            "schema": C1_SCHEMA, "status": C1_STATUS,
            "target": "win_amd64-cp315-standard",
            "pinned_versions": list(_requirements()), "files": files,
            "customer_release_authorized": False, "license_and_SPDX_approved": False,
        }), encoding="ascii")

    def test_real_synthetic_wheels_have_valid_record(self):
        for path in self.locations.values():
            self.assertTrue(_inspect_wheel(path)["metadata_record_sha256_verified"])

    def test_exact_three_metadata_components(self):
        output = inspect_c2(self.root)
        self.assertEqual(output["schema"], SCHEMA)
        self.assertEqual(output["status"], STATUS)
        self.assertEqual(output["package_count"], 3)
        self.assertEqual([x["name"] for x in output["packages"]],
                         ["cffi", "cryptography", "pycparser"])
        self.assertEqual(len(output["spdx_2_3_draft_noassertion"]["packages"]), 3)
        self.assertEqual(output["spdx_2_3_draft_noassertion"]["spdxVersion"], "SPDX-2.3")
        self.assertTrue(all(x["licenseDeclared"] == "NOASSERTION"
                            for x in output["spdx_2_3_draft_noassertion"]["packages"]))
        self.assertTrue(all(x["license_evidence"]["license_files"] for x in output["packages"]))
        self.assertFalse(output["c2_approved"])
        self.assertFalse(output["customer_distribution_authorized"])
        self.assertEqual(output["network_requests"], 0)

    def test_evidence_hash_deterministic(self):
        a, b = inspect_c2(self.root), inspect_c2(self.root)
        self.assertEqual(a["evidence_sha256"], b["evidence_sha256"])

    def test_notices_and_rights_never_approved_by_metadata(self):
        result = inspect_c2(self.root)
        self.assertIn("C2_VENDOR_LICENSE_NOTICE_LEGAL_REVIEW_MISSING",
                      result["blockers"])
        self.assertTrue(all(not p["rights_cleared"] for p in result["packages"]))

    def test_missing_license_evidence_is_a_review_blocker(self):
        name = "pycparser"
        old = self.locations[name]
        old.unlink()
        new = synthetic_wheel(self.wheels, name, "3.12", license_file=False)
        receipt = self.root / RECEIPT
        data = json.loads(receipt.read_text())
        for item in data["files"]:
            if item["distribution"] == name:
                item["sha256"] = sha256(new.read_bytes()).hexdigest()
        receipt.write_text(json.dumps(data))
        output = inspect_c2(self.root)
        self.assertIn("DECLARED_LICENSE_FILE_MISSING:pycparser", output["blockers"])
        self.assertIn("LICENSE_FILE_NOT_OBSERVED:pycparser", output["blockers"])

    def test_tampered_vendor_file_fails_closed(self):
        path = self.locations["cffi"]
        path.write_bytes(path.read_bytes() + b"modification")
        with self.assertRaises(C2ReviewError):
            inspect_c2(self.root)

    def test_unpinned_extra_wheel_fails_closed(self):
        synthetic_wheel(self.wheels, "rogue", "1.0.0")
        with self.assertRaises(C2ReviewError):
            inspect_c2(self.root)

    def test_missing_receipt_fails_closed(self):
        (self.root / RECEIPT).unlink()
        with self.assertRaises(C2ReviewError):
            inspect_c2(self.root)

    def test_unsafe_license_paths_rejected(self):
        for path in ["../LICENSE", "/LICENSE", "dir//LICENSE", r"..\LICENSE", ""]:
            self.assertFalse(_licensed_path(path))
        self.assertTrue(_licensed_path("nested/LICENSE"))

    def test_no_independent_rights_from_metadata(self):
        self.assertEqual(inspect_c2(self.root)["signing_or_release_performed"], False)
        self.assertEqual(inspect_c2(self.root)["vendor_code_executed_or_installed"], False)


if __name__ == "__main__":
    unittest.main()
