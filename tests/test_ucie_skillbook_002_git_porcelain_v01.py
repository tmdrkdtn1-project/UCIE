"""UCIE SkillBook 002: real safe Git porcelain parser + first-party product QA.

All data are literal synthetic NUL-delimited bytes. No git subprocess, no
repository enumeration, no DB access, no approval and no external publishing.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import subprocess
import unittest
from unittest.mock import patch

from ucie_miner import skillbook_git_porcelain_recipe_v01 as recipe
from ucie_miner import skillbook_git_porcelain_product_v01 as book


class GitPorcelainSkillBook002Tests(unittest.TestCase):
    def test_official_git_source_and_draft_entry(self):
        item = book.build_skillbook()
        self.assertEqual(item["skillbook_id"], book.SKILLBOOK_ID)
        self.assertEqual(item["schema"], book.SCHEMA)
        self.assertEqual(item["library_entry"]["source_id"], "doc:git/git")
        self.assertEqual(item["library_entry"]["source_kind"],
                         "OFFICIAL_PUBLIC_DOCUMENT")
        self.assertEqual(item["library_entry"]["entry_status"],
                         "UNVERIFIED_CANDIDATE_ONLY")
        self.assertEqual(item["source_evidence"]["source_tag"], "v2.51.0")
        self.assertEqual(item["source_evidence"]["source_document_sha256"],
                         book.SOURCE_DOC_SHA256)
        self.assertEqual(len(book.SOURCE_DOC_SHA256), 64)
        self.assertFalse(item["source_evidence"]["runtime_git_binary_version_verified"])
        self.assertFalse(item["export_allowed"])
        self.assertFalse(item["proof_gates"]["independent_test_verified"])
        self.assertFalse(item["proof_gates"]["license_redistribution_approved"])
        self.assertFalse(item["proof_gates"]["security_review_approved"])
        self.assertFalse(item["proof_gates"]["human_approved"])
        self.assertFalse(item["proof_gates"]["signed"])
        self.assertFalse(item["proof_gates"]["published"])

    def test_actual_synthetic_consumer_invokes_real_recipe(self):
        result = book.demonstrate_in_memory_consumer()
        self.assertEqual(result["status"], book.DEMO_OBSERVED)
        self.assertEqual(result["demo_entries"], 4)
        self.assertEqual(result["safe_summary_counts"],
                         {"tracked_changed": 1, "renamed": 1, "copied": 0,
                          "conflicted": 1, "untracked": 1, "ignored": 0})
        self.assertTrue(result["budget_3_rejected"])
        self.assertTrue(result["real_ucie_recipe_executed"])
        self.assertFalse(result["git_subprocess_invoked"])
        self.assertFalse(result["real_repository_inspected"])
        self.assertFalse(result["filename_or_private_data_returned"])
        self.assertFalse(result["independent_qa_verified"])
        self.assertFalse(result["export_allowed"])
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertEqual(result["network_requests"], 0)

    def test_status_count_without_revealing_filename(self):
        payload = b" M private-example.txt\x00?? another-example.txt\x00"
        r = recipe.summarize_porcelain_v1_z(payload)
        self.assertEqual(r["total_entries"], 2)
        self.assertEqual(r["counts"]["tracked_changed"], 1)
        self.assertEqual(r["counts"]["untracked"], 1)
        self.assertNotIn("private-example", str(r))
        self.assertNotIn("another-example", str(r))
        self.assertFalse(r["filenames_or_content_returned"])
        self.assertTrue(r["untrusted_path_bytes_discarded"])

    def test_git_z_rename_copy_take_two_paths_but_each_count_one(self):
        r = recipe.summarize_porcelain_v1_z(
            b"R  renamed-destination\x00old-source\x00"
            b"C  copy-destination\x00copy-source\x00", max_entries=2)
        self.assertEqual(r["total_entries"], 2)
        self.assertEqual(r["counts"]["renamed"], 1)
        self.assertEqual(r["counts"]["copied"], 1)
        for hidden in ("renamed-destination", "old-source",
                       "copy-destination", "copy-source"):
            self.assertNotIn(hidden, str(r))

    def test_zero_entries_and_ignored_status_explicit(self):
        empty = recipe.summarize_porcelain_v1_z(b"")
        self.assertEqual(empty["total_entries"], 0)
        self.assertTrue(all(value == 0 for value in empty["counts"].values()))
        status = recipe.summarize_porcelain_v1_z(
            b"!! ignored-dir/\x00?? untracked\x00")
        self.assertEqual(status["counts"]["ignored"], 1)
        self.assertEqual(status["counts"]["untracked"], 1)

    def test_64_entries_inclusive_65_fails_closed(self):
        records = b"".join(
            b" M file_" + str(i).encode("ascii") + b"\x00" for i in range(65))
        first = recipe.summarize_porcelain_v1_z(records[:-len(b" M file_64\x00")])
        self.assertEqual(first["total_entries"], 64)
        with self.assertRaises(recipe.PorcelainSummaryError):
            recipe.summarize_porcelain_v1_z(records)
        with self.assertRaises(recipe.PorcelainSummaryError):
            recipe.summarize_porcelain_v1_z(
                records[:-len(b" M file_64\x00")], max_entries=63)

    def test_missing_terminator_or_rename_source_is_denied(self):
        for data in (
            b" M lost.txt",
            b"R  new.txt\x00",
            b"C  new.txt\x00",
            b" M x.txt\x00?? later.txt",
            b" R x.txt\x00",
        ):
            with self.subTest(data=data):
                with self.assertRaises(recipe.PorcelainSummaryError):
                    recipe.summarize_porcelain_v1_z(data)

    def test_invalid_status_and_non_porcelain_v1_rejected(self):
        for data in (
            b"## main\x00",
            b"XY bad\x00",
            b"   blank\x00",
            b"M changed\x00",
            b"?  path\x00",
            b"\x00",
        ):
            with self.subTest(data=data):
                with self.assertRaises(recipe.PorcelainSummaryError):
                    recipe.summarize_porcelain_v1_z(data)

    def test_ambiguous_paths_and_traversal_blocked(self):
        for path in (
            b"/root", b"../parent", b"sub/../entry", b"sub//entry",
            b"C:\\windows", b"sub\\different", b".", b"..", b"sub/.",
            b"sub/..", b"verylong" * 180
        ):
            with self.subTest(case=path[:20]):
                with self.assertRaises(recipe.PorcelainSummaryError):
                    recipe.summarize_porcelain_v1_z(b"?? " + path + b"\x00")

    def test_untrusted_long_or_nonbytes_input_fails_closed(self):
        for value in (b"x" * 8193, bytearray(b" M x\x00"), " M x\x00", None):
            with self.subTest(input_type=type(value).__name__):
                with self.assertRaises(recipe.PorcelainSummaryError):
                    recipe.summarize_porcelain_v1_z(value)
        for budget in (0, 65, True, 1.2, "4"):
            with self.subTest(budget=budget):
                with self.assertRaises(recipe.PorcelainSummaryError):
                    recipe.summarize_porcelain_v1_z(b"", max_entries=budget)

    def test_unicode_and_newline_name_bytes_not_returned(self):
        r = recipe.summarize_porcelain_v1_z(
            b" M " + "한글\nline".encode("utf-8") + b"\x00")
        self.assertEqual(r["total_entries"], 1)
        self.assertNotIn("한글", str(r))
        self.assertNotIn("line", str(r))

    def test_default_preview_never_calls_recipe(self):
        with patch.object(book, "demonstrate_in_memory_consumer",
                          side_effect=AssertionError("preview called recipe")):
            text = StringIO()
            with redirect_stdout(text):
                code = book.main([])
        self.assertEqual(code, 0)
        result = json.loads(text.getvalue())
        self.assertEqual(result["status"], book.DEMO_PREVIEW)
        self.assertFalse(result["demo_executed"])
        self.assertFalse(result["export_allowed"])

    def test_manual_cli_no_repository_or_git_execution(self):
        with patch.object(subprocess, "run",
                          side_effect=AssertionError("git subprocess forbidden")):
            capture = StringIO()
            with redirect_stdout(capture):
                code = book.main(["--run-synthetic-demo"])
        self.assertEqual(code, 0)
        result = json.loads(capture.getvalue())
        self.assertEqual(result["status"], book.DEMO_OBSERVED)
        self.assertEqual(result["demo_entries"], 4)
        self.assertEqual(result["network_requests"], 0)
        self.assertFalse(result["git_subprocess_invoked"])
        self.assertFalse(result["export_allowed"])

    def test_cli_unknown_arguments_deny_external_paths(self):
        for args in (
            ["--repository", "D:/UCIE"],
            ["--scan", "C:/private"],
            ["--run-synthetic-demo", "--release"],
        ):
            with self.subTest(args=args), self.assertRaises(SystemExit):
                book.main(args)

    def test_forged_approval_cannot_pass_consumer_contract(self):
        invalid = book.build_skillbook()
        invalid["proof_gates"]["independent_test_verified"] = True
        with patch.object(book, "build_skillbook", return_value=invalid), \
             patch.object(book, "summarize_porcelain_v1_z",
                          side_effect=AssertionError("forged approval reached recipe")):
            with self.assertRaises(book.GitSkillBookError):
                book.demonstrate_in_memory_consumer()

    def test_source_registry_contract_is_reused(self):
        item = book.build_skillbook()
        self.assertEqual(item["machine_skill_contract"]["callable"],
                         "ucie_miner.skillbook_git_porcelain_recipe_v01."
                         "summarize_porcelain_v1_z")
        self.assertEqual(item["library_entry"]["evidence_sha256"],
                         book.SOURCE_DOC_SHA256)
        self.assertFalse(item["machine_skill_contract"]["runtime_execution_by_catalog"])
        self.assertFalse(item["machine_skill_contract"]["external_code_execution"])
        self.assertFalse(item["consumer_pilot"]["accepts_repository_or_path_parameter"])
        self.assertFalse(item["consumer_pilot"]["executes_from_browser"])


if __name__ == "__main__":
    unittest.main()
