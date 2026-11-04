"""UCIE SkillBook 001: genuine first-party recipe, source-link and catalog tests.

Only test-generated TemporaryDirectory contents are enumerated. No external
source code, private project data, arbitrary command or HTTP API is executed.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from ucie_miner import skillbook_product_v01 as p
from ucie_miner import skillbook_scandir_recipe_v01 as recipe


class UCIESkillBookV01Tests(unittest.TestCase):
    def test_approved_source_registry_and_unapproved_candidate(self):
        book = p.build_skillbook()
        entry = book["library_entry"]
        self.assertEqual(book["schema"], p.SCHEMA)
        self.assertEqual(entry["source_id"], "doc:python/cpython")
        self.assertEqual(entry["kind"], "REUSABLE_SKILL")
        self.assertEqual(entry["public_url"], "https://docs.python.org/3/library/os.html")
        self.assertEqual(entry["evidence_sha256"], p.SOURCE_DOCUMENT_SHA256)
        self.assertEqual(entry["entry_status"], "UNVERIFIED_CANDIDATE_ONLY")
        self.assertFalse(entry["export_allowed"])
        self.assertFalse(entry["human_approved"])
        self.assertFalse(book["export_allowed"])
        self.assertFalse(book["proof_gates"]["independent_test_verified"])
        self.assertFalse(book["proof_gates"]["license_redistribution_approved"])
        self.assertFalse(book["proof_gates"]["published"])
        self.assertFalse(book["model_training_performed"])
        self.assertEqual(book["network_requests"], 0)
        self.assertEqual(book["operating_database_writes"], 0)

    def test_exact_upstream_revision_without_false_certification(self):
        src = p.build_skillbook()["source_evidence"]
        self.assertEqual(src["source_file"], "Doc/library/os.rst")
        self.assertEqual(src["source_tag"], "v3.15.0")
        self.assertEqual(src["source_commit_sha1"],
                         "d220409a13b77de7a6c30abe16ea90db01528edc")
        self.assertEqual(src["source_document_git_blob_sha1"],
                         "74419ee7f3588f1baec83c85b05716e6388719e3")
        self.assertEqual(src["source_document_sha256"],
                         "9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a")
        self.assertTrue(src["claims_only_official_api_contract_not_independent_runtime_verification"])

    def test_separated_official_ucie_and_unknown_claims(self):
        chapters = p.build_skillbook()["ucie_authored_chapters"]
        self.assertEqual([r["claim_type"] for r in chapters], [
            "OFFICIAL_PYTHON_DOCUMENTED", "UCIE_AUTHORED_RECIPE",
            "UCIE_AUTHORED_NEGATIVE_CASES", "LIMITATIONS_NOT_VERIFIED",
        ])
        self.assertTrue(all(r["heading"] and r["text"] for r in chapters))
        self.assertFalse(p.build_skillbook()["machine_skill_contract"]["runtime_execution_by_catalog"])
        self.assertIn("DRAFT", p.build_skillbook()["machine_skill_contract"]["portable_package_state"])

    def test_source_link_forged_approval_rejected(self):
        with mock.patch.object(p, "build_library_entry", return_value={
            "source_id": "doc:python/cpython",
            "evidence_sha256": p.SOURCE_DOCUMENT_SHA256,
            "entry_status": "UNVERIFIED_CANDIDATE_ONLY",
            "approval_status": "OWNER_APPROVED",
            "export_allowed": True,
        }):
            with self.assertRaises(p.SkillBookProductError):
                p.build_skillbook()

    def test_search_by_task_language_version_and_kind(self):
        for query in ("", "Python", "scandir", "디렉터리", "resource", "3.15",
                      "Python scandir"):
            with self.subTest(query=query):
                result = p.search_skillbooks(query=query, language="Python",
                                             kind="REUSABLE_SKILL")
                self.assertEqual(result["total"], 1)
                self.assertFalse(result["items"][0]["export_allowed"])
                self.assertEqual(result["approved_reusable_packages"], 0)
        self.assertEqual(p.search_skillbooks(query="rust")["total"], 0)
        self.assertEqual(p.search_skillbooks(query="Python missing")["total"], 0)

    def test_invalid_or_unapproved_search_denied(self):
        for kwargs in (
            {"query": "<script>alert(1)</script>"},
            {"query": "x" * 81},
            {"query": 3},
            {"language": "Rust"},
            {"kind": "UCIE_EXPERIENCE"},
            {"kind": "PUBLISHED"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(p.SkillBookProductError):
                p.search_skillbooks(**kwargs)
        with self.assertRaises(p.SkillBookProductError):
            p.get_skillbook("../../private")
        with self.assertRaises(p.SkillBookProductError):
            p.get_skillbook("UCIE-SKILLBOOK-PY-SCANDIR-002")

    def test_first_party_owner_scoped_synthetic_files(self):
        with tempfile.TemporaryDirectory(prefix="UCIE-OWNED-SKILLBOOK-TEST-") as tmp:
            path = Path(tmp).resolve()
            (path / "z file.txt").write_text("synthetic", encoding="utf-8")
            (path / "a.py").write_text("synthetic", encoding="utf-8")
            (path / "child").mkdir()
            output = recipe.bounded_regular_file_names(path)
            self.assertEqual(output, ("a.py", "z file.txt"))
            self.assertNotIn("child", output)
            self.assertEqual(tuple(sorted(output)), output)
            print("UCIE_SKILLBOOK_FIRST_PARTY_POSITIVE="
                  '{"file_count":2,"sorted":true,"synthetic_only":true}')

    def test_symlink_entries_not_followed(self):
        with tempfile.TemporaryDirectory(prefix="UCIE-OWNED-LINKS-") as tmp:
            path = Path(tmp).resolve()
            (path / "regular").write_text("abc", encoding="utf-8")
            (path / "nested").mkdir()
            try:
                (path / "linked_regular").symlink_to(path / "regular")
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation not permitted by runner")
            self.assertEqual(recipe.bounded_regular_file_names(path), ("regular",))
            with self.assertRaises(recipe.BoundedScandirError):
                recipe.bounded_regular_file_names(path / "linked_regular")

    def test_invalid_paths_and_limits_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="UCIE-OWNED-SCAN-") as tmp:
            path = Path(tmp).resolve()
            (path / "one.txt").write_text("1", encoding="utf-8")
            fixtures = [
                ("relative", 10), (path / "missing", 10),
                (path, 0), (path, 129), (path, True), (path, 1.5),
                (None, 1), (path / "one.txt", 1),
            ]
            for target, budget in fixtures:
                with self.subTest(target=str(target), budget=budget), self.assertRaises(
                        recipe.BoundedScandirError):
                    recipe.bounded_regular_file_names(target, max_entries=budget)

    def test_bounded_entry_total_not_just_regular_files(self):
        with tempfile.TemporaryDirectory(prefix="UCIE-OWNED-LIMIT-") as tmp:
            path = Path(tmp).resolve()
            (path / "folder").mkdir()
            (path / "file").write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(recipe.BoundedScandirError, "budget"):
                recipe.bounded_regular_file_names(path, max_entries=1)
            self.assertEqual(recipe.bounded_regular_file_names(path, max_entries=2),
                             ("file",))

    def test_iterator_closed_after_budget_error(self):
        with tempfile.TemporaryDirectory(prefix="UCIE-OWNED-CLOSE-") as tmp:
            path = Path(tmp).resolve()
            class FakeEntry:
                def is_symlink(self): return False
                def is_file(self, *, follow_symlinks): return True
                name = "ok"
            class Iterator:
                closed = False
                def __enter__(self): return self
                def __exit__(self, *args): self.closed = True
                def __iter__(self): return iter((FakeEntry(), FakeEntry()))
            fake = Iterator()
            with mock.patch.object(recipe.os, "scandir", return_value=fake):
                with self.assertRaises(recipe.BoundedScandirError):
                    recipe.bounded_regular_file_names(path, max_entries=1)
            self.assertTrue(fake.closed)
            print("UCIE_SKILLBOOK_FIRST_PARTY_NEGATIVE="
                  '{"entry_limit_blocks":true,"iterator_closed":true}')

    def test_iterator_closed_after_os_error(self):
        with tempfile.TemporaryDirectory(prefix="UCIE-OWNED-ERROR-") as tmp:
            path = Path(tmp).resolve()
            class FakeEntry:
                def is_symlink(self): return False
                def is_file(self, *, follow_symlinks): raise OSError("synthetic failure")
            class Iterator:
                closed = False
                def __enter__(self): return self
                def __exit__(self, *args): self.closed = True
                def __iter__(self): return iter((FakeEntry(),))
            fake = Iterator()
            with mock.patch.object(recipe.os, "scandir", return_value=fake):
                with self.assertRaises(recipe.BoundedScandirError):
                    recipe.bounded_regular_file_names(path)
            self.assertTrue(fake.closed)

    def test_no_private_project_or_network_scan(self):
        import inspect
        code = inspect.getsource(recipe)
        self.assertNotIn("requests", code)
        self.assertNotIn("urllib", code)
        self.assertNotIn("subprocess", code)
        self.assertNotIn("rmtree(", code)
        self.assertNotIn("os.walk(", code)
        self.assertNotIn("D:\\OFFICE_AGENT", code)
        self.assertNotIn("D:\\MYGAME", code)
        self.assertIn("with os.scandir(directory)", code)


if __name__ == "__main__":
    unittest.main()
