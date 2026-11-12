"""UCIE-only C2 license-text review packet: synthetic ZIP fixtures; no code exec."""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from test_ucie_c2_supply_chain_review_v01 import PYPROJECT, synthetic_wheel
from ucie_miner.customer_c2_owner_license_review_packet_v01 import (
    C2PacketError, SCHEMA, STATUS, CONSENT, _safe_relative_name,
    prepare_owner_rights_packet, _owner_export_gate, export_once,
)
from ucie_miner.customer_owner_wheelhouse_acquire_v01 import (
    PINNED, RECEIPT, SCHEMA as C1_SCHEMA, STATUS as C1_STATUS, _requirements,
)
from ucie_miner.customer_offline_dependency_gate_v01 import WHEELHOUSE


class C2OwnerRightsPacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="UCIE_C2_SYNTHETIC_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / ".git").mkdir(parents=True)
        (self.root / "pyproject.toml").write_text(PYPROJECT)
        folder = self.root / WHEELHOUSE
        folder.mkdir(parents=True)
        self.wheels = {}
        files = []
        for name, version in PINNED:
            path = synthetic_wheel(folder, name, version)
            self.wheels[name] = path
            files.append({
                "distribution": name, "version": version,
                "filename": path.name,
                "sha256": sha256(path.read_bytes()).hexdigest(),
            })
        self.receipt = self.root / RECEIPT
        self.receipt.write_text(json.dumps({
            "schema": C1_SCHEMA, "status": C1_STATUS,
            "target": "win_amd64-cp315-standard",
            "pinned_versions": list(_requirements()),
            "files": files, "customer_release_authorized": False,
            "license_and_SPDX_approved": False,
        }), encoding="ascii")

    def test_actual_synthetic_license_texts_extracted_integrity_checked(self):
        packet, files = prepare_owner_rights_packet(self.root)
        self.assertEqual(packet["schema"], SCHEMA)
        self.assertEqual(packet["status"], STATUS)
        self.assertEqual(packet["license_file_count"], 3)
        self.assertEqual(set(x.split("/")[1] for x in files),
                         {name + "-" + version for name, version in PINNED})
        self.assertEqual(packet["license_total_bytes"], sum(map(len, files.values())))
        self.assertTrue(all(raw == b"UCIE authored synthetic test license fixture\n"
                            for raw in files.values()))
        self.assertTrue(all(x["redistribution_and_commercial_rights_approved"] is False
                            for x in packet["reviewed_packages"]))
        self.assertFalse(packet["customer_distribution_authorized"])
        self.assertEqual(packet["network_requests"], 0)
        self.assertEqual(packet["operating_database_writes"], 0)

    def test_no_local_packet_export_on_read_only_preview(self):
        prepare_owner_rights_packet(self.root)
        self.assertFalse((self.root / "downloaded" /
                          "ucie_c2_owner_only_license_review_v01").exists())

    def test_repeated_identical_preview_gives_same_evidence(self):
        a, _ = prepare_owner_rights_packet(self.root)
        b, _ = prepare_owner_rights_packet(self.root)
        self.assertEqual(a["parent_c2_evidence_sha256"], b["parent_c2_evidence_sha256"])
        self.assertEqual(a["review_entries_sha256"], b["review_entries_sha256"])

    def test_tampered_wheel_rejected_before_license_copy(self):
        target = self.wheels["cryptography"]
        target.write_bytes(target.read_bytes() + b"UCIE_NEGATIVE_TAMPER")
        with self.assertRaises(C2PacketError):
            prepare_owner_rights_packet(self.root)

    def test_missing_declared_license_rejected(self):
        old = self.wheels["pycparser"]
        old.unlink()
        new = synthetic_wheel(old.parent, "pycparser", "3.12", license_file=False)
        receipt = json.loads(self.receipt.read_text())
        for file in receipt["files"]:
            if file["distribution"] == "pycparser":
                file["sha256"] = sha256(new.read_bytes()).hexdigest()
        self.receipt.write_text(json.dumps(receipt))
        with self.assertRaises(C2PacketError):
            prepare_owner_rights_packet(self.root)

    def test_portable_path_denies_traversal_unicode_reserved_device(self):
        for name in ("/license", "../LICENSE", "nested/../../LICENSE",
                     "nested//LICENSE", "CON", "NUL.txt", "file.txt.",
                     "LICENSE:ads", "nested\\LICENSE", "💼.txt",
                     "bad\nnewline.txt"):
            self.assertFalse(_safe_relative_name(name), name)
        for name in ("LICENSE", "LICENSE.APACHE", "LICENSE-BSD", "nested/COPYING.txt"):
            self.assertTrue(_safe_relative_name(name), name)

    def test_export_denied_in_synthetic_root_even_with_exact_consent(self):
        with self.assertRaises(C2PacketError):
            _owner_export_gate(self.root, CONSENT)
        with self.assertRaises(C2PacketError):
            export_once(self.root, typed_consent=CONSENT)
        self.assertFalse(any((self.root / "downloaded").glob("ucie_c2_rights_staging_*")))

    def test_export_denied_with_missing_or_forged_consent(self):
        for typed in ("", "YES", CONSENT + " "):
            with self.assertRaises(C2PacketError):
                export_once(self.root, typed_consent=typed)


if __name__ == "__main__":
    unittest.main()
