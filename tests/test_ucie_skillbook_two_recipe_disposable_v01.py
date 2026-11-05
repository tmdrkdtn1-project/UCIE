"""UCIE-only two-SkillBook disposable ZIP consumer acceptance.

Real Python -I -B subprocess, first-party synthetic bytes/files only.
No repo git invocation, operating DB, external project scans or release.
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from ucie_miner import skillbook_two_recipe_disposable_v01 as bundle


class TwoSkillBookDisposableConsumerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="UCIE_TWO_BOOKS_QA_")
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "UCIE_TWO_BOOKS_DRAFT_ONLY.zip"
        raw, self.receipt = bundle.build_draft_bundle()
        self.path.write_bytes(raw)
        self.assertEqual(sha256(raw).hexdigest(), self.receipt["archive_sha256"])

    def _run(self, payload: bytes, *args: str):
        return subprocess.run(
            [sys.executable, "-I", "-B", str(self.path), *args],
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=20, cwd=self.tmp.name, check=False)

    def test_reproducible_zip_and_exact_members(self):
        raw1, a = bundle.build_draft_bundle()
        raw2, b = bundle.build_draft_bundle()
        self.assertEqual(raw1, raw2)
        self.assertEqual(a, b)
        self.assertFalse(a["export_allowed"])
        self.assertFalse(a["release_approved"])
        self.assertFalse(a["independent_qa_verified"])
        self.assertEqual(a["files_written"], 0)
        with ZipFile(BytesIO(raw1)) as archive:
            self.assertEqual(archive.namelist(), list(bundle.ENTRY_NAMES))
            self.assertTrue(all(info.create_system == 3 for info in archive.infolist()))
            self.assertTrue(all(info.file_size <= 16000 for info in archive.infolist()))
            manifest = json.loads(archive.read("MANIFEST.json"))
            self.assertFalse(manifest["signed"])
            self.assertFalse(manifest["export_approved"])
            self.assertFalse(manifest["rights_approved"])
            self.assertFalse(manifest["released"])
            for name, digest in manifest["member_sha256"].items():
                self.assertEqual(sha256(archive.read(name)).hexdigest(), digest)

    def test_actual_python_isolated_git_consumer(self):
        data = b" M synthetic.txt\x00?? second.txt\x00"
        r = self._run(json.dumps({"action": "git-summary",
                                  "payload_hex": data.hex()}).encode("ascii"))
        self.assertEqual(r.returncode, 0, r.stderr.decode(errors="replace"))
        result = json.loads(r.stdout)
        self.assertEqual(result["result"]["total_entries"], 2)
        self.assertEqual(result["result"]["counts"]["tracked_changed"], 1)
        self.assertEqual(result["result"]["counts"]["untracked"], 1)
        self.assertNotIn("synthetic.txt", r.stdout.decode())
        self.assertNotIn("second.txt", r.stdout.decode())
        self.assertFalse(result["export_approved"])
        self.assertFalse(result["independent_qa_verified"])

    def test_actual_python_isolated_scandir_consumer(self):
        r = self._run(b'{"action":"scandir-synthetic"}')
        self.assertEqual(r.returncode, 0, r.stderr.decode(errors="replace"))
        j = json.loads(r.stdout)
        self.assertEqual(j["result"]["names"], ["alpha.txt", "zeta.txt"])
        self.assertTrue(j["result"]["synthetic_fixture_only"])
        self.assertFalse(j["other_project_access"])

    def test_actual_consumer_rejects_external_directory(self):
        for payload in (
            b'{"action":"scandir-synthetic","directory":"C:/private"}',
            b'{"action":"scandir-synthetic","approved":true}',
            b'{"action":"git-summary","payload_hex":"","path":"D:/UCIE"}',
            b'{"action":"git-summary","payload_hex":null}',
            b'{"action":"git-summary","payload_hex":"0g"}',
        ):
            with self.subTest(payload=payload):
                r = self._run(payload)
                self.assertEqual(r.returncode, 2)
                self.assertEqual(json.loads(r.stdout)["status"],
                                 "UCIE_FIRST_PARTY_DRAFT_FAIL_CLOSED")
                self.assertLessEqual(len(r.stdout), 80)

    def test_actual_consumer_rejects_overbudget_unknown_and_forgery(self):
        for payload in (
            b'{"action":"git-summary","payload_hex":"' + b"00" * 8193 + b'"}',
            b'{"action":"git-summary","payload_hex":"aa","action":"scandir-synthetic"}',
            b'{"action":"release"}',
            b'{"action":"git-summary","payload_hex":"","human_approved":true}',
            b'{"action":"git-summary","payload_hex":"","rights_approved":true}',
            b'{"action":"git-summary","payload_hex":"zz"}',
            b" " * 32769,
        ):
            with self.subTest(length=len(payload)):
                r = self._run(payload)
                self.assertEqual(r.returncode, 2)
                self.assertEqual(json.loads(r.stdout)["status"],
                                 "UCIE_FIRST_PARTY_DRAFT_FAIL_CLOSED")

    def test_actual_consumer_rejects_modified_member(self):
        with ZipFile(self.path, "a") as archive:
            archive.writestr("extra.py", "no")
        r = self._run(b'{"action":"scandir-synthetic"}')
        self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(r.stdout)["status"],
                         "UCIE_FIRST_PARTY_DRAFT_FAIL_CLOSED")

    def test_actual_consumer_rejects_cli_args(self):
        r = self._run(b'{"action":"scandir-synthetic"}', "--release")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(r.stdout)["status"],
                         "UCIE_FIRST_PARTY_DRAFT_FAIL_CLOSED")

    def test_builder_fails_when_pinned_first_party_source_differs(self):
        with patch.object(bundle, "_git_blob", return_value="0" * 40):
            with self.assertRaises(bundle.DraftBundleError):
                bundle.build_draft_bundle()


if __name__ == "__main__":
    unittest.main()
