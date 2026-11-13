"""UCIE C2 private NOTICE draft synthetic-only tests (no real vendor originals)."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucie_miner import customer_c2_private_notice_draft_v01 as draft
from test_ucie_c2_existing_owner_license_integrity_v01 import (
    ExistingOwnerC2FiveLicenseTextAuditTests,
)


class PrivateNoticeDraftTests(unittest.TestCase):
    def make(self, root: Path):
        return ExistingOwnerC2FiveLicenseTextAuditTests().build(root)

    def test_01_stage_exact_five_original_bytes_and_still_no_go(self):
        with TemporaryDirectory() as tmp:
            source, pin, manifest = self.make(Path(tmp))
            before = {p.relative_to(source).as_posix(): sha256(p.read_bytes()).hexdigest()
                      for p in source.rglob("*") if p.is_file()}
            result = draft.stage_owner_private_notice_draft(source, pin)
            target = source.parent / draft.DRAFT_NAME
            self.assertEqual(result["exact_existing_original_license_copies"], 5)
            self.assertFalse(result["customer_distribution_authorized"])
            self.assertTrue(result["open_ssl_notice_absent"])
            self.assertEqual(len(list(target.glob("LICENSE_ORIGINAL_*.txt"))), 5)
            self.assertEqual(sum(p.stat().st_size for p in target.glob("LICENSE_ORIGINAL_*.txt")),
                             manifest["license_total_bytes"])
            after = {p.relative_to(source).as_posix(): sha256(p.read_bytes()).hexdigest()
                     for p in source.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
            self.assertTrue((target / "NOTICE_REVIEW_REQUIRED.txt").is_file())

    def test_02_existing_draft_not_overwritten(self):
        with TemporaryDirectory() as tmp:
            source, pin, _ = self.make(Path(tmp))
            draft.stage_owner_private_notice_draft(source, pin)
            with self.assertRaises(ValueError):
                draft.stage_owner_private_notice_draft(source, pin)

    def test_03_wrong_independent_source_sha_blocks_copy(self):
        with TemporaryDirectory() as tmp:
            source, _, _ = self.make(Path(tmp))
            with self.assertRaises(ValueError):
                draft.stage_owner_private_notice_draft(source, "0" * 64)
            self.assertFalse((source.parent / draft.DRAFT_NAME).exists())

    def test_04_tampered_original_blocks_copy(self):
        with TemporaryDirectory() as tmp:
            source, pin, manifest = self.make(Path(tmp))
            rel = manifest["reviewed_packages"][0]["declared_license_texts"][0]["relative_review_path"]
            path = source.joinpath(*rel.split("/"))
            path.write_bytes(b"X" + path.read_bytes()[1:])
            with self.assertRaises(ValueError):
                draft.stage_owner_private_notice_draft(source, pin)
            self.assertFalse((source.parent / draft.DRAFT_NAME).exists())

    def test_05_tampered_private_license_bytes_blocks_recheck(self):
        with TemporaryDirectory() as tmp:
            source, pin, _ = self.make(Path(tmp))
            draft.stage_owner_private_notice_draft(source, pin)
            target = source.parent / draft.DRAFT_NAME
            f = target / "LICENSE_ORIGINAL_01.txt"
            f.write_bytes(b"X" + f.read_bytes()[1:])
            with self.assertRaises(ValueError):
                draft.verify_private_notice_draft(target, pin)

    def test_06_false_human_or_customer_release_approval_blocks_recheck(self):
        with TemporaryDirectory() as tmp:
            source, pin, _ = self.make(Path(tmp))
            draft.stage_owner_private_notice_draft(source, pin)
            target = source.parent / draft.DRAFT_NAME
            f = target / "review_manifest.json"
            data = json.loads(f.read_text())
            data["customer_distribution_authorized"] = True
            f.write_bytes(draft._canonical(data))
            with self.assertRaises(ValueError):
                draft.verify_private_notice_draft(target, pin)

    def test_07_open_ssl_notice_absence_cannot_be_forged(self):
        with TemporaryDirectory() as tmp:
            source, pin, _ = self.make(Path(tmp))
            draft.stage_owner_private_notice_draft(source, pin)
            target = source.parent / draft.DRAFT_NAME
            f = target / "review_manifest.json"
            data = json.loads(f.read_text())
            data["open_ssl_embedded_notice_included"] = True
            f.write_bytes(draft._canonical(data))
            with self.assertRaises(ValueError):
                draft.verify_private_notice_draft(target, pin)

    def test_08_extra_or_linked_private_file_fails_closed(self):
        with TemporaryDirectory() as tmp:
            source, pin, _ = self.make(Path(tmp))
            draft.stage_owner_private_notice_draft(source, pin)
            target = source.parent / draft.DRAFT_NAME
            (target / "CUSTOMER_GO.txt").write_text("YES")
            with self.assertRaises(ValueError):
                draft.verify_private_notice_draft(target, pin)

    def test_09_non_owner_cli_stays_no_go_and_no_write(self):
        with TemporaryDirectory() as tmp:
            source, pin, _ = self.make(Path(tmp))
            from contextlib import redirect_stdout
            from io import StringIO
            output = StringIO()
            with redirect_stdout(output):
                code = draft.main(["--owner-stage-private-review-only",
                                   "--expected-review-entries-sha256", pin])
            self.assertEqual(code, 2)
            self.assertFalse((source.parent / draft.DRAFT_NAME).exists())
            self.assertFalse(json.loads(output.getvalue())["customer_distribution_authorized"])

    def test_10_no_network_during_private_stage(self):
        with TemporaryDirectory() as tmp:
            source, pin, _ = self.make(Path(tmp))
            with patch("urllib.request.urlopen", side_effect=AssertionError("network request")):
                result = draft.stage_owner_private_notice_draft(source, pin)
            self.assertFalse(result["customer_distribution_authorized"])


if __name__ == "__main__":
    unittest.main()
