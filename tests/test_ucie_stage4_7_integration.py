"""Synthetic-only UCIE Stage 4-7 integration. No production DB access."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ucie_miner.integration import preview_knowledge_rules
from ucie_miner.knowledge import import_miner_candidates
from ucie_miner.patterns import PatternError
from ucie_miner.review import _read_candidates
from ucie_miner.provenance_review import inspect_public_prs
from ucie_miner.preapproval import preapproval_readiness
from ucie_miner.acceptance_bundle import build_readonly_acceptance_preview
from ucie_miner.static_concurrency import inspect_python_scandir_source
from ucie_miner.static_rule_bridge import preview_static_rule_candidates
from ucie_miner.evidence_binding import bind_candidate_receipts
from ucie_miner.merge_snapshot import compare_merge_snapshot, load_merge_snapshot
from ucie_miner.license_review import inspect_pinned_licenses
from ucie_miner.regression_plans import create_regression_matrix
from ucie_miner.review import load_manifest


class Stage4To7IntegrationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        runtime = self.root / "runtime"
        curated = self.root / "curated_public"
        runtime.mkdir()
        curated.mkdir()
        evid = self.root / "docs" / "evidence"
        evid.mkdir(parents=True)
        pinned = ROOT / "docs" / "evidence" / "public_pr_merge_snapshot_v1.json"
        (evid / pinned.name).write_bytes(pinned.read_bytes())
        manifest_text = (ROOT / "curated_public" /
                         "pr_review_evidence_v1.json").read_text("utf-8")
        (curated / "pr_review_evidence_v1.json").write_text(
            manifest_text, encoding="utf-8")
        self.entries = json.loads(manifest_text)["entries"]
        self.miner = runtime / "public_miner.sqlite3"
        self.knowledge = runtime / "knowledge.sqlite3"
        with closing(sqlite3.connect(self.miner)) as db, db:
            db.execute("""CREATE TABLE candidates (
                source TEXT NOT NULL, pr_number INTEGER NOT NULL,
                public_url TEXT NOT NULL, merged_at TEXT NOT NULL,
                evidence_sha256 TEXT NOT NULL, status TEXT NOT NULL)""")
            for row in self.entries:
                self._insert(db, row["source"], row["pr_number"],
                             row["merged_at"])
        import_miner_candidates(self.root)

    @staticmethod
    def _insert(db, source, number, merged):
        db.execute("INSERT INTO candidates VALUES (?,?,?,?,?,?)",
                   (source, number, f"https://github.com/{source}/pull/{number}",
                    merged, hashlib.sha256(str(number).encode()).hexdigest(),
                    "UNVERIFIED_CANDIDATE_ONLY"))

    def test_nine_prs_map_to_eight_unverified_ruleplans(self):
        prior_miner = self.miner.read_bytes()
        prior_knowledge = self.knowledge.read_bytes()
        preview = preview_knowledge_rules(self.root)
        self.assertEqual(preview["miner_count"], 9)
        self.assertEqual(preview["knowledge_count"], 9)
        self.assertEqual(preview["pattern_preview"]["family_count"], 8)
        self.assertEqual(len(preview["rulepack_preview"]["proposals"]), 8)
        self.assertEqual(preview["database_writes"], 0)
        self.assertFalse(preview["production_approved"])
        self.assertFalse(preview["approval_gate"]["deploy_allowed"])
        self.assertTrue(all(x["executable_command"] is None
                            for x in preview["rulepack_preview"]["proposals"]))
        self.assertEqual(self.miner.read_bytes(), prior_miner)
        self.assertEqual(self.knowledge.read_bytes(), prior_knowledge)

    def test_unmapped_candidate_remains_unverified(self):
        with closing(sqlite3.connect(self.miner)) as db, db:
            self._insert(db, "python/cpython", 999998,
                         "2026-10-01T00:00:00Z")
        import_miner_candidates(self.root)
        result = preview_knowledge_rules(self.root)
        self.assertEqual(result["unmapped_count"], 1)
        self.assertEqual(result["pattern_preview"]["family_count"], 8)

    def test_stale_knowledge_digest_fails_closed(self):
        with closing(sqlite3.connect(self.knowledge)) as db, db:
            db.execute("UPDATE evidence SET evidence_sha256=? WHERE pr_number=153462",
                       ("f" * 64,))
        with self.assertRaises(PatternError):
            preview_knowledge_rules(self.root)

    def test_missing_import_fails_closed(self):
        self.knowledge.unlink()
        with self.assertRaises(PatternError):
            preview_knowledge_rules(self.root)

    def test_quarantined_backport_excluded(self):
        with closing(sqlite3.connect(self.knowledge)) as db, db:
            db.execute("""UPDATE evidence SET disposition='QUARANTINED'
                           WHERE source='python/cpython' AND pr_number=159365""")
        result = preview_knowledge_rules(self.root)
        self.assertEqual(result["quarantined_or_retracted_count"], 1)
        self.assertEqual(result["pattern_preview"]["family_count"], 8)
        self.assertFalse(result["production_approved"])

    def test_pinned_merge_snapshot_nine_prs_is_not_a_version_pass(self):
        rows = _read_candidates(self.root)
        receipt = inspect_public_prs(rows)
        snap = compare_merge_snapshot(self.root, rows, receipt)
        self.assertEqual(snap["local_pinned_pr_count"], 9)
        self.assertEqual(snap["extra_unmapped_local_pr_count"], 0)
        self.assertEqual(len(snap["snapshot_sha256"]), 64)
        self.assertFalse(snap["version_inclusion_verified"])
        self.assertTrue(all(x["fixed_release_version"] == "UNDETERMINED"
                            for x in snap["observations"]))

    def test_pinned_merge_snapshot_rejects_changed_remote_sha(self):
        rows = _read_candidates(self.root)
        receipt = inspect_public_prs(rows)
        case = receipt["items"][0]
        case["source_check"] = "SYNTHETIC_METADATA_MATCHED"
        case["observed_merge_commit_sha"] = "0" * 40
        with self.assertRaises(PatternError):
            compare_merge_snapshot(self.root, rows, receipt)

    def test_pinned_merge_snapshot_rejects_changed_original_file(self):
        path = self.root / "docs" / "evidence" / "public_pr_merge_snapshot_v1.json"
        file = json.loads(path.read_text("utf-8"))
        file["entries"][0]["merged_at"] = "2025-01-01T00:00:00Z"
        path.write_text(json.dumps(file), encoding="utf-8")
        with self.assertRaises(PatternError):
            compare_merge_snapshot(self.root, _read_candidates(self.root),
                                   inspect_public_prs(_read_candidates(self.root)))

    def test_pinned_merge_snapshot_unmapped_rows_remain_unverified(self):
        with closing(sqlite3.connect(self.miner)) as db, db:
            self._insert(db, "python/cpython", 999998, "2026-10-01T00:00:00Z")
        rows = _read_candidates(self.root)
        out = compare_merge_snapshot(self.root, rows, inspect_public_prs(rows))
        self.assertEqual(out["local_pinned_pr_count"], 9)
        self.assertEqual(out["extra_unmapped_local_pr_count"], 1)

    def binding_inputs(self):
        chain = preview_knowledge_rules(self.root)
        rows = _read_candidates(self.root)
        manifest = load_manifest(self.root)
        provenance = inspect_public_prs(rows)
        licenses = inspect_pinned_licenses(self.root)
        regression = create_regression_matrix(chain["rulepack_preview"])
        return rows, manifest, chain, provenance, licenses, regression

    def test_binding_cross_checks_nine_sources_eight_families(self):
        receipt = bind_candidate_receipts(*self.binding_inputs())
        self.assertEqual(receipt["source_count"], 9)
        self.assertEqual(receipt["mapped_pr_count"], 9)
        self.assertEqual(receipt["family_count"], 8)
        self.assertEqual(len(receipt["receipt_sha256"]), 64)
        self.assertFalse(receipt["receipt_cryptographically_signed"])
        self.assertFalse(receipt["deploy_allowed"])

    def test_binding_tampered_miner_hash_denied(self):
        args = self.binding_inputs()
        args[0][0]["evidence_sha256"] = "f" * 64
        with self.assertRaises(PatternError):
            bind_candidate_receipts(*args)

    def test_binding_tampered_provenance_hash_denied(self):
        args = self.binding_inputs()
        args[3]["items"][0]["comparison_sha256"] = "0" * 64
        with self.assertRaises(PatternError):
            bind_candidate_receipts(*args)

    def test_binding_missing_license_marker_denied(self):
        args = self.binding_inputs()
        args[4]["items"].pop()
        with self.assertRaises(PatternError):
            bind_candidate_receipts(*args)

    def test_binding_forged_license_approval_denied(self):
        args = self.binding_inputs()
        args[4]["items"][0]["legal_approval"] = True
        with self.assertRaises(PatternError):
            bind_candidate_receipts(*args)

    def test_binding_reordered_regression_plan_denied(self):
        args = self.binding_inputs()
        args[5]["cases"][0]["actual_test_result"] = "PASS"
        with self.assertRaises(PatternError):
            bind_candidate_receipts(*args)

    def test_binding_stale_family_fingerprint_denied(self):
        args = self.binding_inputs()
        args[2]["pattern_preview"]["families"][0]["fingerprint_sha256"] = "0" * 64
        with self.assertRaises(PatternError):
            bind_candidate_receipts(*args)

    def external_claim(self):
        chain = preview_knowledge_rules(self.root)
        plan = create_regression_matrix(chain["rulepack_preview"])
        case = plan["cases"][0]
        pinned = load_merge_snapshot(self.root)
        source = case["source"]
        number = int(case["case_id"].split("#", 1)[1].split(":", 1)[0])
        commit = next(row["merge_commit_sha"] for row in pinned["entries"]
                      if row["source"] == source and row["pr_number"] == number)
        return {
            "schema": "UCIE_EXTERNAL_REGRESSION_CLAIM_V1",
            "case_id": case["case_id"], "source": source,
            "rule_code": case["rule_code"],
            "evidence_fingerprint": case["evidence_fingerprint"],
            "merge_commit_sha": commit,
            "runtime_product": "CPython" if source == "python/cpython" else "PowerShell",
            "runtime_version": "3.15.0" if source == "python/cpython" else "7.6.0",
            "platform": "Windows",
            "fixture_sha256": hashlib.sha256(b"synthetic").hexdigest(),
            "pre_fix": {"revision_sha": "b" * 40,
                        "result": "FAILURE_OBSERVED_CLAIM",
                        "observation_sha256": hashlib.sha256(b"before").hexdigest()},
            "post_fix": {"revision_sha": commit,
                         "result": "SUCCESS_OBSERVED_CLAIM",
                         "observation_sha256": hashlib.sha256(b"after").hexdigest()},
            "recorded_utc": "2026-10-14T00:00:00Z",
            "independent_attestation": None,
        }

    def test_external_regression_claim_is_never_an_approval(self):
        result = build_readonly_acceptance_preview(
            self.root, is_windows=True, python_version=(3, 15),
            external_regression_claims=[self.external_claim()])
        self.assertEqual(result["external_regression_claims"], 1)
        self.assertEqual(result["external_regression_claims_missing"], 7)
        self.assertFalse(result["external_regression_claims_are_attested"])
        self.assertEqual(result["status"], "NO_GO")
        self.assertFalse(result["independent_regression_signoff"])
        self.assertFalse(result["production_approved"])

    def test_invalid_external_revision_fails_closed(self):
        claim = self.external_claim()
        claim["post_fix"]["revision_sha"] = "c" * 40
        with self.assertRaises(PatternError):
            build_readonly_acceptance_preview(
                self.root, is_windows=True, python_version=(3, 15),
                external_regression_claims=[claim])

    def test_stage8_optional_static_docket_is_explicitly_no_go(self):
        scan = inspect_python_scandir_source(
            "import os\n"
            "def run(path, executor, worker):\n"
            "    raw = os.scandir(path)\n"
            "    executor.submit(worker, raw)\n")
        static_preview = preview_static_rule_candidates(self.root, scan)
        bundle = build_readonly_acceptance_preview(
            self.root, is_windows=True, python_version=(3, 15),
            static_preview=static_preview)
        self.assertEqual(bundle["status"], "NO_GO")
        self.assertEqual(bundle["static_review_candidate_count"], 1)
        self.assertEqual(len(bundle["static_review_docket_sha256"]), 64)
        self.assertFalse(bundle["static_review_approved"])
        self.assertFalse(bundle["rulepack_signed"])
        self.assertFalse(bundle["production_approved"])
        self.assertEqual(bundle["persistent_writes"], 0)

    def test_stage8_bundle_includes_unverified_license_and_regression(self):
        result = build_readonly_acceptance_preview(
            self.root, is_windows=True, python_version=(3, 15))
        self.assertEqual(result["status"], "NO_GO")
        self.assertEqual(result["candidate_binding_status"],
                         "STRUCTURALLY_CONSISTENT_CANDIDATES")
        self.assertEqual(len(result["candidate_binding_sha256"]), 64)
        self.assertFalse(result["candidate_binding_is_signature"])
        self.assertEqual(len(result["pinned_merge_snapshot_sha256"]), 64)
        self.assertEqual(result["pinned_merge_pr_count"], 9)
        self.assertFalse(result["release_version_inclusion_verified"])
        self.assertEqual(result["miner_candidate_count"], 9)
        self.assertEqual(result["pattern_families"], 8)
        self.assertEqual(result["synthetic_regression_plans"], 8)
        self.assertEqual(result["external_regression_claims"], 0)
        self.assertEqual(result["external_regression_claims_missing"], 8)
        self.assertFalse(result["external_regression_claims_are_attested"])
        self.assertGreaterEqual(result["license_document_count"], 2)
        self.assertEqual(result["regression_execution_state"], "NOT_EXECUTED")
        self.assertEqual(result["public_pr_metadata_state"], "NOT_CHECKED")
        self.assertFalse(result["operational_host_attested"])
        self.assertFalse(result["independent_license_approval"])
        self.assertFalse(result["rulepack_signed"])
        self.assertFalse(result["scheduler_registered"])
        self.assertEqual(result["persistent_writes"], 0)
        self.assertFalse(result["production_approved"])

    def test_full_candidate_chain_never_authorizes_operation(self):
        chain = preview_knowledge_rules(self.root)
        source_rows = _read_candidates(self.root)
        receipt = inspect_public_prs(source_rows)
        verdict = preapproval_readiness(chain, receipt)
        self.assertEqual(receipt["count"], 9)
        self.assertEqual(chain["pattern_preview"]["family_count"], 8)
        self.assertEqual(verdict["status"], "NO_GO")
        self.assertEqual(verdict["candidate_count"], 9)
        self.assertIn("PUBLIC_METADATA_RECHECK_REQUIRED", verdict["pending"])
        self.assertFalse(verdict["rulepack_signed"])
        self.assertFalse(verdict["scheduler_registered"])
        self.assertFalse(verdict["package_deployed"])

    def test_missing_canonical_fails_closed(self):
        with closing(sqlite3.connect(self.knowledge)) as db, db:
            db.execute("""UPDATE evidence SET disposition='RETRACTED'
                           WHERE source='python/cpython' AND pr_number=153462""")
        with self.assertRaises(PatternError):
            preview_knowledge_rules(self.root)


if __name__ == "__main__":
    unittest.main()
