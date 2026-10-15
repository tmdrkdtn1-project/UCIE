"""Read-only public batch integration using only UCIE-authored synthetic feeds."""
from datetime import datetime, timezone
from contextlib import closing
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import sqlite3
import tempfile
import unittest

from ucie_miner.public_batch import build_public_batch, review_batch_preview
from ucie_miner.public_discovery import SOURCES, DiscoveryError, public_feed_url
from ucie_miner.public_evidence_routes import github_evidence_url

NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
CANDIDATES = {
    "python/cpython": [(159311, "Fix race thread test", "2026-10-14T02:38:51Z")],
    "PowerShell/PowerShell": [(28042, "Fix command regression", "2026-10-09T16:35:49Z")],
    "git/git": [(2700, "Fix git CLI regression", "2026-10-12T09:30:00Z")],
    "modelcontextprotocol/python-sdk": [(3696, "Fix missing API arguments", "2026-10-13T09:20:59Z")],
    "actions/runner-images": [(14517, "Fix runner compatibility break", "2026-08-10T07:55:56Z")],
}
MERGE = "a" * 40


def metadata(url):
    for source in SOURCES:
        if url == public_feed_url(source):
            return [{
                "number": number, "title": title, "merged_at": dt,
                "html_url": f"https://github.com/{source}/pull/{number}",
                "base": {"repo": {"full_name": source}},
                "merge_commit_sha": MERGE,
            } for number, title, dt in CANDIDATES[source]]
    raise AssertionError("unapproved or unexpected metadata URL")


def evidence(url):
    if "files?per_page=30" in url:
        return [
            {"filename": "tests/synthetic.py", "status": "modified",
             "patch": "@@ -1 +1 @@\n-raise ValueError('old')\n+raise ValueError('new argument')\n"}
        ]
    if "/releases?per_page=10" in url:
        return [{"tag_name": "v3.15.0", "draft": False, "prerelease": False,
                 "published_at": "2026-10-13T10:00:00Z"}]
    if "/security-advisories?per_page=10" in url:
        return []
    return "<html><body>os.scandir Resolve-Path git MCP runner</body></html>"


