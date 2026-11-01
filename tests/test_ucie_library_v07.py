"""UCIE V0.6+V0.7 bundled public proof audit: offline safe regression tests."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from hashlib import sha256
import json
import tempfile
import unittest

from test_ucie_library_v02 import fixture
from ucie_miner.library_audit_v07 import (
    SCHEMA, STATUS, INCOMPLETE, CONFLICT, AuditError,
    audit_handoff_receipts, audit_existing_public_library, summarize_audit,
)
from ucie_miner.library_proof_assessment_v06 import (
    SCHEMA as EVIDENCE_SCHEMA, EvidenceShapeError, inspect_public_claim_shape,
)
from ucie_miner.library_explore import explore_linked_public_candidates
from ucie_miner.library_browser_v07 import (
    SCHEMA as UI_SCHEMA, make_handler, render_audit_dashboard,
    render_audit_candidate,
)
from ucie_miner.library_review_v04 import dossier_from_linked_handoff
from ucie_miner.library_review_records_v05 import (
    ClaimError, record_claim, review_claims, _read_all, _location,
)
from ucie_public.policy import PolicyError

NOW = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)


def synthetic_items(handoff):
    result = explore_linked_public_candidates(handoff, limit=20)
    return result["items"]


def claims_for(handoff):
    item = synthetic_items(handoff)[0]
    return {
        "receipt_id": "a" * 64,
        "item_id": item["library_item_id"],
        "source_id": item["source_id"],
        "source_sha256": item["evidence_sha256"],
        "gate": "VERSION_APPLICABILITY",
        "public_evidence_url": item["public_url"],
        "claimed_document_sha256": "b" * 64,
        "version_hint": "UNDETERMINED",
        "status": "CLAIM_RECEIVED_UNVERIFIED",
        "independent_verification": False,
    }


@contextmanager
def fixture_root():
    with tempfile.TemporaryDirectory(prefix="ucie-v07-only-") as d:
        root = Path(d) / "UCIE"
        root.mkdir()

        def exact_root(x):
            path = Path(x)
            if path != root or not path.is_dir() or path.is_symlink():
                raise ClaimError("synthetic root rejected")
            return path

        with patch("ucie_miner.library_review_records_v05._root",
                   side_effect=exact_root), patch(
                       "ucie_miner.library_audit_v07._root",
                       side_effect=exact_root):
            yield root


def store(root, dossier, *, gate="VERSION_APPLICABILITY", digest="b"*64,
          version="UNDETERMINED"):
    with patch("ucie_miner.library_review_records_v05.dossier_existing_public_candidate",
               return_value=dossier):
        return record_claim(
            root, item_id=dossier["item"]["library_item_id"],
            gate=gate, evidence_url=dossier["item"]["public_url"],
            claimed_sha256=digest, version_hint=version, clock=NOW)


@contextmanager
def local_ui(handoff, claims):
    def auditor(root):
        return audit_handoff_receipts(handoff, claims)

    with HTTPServer(("127.0.0.1", 0),
                    make_handler(Path("Z:/UCIE/synthetic"), auditor=auditor)) as server:
        t = Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            yield "http://127.0.0.1:" + str(server.server_port)
        finally:
            server.shutdown()
            t.join(timeout=5)


class IntegratedAuditTests(unittest.TestCase):
    def test_source_linkage_only_no_receipts_and_non_executable_drafts(self):
        h = fixture()
        report = audit_handoff_receipts(h, [])
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["status"], STATUS)
        self.assertEqual(report["source_linked_candidates"], 26)
        self.assertEqual(report["claim_receipts_integrity_checked"], 0)
        self.assertEqual(report["candidate_count_with_claims"], 0)
        self.assertEqual(report["candidate_count_without_claims"], 26)
        self.assertEqual(sum(report["per_source"].values()), 26)
        self.assertEqual(sum(report["per_domain"].values()), 26)
        self.assertEqual(report["approved_candidates"], 0)
        self.assertEqual(report["independently_verified_fixes"], 0)
        self.assertEqual(report["exportable_rules"], 0)
        self.assertFalse(report["auto_promoted"])
        self.assertEqual(report["operating_database_writes"], 0)
        self.assertEqual(report["review_receipt_writes"], 0)
        for row in report["candidates"]:
            self.assertEqual(row["status"], "NOT_VERIFIED")
            self.assertEqual(len(row["gates"]), 6)
            self.assertEqual(row["gates"][0]["status"],
                             "SOURCE_LINKAGE_ONLY_NOT_FIX_VERIFIED")
            self.assertTrue(all(g["status"] == "NOT_VERIFIED"
                                for g in row["gates"][1:]))
            self.assertEqual(row["review_guide"]["type"],
                             "INERT_UCIE_REVIEW_GUIDE_NOT_RULE")
            self.assertFalse(row["review_guide"]["generated_executable_rule"])
            self.assertFalse(row["owner_approved"])
        short = summarize_audit(report, limit=10)
        self.assertEqual(short["review_queue"], [])
        self.assertEqual(len(short["report_sha256"]), 64)
        self.assertEqual(summarize_audit(report)["report_sha256"],
                         short["report_sha256"])

    def test_claim_routing_shape_and_false_approval_denied(self):
        h = fixture()
        claim = claims_for(h)
        assessment = inspect_public_claim_shape(
            claim, source_id=claim["source_id"],
            source_sha256=claim["source_sha256"])
        self.assertEqual(assessment["schema"], EVIDENCE_SCHEMA)
        self.assertIn(assessment["citation_shape"],
                      {"PUBLIC_REPOSITORY_PR_CITATION_ONLY",
                       "PINNED_PUBLIC_COMMIT_CITATION_ONLY"})
        self.assertEqual(assessment["review_classification"],
                         "VERSION_SCOPE_NOT_INDEPENDENTLY_CHECKED")
        self.assertFalse(assessment["claimed_document_sha_recomputed"])
        self.assertFalse(assessment["exact_release_verified"])
        self.assertFalse(assessment["regression_passed"])
        report = audit_handoff_receipts(h, [claim])
        self.assertEqual(report["claim_receipts_integrity_checked"], 1)
        self.assertEqual(report["claims_assigned_to_current_sources"], 1)
        self.assertEqual(report["candidate_count_with_claims"], 1)
        self.assertEqual(report["per_gate_claim_counts"]["VERSION_APPLICABILITY"], 1)
        self.assertEqual(
            report["evidence_review_class_counts"]["VERSION_SCOPE_NOT_INDEPENDENTLY_CHECKED"],
            1)
        summary = summarize_audit(report)
        self.assertEqual(len(summary["review_queue"]), 1)
        self.assertFalse(summary["review_queue"][0]["rule_generated"])
        self.assertEqual(summary["approved_candidates"], 0)
        with self.assertRaises(EvidenceShapeError):
            inspect_public_claim_shape(
                dict(claim, independent_verification=True),
                source_id=claim["source_id"],
                source_sha256=claim["source_sha256"])
        with self.assertRaises(EvidenceShapeError):
            inspect_public_claim_shape(
                claim, source_id=claim["source_id"],
                source_sha256="f" * 64)

    def test_conflicting_hash_and_versions_are_not_verification(self):
        h = fixture()
        first = claims_for(h)
        same_url_different_digest = dict(first,
            receipt_id="c" * 64, claimed_document_sha256="d" * 64)
        second_version = dict(first, receipt_id="e" * 64,
                              claimed_document_sha256="b" * 64,
                              version_hint="3.15")
        third_version = dict(first, receipt_id="f" * 64,
                             claimed_document_sha256="b" * 64,
                             version_hint="3.14")
        out = audit_handoff_receipts(
            h, [first, same_url_different_digest, second_version, third_version])
        self.assertEqual(out["status"], CONFLICT)
        self.assertGreaterEqual(out["conflicting_claim_groups"], 2)
        self.assertEqual(out["conflicted_candidate_count"], 1)
        self.assertEqual(out["approved_candidates"], 0)
        row = next(x for x in out["candidates"]
                   if x["item_id"] == first["item_id"])
        self.assertEqual(row["status"], "RECEIPT_CONFLICT_REVIEW_REQUIRED_NO_GO")
        self.assertEqual(row["claim_count"], 4)
        self.assertFalse(row["independently_verified"])

    def test_orphan_and_sha_drift_are_reported_without_approval(self):
        h = fixture()
        first = claims_for(h)
        orphan = dict(first, receipt_id="c"*64, item_id="f"*64)
        stale = dict(first, receipt_id="d"*64, source_sha256="f"*64)
        out = audit_handoff_receipts(h, [first, orphan, stale])
        self.assertEqual(out["status"], CONFLICT)
        self.assertEqual(out["orphaned_claim_count"], 1)
        self.assertEqual(out["source_sha_conflicts"], 1)
        self.assertEqual(out["claims_assigned_to_current_sources"], 1)
        self.assertEqual(out["approved_candidates"], 0)
        self.assertFalse(out["auto_promoted"])

    def test_missing_source_linkage_and_forged_approval_stop_before_claims(self):
        h = fixture()
        h["status"] = "SOURCE_REVISIONS_PENDING_NO_GO"
        h["source_revisions"] += 1
        h["pending_source_revisions"] = 1
        out = audit_handoff_receipts(h, [claims_for(fixture())])
        self.assertEqual(out["status"], INCOMPLETE)
        self.assertEqual(out["candidates"], [])
        forged = fixture()
        forged["tasks"][0]["approval"] = True
        with self.assertRaises(PolicyError):
            audit_handoff_receipts(forged, [])
        complete = fixture()
        dupe = claims_for(complete)
        with self.assertRaises(AuditError):
            audit_handoff_receipts(complete, [dupe, dupe])
        with self.assertRaises(AuditError):
            audit_handoff_receipts(complete, [{}])

    def test_existing_v05_append_only_receipts_audited_once_no_writes(self):
        h = fixture()
        item = synthetic_items(h)[0]
        dossier = dossier_from_linked_handoff(h, item_id=item["library_item_id"])
        with fixture_root() as root:
            self.assertFalse((root / "runtime").exists())
            with patch("ucie_miner.library_audit_v07.prepare_verification_handoff",
                       return_value=h) as handoff:
                original = audit_existing_public_library(root)
                self.assertEqual(original["claim_receipts_integrity_checked"], 0)
                self.assertEqual(handoff.call_count, 1)
            submitted = store(root, dossier)
            self.assertEqual(submitted["status"], "CLAIM_STORED_UNVERIFIED")
            submitted2 = store(root, dossier, digest="c"*64)
            self.assertEqual(submitted2["status"], "CLAIM_STORED_UNVERIFIED")
            with patch("ucie_miner.library_audit_v07.prepare_verification_handoff",
                       return_value=h) as handoff, patch(
                "ucie_miner.library_audit_v07._read_all",
                wraps=_read_all
            ) as reader:
                report = audit_existing_public_library(root)
                self.assertEqual(handoff.call_count, 1)
                self.assertEqual(reader.call_count, 1)
            self.assertEqual(report["status"], CONFLICT)
            self.assertEqual(report["claim_receipts_integrity_checked"], 2)
            self.assertEqual(report["claims_assigned_to_current_sources"], 2)
            target = (root / "runtime" / "public_review_v05" / "receipts"
                      / (submitted["receipt_id"] + ".json"))
            original_bytes = target.read_bytes()
            saved = json.loads(original_bytes)
            saved["independent_verification"] = True
            target.write_text(json.dumps(saved), encoding="ascii")
            with patch("ucie_miner.library_audit_v07.prepare_verification_handoff",
                       return_value=h):
                with self.assertRaises(ClaimError):
                    audit_existing_public_library(root)
            target.write_bytes(original_bytes)

    def test_local_browser_audit_queue_gate_view_and_security(self):
        h = fixture()
        receipt = claims_for(h)
        with local_ui(h, [receipt]) as base:
            with urlopen(base + "/audit", timeout=5) as response:
                page = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("V0.7", page)
                self.assertIn(UI_SCHEMA, page)
                self.assertNotIn("UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V05", page)
                self.assertEqual(page.count("class=\"audit-nav\""), 1)
                self.assertIn("검증 완료 규칙", page)
                self.assertIn("0</div>", page)
                self.assertIn("VERSION_SCOPE_NOT_INDEPENDENTLY_CHECKED", page)
                self.assertIn('href="/audit/item/' + receipt["item_id"] + '"', page)
            with urlopen(base + "/audit/item/" + receipt["item_id"],
                         timeout=5) as response:
                detail = response.read().decode("utf-8")
                self.assertIn("오류 예방 검토 초안", detail)
                self.assertIn("INERT_UCIE_REVIEW_GUIDE_NOT_RULE", detail)
                self.assertIn("UNDETERMINED", detail)
                self.assertIn("SOURCE_LINKAGE_ONLY_NOT_FIX_VERIFIED", detail)
                self.assertNotIn("OWNER_APPROVED", detail)
            with urlopen(base + "/health", timeout=5) as response:
                health = json.load(response)
                self.assertEqual(health["schema"], UI_SCHEMA)
                self.assertEqual(health["operating_db_writes"], 0)
                self.assertFalse(health["auto_promoted"])
            for path in (
                "/audit?url=https://evil.test",
                "/audit/item/nothex",
                "/audit/item/" + "f"*64,
            ):
                with self.subTest(path=path), self.assertRaises(HTTPError) as err:
                    urlopen(base + path, timeout=5)
                self.assertIn(err.exception.code, (400, 404))
            with self.assertRaises(HTTPError) as err:
                urlopen(Request(base + "/audit", data=b"x", method="POST"),
                        timeout=5)
            self.assertEqual(err.exception.code, 405)
            with self.assertRaises(HTTPError) as err:
                urlopen(Request(base + "/audit", headers={"Host": "evil.test"}),
                        timeout=5)
            self.assertEqual(err.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
