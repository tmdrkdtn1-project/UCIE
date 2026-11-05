"""First-party V1 integration using ONLY a disposable local Git repository.

No clone/fetch/remote, owner repository reading, external project access,
operating database access, scheduler mutation, third-party QA or release.
Git command execution is limited to a new TemporaryDirectory fixture.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from ucie_miner import skillbook_git_porcelain_recipe_v01 as git_recipe
from ucie_miner import skillbook_git_porcelain_product_v01 as git_product
from ucie_miner import skillbook_product_v01 as books
from ucie_miner import skillbook_scandir_recipe_v01 as scandir_recipe
from ucie_miner import skillbook_catalog_union_v01 as federation
from ucie_miner import library_browser_skillbook_v01 as browser

EXPECTED = {
    "tracked_changed": 1, "renamed": 1, "copied": 0, "conflicted": 0,
    "untracked": 1, "ignored": 1,
}


class RealGitSkillBookV1Tests(unittest.TestCase):
    def setUp(self):
        self.git = shutil.which("git")
        self.assertIsNotNone(self.git, "GIT_BINARY_MISSING_REAL_QA_NO_GO")
        temp = tempfile.TemporaryDirectory(prefix="UCIE_SB002_GIT_ONLY_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.repo = self.root / "disposable_ucie_git"
        self.repo.mkdir()
        self.hooks = self.root / "no_hooks"
        self.hooks.mkdir()
        (self.root / "empty_template").mkdir()
        env = {k: v for k, v in os.environ.items()
               if not k.upper().startswith("GIT_")}
        env.update({
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TEMPLATE_DIR": str(self.root / "empty_template"),
            "GIT_ALLOW_PROTOCOL": "", "GIT_TERMINAL_PROMPT": "0",
            "HOME": str(self.root), "USERPROFILE": str(self.root),
            "XDG_CONFIG_HOME": str(self.root),
        })
        self.git_env = env
        self._git("init", "-q", "--initial-branch=main")
        (self.repo / ".gitignore").write_bytes(b"ignored-dir/\n")
        (self.repo / "modify.txt").write_bytes(b"before\n")
        (self.repo / "old-name.txt").write_bytes(b"same stable content\n" * 8)
        self._git("add", "--", ".gitignore", "modify.txt", "old-name.txt")
        self._git("-c", "user.name=UCIE-TEST",
                  "-c", "user.email=ucie@example.invalid",
                  "commit", "-qm", "disposable fixture")
        (self.repo / "modify.txt").write_bytes(b"modified\n")
        (self.repo / "old-name.txt").rename(self.repo / "new-name.txt")
        self._git("add", "-u")
        self._git("add", "--", "new-name.txt")
        (self.repo / "untracked.txt").write_bytes(b"test only\n")
        (self.repo / "ignored-dir").mkdir()
        (self.repo / "ignored-dir" / "dummy.txt").write_bytes(b"test only\n")

    def _git(self, *args: str) -> bytes:
        allowed = {"init", "add", "commit", "status", "--version"}
        self.assertTrue(any(arg in allowed for arg in args))
        result = subprocess.run([
            self.git, "-C", str(self.repo),
            "-c", "core.hooksPath=" + str(self.hooks),
            "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false",
            "-c", "gc.auto=0", *args
        ], cwd=self.repo, env=self.git_env, shell=False,
           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15,
           check=False)
        self.assertEqual(result.returncode, 0,
                         "DISPOSABLE_GIT_COMMAND_FAILED_NO_GO")
        self.assertLessEqual(len(result.stdout), 16000)
        return result.stdout

    def _status(self):
        data = self._git("status", "--porcelain=v1", "-z",
                         "--ignored", "--untracked-files=normal")
        self.assertIn(b"R  new-name.txt\x00old-name.txt\x00", data)
        self.assertTrue(data.endswith(b"\x00"))
        self.assertLessEqual(len(data), git_recipe.MAX_BYTES)
        return data

    def test_actual_git_status_z_and_safe_summary(self):
        outcome = git_recipe.summarize_porcelain_v1_z(
            self._status(), max_entries=4)
        self.assertEqual(outcome["total_entries"], 4)
        self.assertEqual(outcome["counts"], EXPECTED)
        self.assertFalse(outcome["filenames_or_content_returned"])
        self.assertFalse(outcome["git_process_executed"])
        for path in ("modify.txt", "new-name.txt", "old-name.txt",
                     "untracked.txt", "ignored-dir"):
            self.assertNotIn(path, json.dumps(outcome))
        print("UCIE_SB002_REAL_GIT_DISPOSABLE="
              + json.dumps({
                  "status": "FIRST_PARTY_REAL_GIT_STATUS_COMPATIBILITY_OBSERVED",
                  "counts": outcome["counts"], "entries": outcome["total_entries"],
                  "recipe_executed_git": False,
                  "git_binary_executed_by_test_only": True,
                  "independent_qa_verified": False,
                  "export_allowed": False,
                  "operating_database_writes": 0,
                  "other_project_access": False,
              }, sort_keys=True))

    def test_real_git_status_budget_and_branch_header_denial(self):
        with self.assertRaises(git_recipe.PorcelainSummaryError):
            git_recipe.summarize_porcelain_v1_z(
                self._status(), max_entries=3)
        branch = self._git("status", "--porcelain=v1",
                           "-z", "--branch")
        with self.assertRaises(git_recipe.PorcelainSummaryError):
            git_recipe.summarize_porcelain_v1_z(branch)

    def test_two_books_catalog_html_contract_and_real_consumption(self):
        search = federation.search_federated(
            self.root,
            filters=federation.parse_filters("shelf=skillbooks"),
            public_reader=lambda *_a, **_k:
                self.fail("W04 operating public DB read not authorized"))
        self.assertEqual(search["public_shelf_status"], "NOT_REQUESTED")
        self.assertEqual(search["public_evidence_candidates"], [])
        self.assertEqual(search["network_requests"], 0)
        self.assertEqual(len(search["skillbooks"]), 2)
        html = federation.render_federated(search)
        expected = {books.SKILLBOOK_ID, git_product.SKILLBOOK_ID}
        self.assertEqual({b["skillbook_id"] for b in search["skillbooks"]},
                         expected)
        sources = set()
        for row in search["skillbooks"]:
            self.assertIn('href="/skillbooks/' + row["skillbook_id"] + '"',
                          html)
            product = books.get_skillbook(row["skillbook_id"])
            detail = browser.render_chapter(product)
            self.assertIn(row["source_document_sha256"], detail)
            self.assertIn("--run-synthetic-demo", detail)
            self.assertFalse(product["export_allowed"])
            self.assertFalse(product["proof_gates"]["independent_test_verified"])
            self.assertFalse(product["proof_gates"]["license_redistribution_approved"])
            self.assertFalse(product["proof_gates"]["security_review_approved"])
            self.assertFalse(product["proof_gates"]["human_approved"])
            self.assertFalse(product["proof_gates"]["published"])
            sources.add((row["source_id"], row["source_document_sha256"],
                         product["machine_skill_contract"]["callable"]))
        self.assertEqual(len(sources), 2)

        outcome = git_recipe.summarize_porcelain_v1_z(
            self._status(), max_entries=4)
        self.assertEqual(outcome["counts"], EXPECTED)
        directory = self.root / "ucie_disposable_scandir"
        directory.mkdir()
        (directory / "alpha.txt").write_bytes(b"fixture")
        (directory / "zeta.txt").write_bytes(b"fixture")
        self.assertEqual(
            scandir_recipe.bounded_regular_file_names(
                directory, max_entries=2),
            ("alpha.txt", "zeta.txt"))

    def test_actual_git_version_is_not_pinned_source_version(self):
        raw = self._git("--version").decode("ascii", errors="replace")
        match = re.search(r"git version ([0-9]+\.[0-9]+(?:\.[0-9]+)?)", raw)
        self.assertIsNotNone(match, "GIT_BINARY_VERSION_UNVERIFIED_NO_GO")
        self.assertEqual(git_product.SOURCE_TAG, "v2.51.0")
        self.assertFalse(git_product.build_skillbook()["source_evidence"][
            "runtime_git_binary_version_verified"])
        print("UCIE_SB002_TEST_BINARY_GIT_VERSION=" + match.group(1))


if __name__ == "__main__":
    unittest.main()