class BatchPipelineTests(unittest.TestCase):
    def test_full_five_source_batch_bounded_and_manual_only(self):
        meta, proof = [], []
        def m(url):
            meta.append(url)
            return metadata(url)
        def e(url):
            proof.append(url)
            return evidence(url)
        batch = build_public_batch(
            metadata_fetch=m, evidence_fetch=e, now=NOW, max_enrich=3)
        self.assertEqual(len(meta), 5)
        self.assertEqual(len(proof), 12)
        self.assertEqual(batch["overall_gets_upper_bound"], 17)
        self.assertEqual(batch["enriched_count"], 3)
        self.assertEqual(batch["public_metadata_candidate_count"], 5)
        self.assertEqual(len({
            x["source"] for x in batch["candidate_skill_queue"]}), 3)
        self.assertEqual(batch["status"], "READ_ONLY_RESEARCH_CANDIDATES_NO_GO")
        self.assertFalse(batch["source_data_and_patch_code_retained"])
        self.assertEqual(batch["operating_database_writes"], 0)
        self.assertEqual(batch["knowledge_rules_auto_promoted"], 0)
        self.assertFalse(batch["production_approved"])
        self.assertEqual(len(batch["candidate_queue_sha256"]), 64)
        review = review_batch_preview(batch)
        self.assertEqual(review["candidate_count"], 3)
        self.assertFalse(review["operational_go"])

    def test_source_optout_prevents_all_http_requests_to_that_source(self):
        called = []
        def meta(url):
            called.append(url)
            return metadata(url)
        def proof(url):
            called.append(url)
            return evidence(url)
        batch = build_public_batch(
            metadata_fetch=meta, evidence_fetch=proof,
            opted_out_sources=("modelcontextprotocol/python-sdk",),
            now=NOW, max_enrich=3)
        self.assertFalse(any("modelcontextprotocol/python-sdk" in u
                             for u in called))
        self.assertIn("modelcontextprotocol/python-sdk",
                      batch["source_optouts_prevented_network"])
        self.assertFalse(any(item["source"] ==
            "modelcontextprotocol/python-sdk"
            for item in batch["candidate_skill_queue"]))

    def test_explicit_pr_optout_and_history_dedupe(self):
        result = build_public_batch(
            metadata_fetch=metadata, evidence_fetch=evidence,
            opted_out_prs=[("python/cpython", 159311)],
            already_reviewed_prs=[("PowerShell/PowerShell", 28042)],
            now=NOW)
        self.assertFalse(any(x["pr_number"] in (159311, 28042)
                             for x in result["candidate_skill_queue"]))
        self.assertEqual(result["explicit_review_history_count"], 1)
        self.assertEqual(result["explicit_pr_optout_count"], 1)

    def test_existing_read_only_miner_db_skips_known_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "runtime").mkdir()
            db_path = root / "runtime" / "public_miner.sqlite3"
            with closing(sqlite3.connect(db_path)) as conn:
                conn.execute("CREATE TABLE candidates(source TEXT, pr_number INTEGER, status TEXT)")
                conn.execute("INSERT INTO candidates VALUES (?,?,?)",
                             ("python/cpython", 159311,
                              "UNVERIFIED_CANDIDATE_ONLY"))
                conn.commit()
            original = db_path.read_bytes()
            result = build_public_batch(
                metadata_fetch=metadata, evidence_fetch=evidence,
                root=root, now=NOW)
            self.assertEqual(result["existing_miner_duplicates_skipped"], 1)
            self.assertFalse(any(x["source"] == "python/cpython"
                                 for x in result["candidate_skill_queue"]))
            self.assertEqual(db_path.read_bytes(), original)

    def test_missing_runtime_never_creates_directory_or_db(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = build_public_batch(
                metadata_fetch=metadata, evidence_fetch=evidence,
                root=root, now=NOW)
            self.assertGreater(batch["enriched_count"], 0)
            self.assertFalse((root / "runtime").exists())

    def test_unpinned_merge_cannot_be_enriched(self):
        invoked = []
        def unpinned(url):
            rows = metadata(url)
            for r in rows:
                r["merge_commit_sha"] = None
            return rows
        def forbidden(url):
            invoked.append(url)
            raise AssertionError("must not call evidence for unpinned PR")
        result = build_public_batch(
            metadata_fetch=unpinned, evidence_fetch=forbidden, now=NOW,
            max_enrich=2)
        self.assertEqual(invoked, [])
        self.assertEqual(result["enriched_count"], 0)
        self.assertGreaterEqual(len(result["unproven_merge_skips"]), 2)
        self.assertLessEqual(len(result["unproven_merge_skips"]), 12)
        self.assertFalse(result["production_approved"])

    def test_404_advisory_is_visible_but_not_production_pass(self):
        def unavailable_advisory(url):
            if "/security-advisories?" in url:
                from ucie_miner.public_evidence_routes import PublicEvidenceError
                raise PublicEvidenceError("fixture unavailable")
            return evidence(url)
        batch = build_public_batch(
            metadata_fetch=metadata, evidence_fetch=unavailable_advisory,
            now=NOW, max_enrich=1)
        self.assertEqual(batch["enriched_count"], 1)
        item = batch["candidate_skill_queue"][0]
        self.assertEqual(item["evidence_status"], "INCOMPLETE_PUBLIC_EVIDENCE")
        self.assertIn("advisory", item["missing_evidence_types"])
        self.assertFalse(batch["production_approved"])

    def test_explicit_doc_skip_is_incomplete_not_silent_pass(self):
        urls = []
        def proof(url):
            urls.append(url)
            return evidence(url)
        batch = build_public_batch(
            metadata_fetch=metadata, evidence_fetch=proof, now=NOW,
            max_enrich=1, include_docs=False)
        self.assertEqual(batch["enrichment_gets_budget"], 3)
        self.assertIn("document", batch["candidate_skill_queue"][0]
                      ["missing_evidence_types"])
        self.assertFalse(any("docs.python.org" in u or
                             "git-scm.com" in u for u in urls))

    def test_feed_failure_fails_closed_and_does_not_enrich(self):
        visited = []
        def broken(url):
            if "PowerShell/PowerShell" in url:
                raise DiscoveryError("public API unavailable")
            return metadata(url)
        def track(url):
            visited.append(url)
            return evidence(url)
        with self.assertRaises(DiscoveryError):
            build_public_batch(metadata_fetch=broken, evidence_fetch=track,
                               now=NOW)
        self.assertEqual(visited, [])

    def test_reject_unapproved_source_before_any_network(self):
        calls = []
        def nofetch(url):
            calls.append(url)
            return []
        with self.assertRaises(DiscoveryError):
            build_public_batch(metadata_fetch=nofetch, evidence_fetch=nofetch,
                               sources=("external/private",), now=NOW)
        self.assertEqual(calls, [])

    def test_reject_all_sources_opted_out_before_network(self):
        calls = []
        def nofetch(url):
            calls.append(url)
            return []
        with self.assertRaises(DiscoveryError):
            build_public_batch(metadata_fetch=nofetch, evidence_fetch=nofetch,
                               opted_out_sources=SOURCES, now=NOW)
        self.assertEqual(calls, [])

    def test_guarded_fixed_upper_bound(self):
        for max_enrich in (0, 4, -1, True, "3"):
            with self.subTest(value=max_enrich), self.assertRaises(DiscoveryError):
                build_public_batch(max_enrich=max_enrich, now=NOW)

    def test_identical_synthetic_feeds_produce_identical_batch(self):
        a = build_public_batch(metadata_fetch=metadata,
                               evidence_fetch=evidence, now=NOW)
        b = build_public_batch(metadata_fetch=metadata,
                               evidence_fetch=evidence, now=NOW)
        self.assertEqual(a, b)

    def test_forged_success_approval_fails_offline_review(self):
        receipt = build_public_batch(metadata_fetch=metadata,
                                     evidence_fetch=evidence, now=NOW)
        for field, value in (("rulepack_signed", True),
                             ("model_weights_updated", True),
                             ("operating_database_writes", 1),
                             ("real_upstream_fix_independently_verified", True)):
            forged = deepcopy(receipt)
            forged[field] = value
            with self.subTest(field=field), self.assertRaises(DiscoveryError):
                review_batch_preview(forged)

    def test_forged_candidate_or_queue_hash_rejected(self):
        receipt = build_public_batch(metadata_fetch=metadata,
                                     evidence_fetch=evidence, now=NOW)
        forged = deepcopy(receipt)
        forged["candidate_skill_queue"][0]["human_approval_received"] = True
        # An unkeyed SHA can be recomputed by an attacker; a structurally
        # consistent forged receipt must not become an approval.
        forged["candidate_queue_sha256"] = hashlib.sha256(json.dumps(
            forged["candidate_skill_queue"], sort_keys=True,
            ensure_ascii=True, allow_nan=False,
            separators=(",", ":")).encode("ascii")).hexdigest()
        with self.assertRaises(DiscoveryError):
            review_batch_preview(forged)
        forged = deepcopy(receipt)
        forged["candidate_queue_sha256"] = "0" * 64
        with self.assertRaises(DiscoveryError):
            review_batch_preview(forged)

    def test_zero_valid_feed_has_no_artificial_leads(self):
        result = build_public_batch(
            metadata_fetch=lambda _: [], evidence_fetch=lambda _: [],
            now=NOW)
        self.assertEqual(result["enriched_count"], 0)
        self.assertEqual(result["candidate_skill_queue"], [])
        self.assertEqual(result["overall_gets_upper_bound"], 13)
        self.assertFalse(result["production_approved"])


if __name__ == "__main__":
    unittest.main()
