"""UCIE V1 single-path integrated product acceptance, synthetic and offline.

Tests all *implemented* first-party surfaces in one real executable sequence:
two pinned books -> sourced principle -> W04 catalog -> source review journal
-> hash-verified bounded ZIP -> Python -I -B original recipe consumer ->
W09 release gate remains NO_GO. No external source code, user files,
operating miner DB, scheduler, signing, uploading, promotion or publication.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ucie_miner import skillbook_product_v01 as py_book
from ucie_miner import skillbook_git_porcelain_product_v01 as git_book
from ucie_miner import skillbook_principle_composer_v01 as principle
from ucie_miner import skillbook_catalog_union_v01 as library
from ucie_miner import skillbook_pinned_source_review_v01 as journal
from ucie_miner import skillbook_two_recipe_disposable_v01 as package
from ucie_miner import skillbook_w09_release_gate_v01 as release


class UCIEV1IntegratedProductAcceptance(unittest.TestCase):
    def test_full_v1_implemented_product_path_does_not_auto_release(self):
        python = py_book.build_skillbook()
        git = git_book.build_skillbook()
        books = (python, git)
        self.assertEqual(len({book["skillbook_id"] for book in books}), 2)
        self.assertEqual(
            {book["library_entry"]["source_id"] for book in books},
            {"doc:python/cpython", "doc:git/git"},
        )
        self.assertTrue(all(
            book["status"] == "FIRST_PARTY_DRAFT_NOT_APPROVED"
            and book["export_allowed"] is False
            for book in books
        ))

        authored = principle.compose_bounded_metadata_principle()
        self.assertEqual(
            authored["principle_id"],
            "UCIE-PRINCIPLE-PYTHON-GIT-BOUNDED-METADATA-001",
        )
        self.assertEqual(
            {row["skillbook_id"] for row in authored["sources"]},
            {book["skillbook_id"] for book in books},
        )
        self.assertEqual(len(authored["chapters"]), 5)
        self.assertFalse(authored["export_allowed"])

        # A synthetic, deliberately NON-MATCHING raw file produces a
        # review-required event; never claim it verifies the official bytes.
        raw_test_data = b"UCIE synthetic first-party raw source fixture, NOT official RST\n"
        test_proof = journal.verify_pinned_raw_bytes(
            "doc:python/cpython", raw_test_data)
        self.assertFalse(test_proof["pinned_bytes_match"])
        event = journal.propose_source_review(test_proof)
        history, ledger_receipt = journal.extend_review_journal(b"", event)
        self.assertEqual(ledger_receipt["total_events"], 1)
        self.assertFalse(ledger_receipt["approved_or_released"])

        # Actual W04 dossier with validated, in-memory unsigned journal.
        dossier = library.inspect_review_candidate(
            pinned_review_history=history)
        source_row = next(
            item for item in dossier["pinned_source_review_statuses"]
            if item["source_id"] == "doc:python/cpython"
        )
        self.assertEqual(source_row["review_event_id"], event["event_id"])
        self.assertEqual(
            source_row["status"], "PINNED_RAW_SOURCE_MISMATCH_REVIEW_REQUIRED")
        self.assertFalse(dossier["export_allowed"])
        human_view = library.render_review_candidate(dossier)
        self.assertIn("버전 고정 원본 검토 원장", human_view)

        # Produce real reproducible first-party executable draft bytes in
        # memory and verify integrity *before* any original consumer runs.
        raw_zip, build = package.build_draft_bundle()
        self.assertEqual(sha256(raw_zip).hexdigest(), build["archive_sha256"])
        integrity = package.verify_draft_bundle_before_execution(
            raw_zip, build["archive_sha256"])
        self.assertTrue(integrity["pre_execution_integrity_check"])
        self.assertFalse(integrity["external_execution_authorized"])
        self.assertFalse(integrity["export_allowed"])
        self.assertEqual(integrity["verified_member_count"], 8)

        with tempfile.TemporaryDirectory(prefix="UCIE_V1_RC_") as td:
            zip_path = Path(td) / "ucie-first-party-not-released.zip"
            zip_path.write_bytes(raw_zip)
            results = {}
            for label, payload in (
                ("scandir", b'{"action":"scandir-synthetic"}'),
                ("git", json.dumps({
                    "action": "git-summary",
                    "payload_hex": (
                        b" M one.txt\x00?? two.txt\x00".hex()),
                }).encode("ascii")),
                ("principle", b'{"action":"principle-synthetic"}'),
            ):
                proc = subprocess.run(
                    [sys.executable, "-I", "-B", str(zip_path)],
                    input=payload, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, check=False,
                    cwd=td, timeout=20,
                )
                self.assertEqual(
                    proc.returncode, 0,
                    label + ": " + proc.stderr.decode("utf-8", "replace")[:400],
                )
                results[label] = json.loads(proc.stdout)
            self.assertEqual(
                results["scandir"]["result"]["names"],
                ["alpha.txt", "zeta.txt"],
            )
            self.assertEqual(results["git"]["result"]["total_entries"], 2)
            self.assertEqual(
                results["git"]["result"]["counts"]["untracked"], 1)
            self.assertEqual(
                results["principle"]["result"]["git_entry_count"], 2)
            self.assertEqual(
                results["principle"]["result"]["scandir_file_count"], 2)
            self.assertFalse(results["principle"]["export_approved"])

        # W09 explicitly refuses to interpret first-party evidence,
        # the tested ZIP, or local source records as release approval.
        gate = release.preview_release_gate()
        self.assertFalse(gate["export_allowed"])
        self.assertFalse(gate["owner_release_authorized"])
        self.assertFalse(gate["package_signed"])
        self.assertFalse(gate["independent_qa_verified"])

    def test_integrated_flow_cannot_accept_forged_export_or_zip(self):
        import copy
        from ucie_miner import skillbook_editorial_production_v01 as editor
        draft = editor.compose_curated_two_book_pilot()
        modified = copy.deepcopy(draft)
        modified["export_allowed"] = True
        with self.assertRaises(library.FederationError):
            library.inspect_review_candidate(
                modified["draft_sha256"],
                editorial_records=(modified,),
            )
        raw, build = package.build_draft_bundle()
        with self.assertRaises(package.DraftBundleError):
            package.verify_draft_bundle_before_execution(
                raw + b"tamper", build["archive_sha256"])

    def test_release_state_separate_from_functional_implementation(self):
        preview = release.preview_release_gate()
        self.assertTrue(preview["blocked_release_requirements"])
        self.assertFalse(preview["owner_release_authorized"])
        self.assertFalse(preview["license_redistribution_approved"])
        self.assertFalse(preview["independent_qa_verified"])
        self.assertFalse(preview["package_created"])
        self.assertEqual(preview["operating_database_writes"], 0)


if __name__ == "__main__":
    unittest.main()
