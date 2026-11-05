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

    def test_authored_chapter_provenance_machine_contract_and_revision(self):
        raw, receipt = bundle.build_draft_bundle()
        with ZipFile(BytesIO(raw)) as archive:
            machine = json.loads(archive.read("SKILLBOOKS.json"))
            human = archive.read("SKILLBOOKS.md").decode("utf-8")
            manifest = json.loads(archive.read("MANIFEST.json"))
        self.assertEqual(machine["schema"], bundle.CONTENT_SCHEMA)
        self.assertEqual(manifest["content_schema"], bundle.CONTENT_SCHEMA)
        self.assertEqual(machine["blueprint_id"], receipt["blueprint_id"])
        self.assertEqual(machine["blueprint_id"], manifest["blueprint_id"])
        self.assertTrue(receipt["human_skillbook_chapters_included"])
        self.assertTrue(receipt["machine_skill_contracts_included"])
        self.assertFalse(receipt["automatic_semantic_synthesis_claimed"])
        self.assertEqual(len(machine["items"]), 2)
        seen = set()
        for item in machine["items"]:
            with self.subTest(book=item["skillbook_id"]):
                name = item["skillbook_id"]
                source_id, digest, tag, callable_name = bundle.PINNED_BOOKS[name]
                self.assertNotIn(name, seen)
                seen.add(name)
                self.assertEqual(item["source_id"], source_id)
                self.assertEqual(item["source_sha256"], digest)
                self.assertEqual(item["source_tag"], tag)
                self.assertEqual(item["machine_skill_contract"]["callable"],
                                 callable_name)
                self.assertEqual(len(item["chapter_claims"]), 4)
                self.assertEqual(len(item["revision_history"]), 1)
                self.assertFalse(item["revision_history"][0]["published"])
                self.assertFalse(item["export_allowed"])
                self.assertFalse(item["proof_gates"]["human_approved"])
                self.assertFalse(item["proof_gates"]["independent_test_verified"])
                self.assertFalse(item["proof_gates"]["license_redistribution_approved"])
                self.assertIn(item["title"], human)
                self.assertIn(digest, human)
                for chapter in item["chapter_claims"]:
                    self.assertIn(chapter["heading"], human)
                    self.assertIn(chapter["text"], human)
        self.assertEqual(seen, set(bundle.PINNED_BOOKS))
        self.assertFalse(machine["external_semantic_synthesis_verified"])
        self.assertFalse(machine["rights_approved"])
        self.assertFalse(machine["released"])

    def test_modified_authored_chapter_source_refused(self):
        with patch.dict(bundle.PRODUCT_BLOBS, {"skillbook_product_v01.py": "0" * 40}):
            with self.assertRaises(bundle.DraftBundleError):
                bundle.build_draft_bundle()

    def test_modified_authored_json_member_refused_by_consumer(self):
        from zipfile import ZIP_STORED
        with ZipFile(self.path) as archive:
            members = [(name, archive.read(name)) for name in archive.namelist()]
        with ZipFile(self.path, "w", compression=ZIP_STORED) as archive:
            for name, data in members:
                if name == "SKILLBOOKS.json":
                    self.assertIn(b'"export_allowed":false', data)
                    data = data.replace(b'"export_allowed":false',
                                        b'"export_allowed":true', 1)
                archive.writestr(name, data)
        r = self._run(b'{"action":"scandir-synthetic"}')
        self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(r.stdout)["status"],
                         "UCIE_FIRST_PARTY_DRAFT_FAIL_CLOSED")

    def test_windows_autocrlf_checkout_reproduces_same_pinned_archive(self):
        root = Path(bundle.__file__).resolve().parent
        for name, expected_blob in bundle.SOURCE_BLOBS.items():
            with self.subTest(name=name):
                source = (root / name).read_bytes()
                canonical = bundle._canonical_source_bytes(source, expected_blob)
                crlf_checkout = canonical.replace(b"\n", b"\r\n")
                self.assertEqual(
                    bundle._canonical_source_bytes(crlf_checkout, expected_blob),
                    canonical)
                self.assertEqual(bundle._git_blob(canonical), expected_blob)
                self.assertNotIn(b"\r", canonical)

    def test_source_canonicalization_rejects_bare_cr_and_mutation(self):
        root = Path(bundle.__file__).resolve().parent
        name, expected_blob = next(iter(bundle.SOURCE_BLOBS.items()))
        canonical = bundle._canonical_source_bytes(
            (root / name).read_bytes(), expected_blob)
        for raw in (canonical + b"# changed\n",
                    canonical.replace(b"\n", b"\r", 1),
                    b"", b"z" * (bundle.MAX_SOURCE_BYTES + 1)):
            with self.subTest(length=len(raw)):
                with self.assertRaises(bundle.DraftBundleError):
                    bundle._canonical_source_bytes(raw, expected_blob)

    def test_cross_source_original_chapter_in_draft_and_versioned_lineage(self):
        from ucie_miner import skillbook_principle_composer_v01 as composer
        raw, receipt = bundle.build_draft_bundle()
        with ZipFile(BytesIO(raw)) as archive:
            manuscript = json.loads(archive.read("PRINCIPLE.json"))
            human = archive.read("PRINCIPLE.md").decode("utf-8")
            manifest = json.loads(archive.read("MANIFEST.json"))
        canonical = composer.compose_bounded_metadata_principle()
        self.assertEqual(manuscript, canonical)
        self.assertEqual(manifest["principle_schema"], composer.SCHEMA)
        self.assertEqual(manifest["principle_content_sha256"],
                         canonical["content_sha256"])
        self.assertEqual(manifest["composer_git_blob_sha1"], bundle.COMPOSER_BLOB)
        self.assertEqual(receipt["principle_id"], composer.PRINCIPLE_ID)
        self.assertTrue(receipt["curated_original_cross_source_chapter_included"])
        self.assertFalse(receipt["semantic_generation_from_arbitrary_evidence"])
        self.assertEqual(human, composer.render_principle_markdown(canonical))
        self.assertIn("공통 원리", human)
        self.assertIn("반례", human)
        self.assertEqual(len(manuscript["sources"]), 2)
        self.assertEqual(len(manuscript["chapters"]), 5)
        self.assertEqual(len(manuscript["revision_history"]), 1)
        self.assertEqual(manuscript["revision_history"][0]["source_content_sha256"],
                         manuscript["content_sha256"])
        for key in ("export_allowed", "owner_approved", "rights_approved",
                    "independent_qa_verified", "released"):
            self.assertFalse(manuscript[key], key)

    def test_isolated_two_recipe_cross_source_comparison(self):
        result = self._run(b'{"action":"principle-synthetic"}')
        self.assertEqual(result.returncode, 0,
                         result.stderr.decode(errors="replace"))
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["skillbook_id"], bundle.PRINCIPLE_ID)
        self.assertEqual(receipt["result"]["scandir_file_count"], 2)
        self.assertEqual(receipt["result"]["git_entry_count"], 2)
        self.assertEqual(receipt["result"]["git_counts"]["tracked_changed"], 1)
        self.assertEqual(receipt["result"]["git_counts"]["untracked"], 1)
        self.assertTrue(receipt["result"]["synthetic_sources_only"])
        self.assertFalse(receipt["result"]["scandir_names_exported"])
        self.assertFalse(receipt["result"]["git_names_exported"])
        self.assertFalse(receipt["export_approved"])
        for name in ("alpha.txt", "beta.txt", "fake-a.txt", "fake-b.txt"):
            self.assertNotIn(name, result.stdout.decode())

    def test_cross_source_input_forbidden_and_principle_tamper_denied(self):
        for payload in (
            b'{"action":"principle-synthetic","directory":"D:/UCIE"}',
            b'{"action":"principle-synthetic","source_id":"repo:else"}',
            b'{"action":"principle-synthetic","release":true}',
        ):
            with self.subTest(payload=payload):
                r = self._run(payload)
                self.assertEqual(r.returncode, 2)
                self.assertEqual(json.loads(r.stdout)["status"],
                                 "UCIE_FIRST_PARTY_DRAFT_FAIL_CLOSED")
        with ZipFile(self.path) as archive:
            original = [(name, archive.read(name))
                        for name in archive.namelist()]
        with ZipFile(self.path, "w") as archive:
            for name, data in original:
                if name == "PRINCIPLE.json":
                    self.assertIn(b'"export_allowed":false', data)
                    data = data.replace(b'"export_allowed":false',
                                        b'"export_allowed":true', 1)
                archive.writestr(name, data)
        r = self._run(b'{"action":"principle-synthetic"}')
        self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(r.stdout)["status"],
                         "UCIE_FIRST_PARTY_DRAFT_FAIL_CLOSED")

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
