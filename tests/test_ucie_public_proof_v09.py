"""UCIE V0.8-V0.9 end-to-end source-anchored, explicitly opted-in probes.

All network calls are synthetic. No real external requests, release promotion,
source code execution or operating database writes during CI.
"""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import tempfile
import unittest

from test_ucie_library_v02 import fixture
from ucie_miner.library_explore import (
    explore_linked_public_candidates, _candidate_rows,
)
from ucie_miner.library_audit_v07 import audit_handoff_receipts, CONFLICT
from ucie_miner.library_public_probe_v08 import (
    ProbeError, DOC_SIZE, _public_get, _identity_preflight,
    inspect_public_source_revision, inspect_claimed_official_document,
)
from ucie_miner.library_public_proof_v09 import (
    SCHEMA, BatchError, perform_public_probe_batch,
)
from ucie_miner.library_browser_v09 import (
    SCHEMA as UI_SCHEMA, make_handler,
)


def rows(h):
    return explore_linked_public_candidates(h, limit=20)["items"]


def checked_json(url):
    repo = url.split("/repos/", 1)[1].split("/pulls/", 1)[0]
    if "/pulls/" in url:
        number = int(url.rsplit("/", 1)[-1])
        row = next(x for x in rows(fixture()) if
                   x["source_id"] == "repo:" + repo
                   and x["public_url"].endswith("/pull/" + str(number)))
        return {
            "number": number, "state": "closed",
            "merged_at": "2026-10-01T00:00:00Z",
            "merge_commit_sha": row["revision_hint"],
            "base": {"repo": {"full_name": repo}},
            "body": "UNTRUSTED_PR_INSTRUCTION_DO_NOT_EXECUTE",
        }
    return {"sha": url.rsplit("/", 1)[-1]}


def public_doc_claim(row, *, digest=None):
    return {
        "receipt_id": "e" * 64,
        "item_id": row["library_item_id"],
        "source_id": row["source_id"],
        "source_sha256": row["evidence_sha256"],
        "gate": "LICENSE",
        "public_evidence_url": "https://docs.python.org/3/library/index.html",
        "claimed_document_sha256": digest or sha256(b"public docs").hexdigest(),
        "version_hint": "UNDETERMINED",
        "status": "CLAIM_RECEIVED_UNVERIFIED",
        "independent_verification": False,
    }


@contextmanager
def synthetic_root():
    with tempfile.TemporaryDirectory(prefix="ucie-v09-public-") as td:
        root = Path(td) / "UCIE"
        root.mkdir()
        def valid(path):
            p = Path(path)
            if p != root or not p.is_dir() or p.is_symlink():
                raise BatchError("synthetic dedicated root required")
            return p
        with patch("ucie_miner.library_public_proof_v09._root",
                   side_effect=valid):
            yield root


@contextmanager
def browser(handoff, prober):
    def auditor(root):
        return audit_handoff_receipts(handoff, [])
    with HTTPServer(("127.0.0.1", 0), make_handler(
            Path("Z:/UCIE/synthetic"), auditor=auditor,
            public_prober=prober)) as server:
        t = Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            yield "http://127.0.0.1:" + str(server.server_port)
        finally:
            server.shutdown()
            t.join(timeout=4)


class PublicProbeTests(unittest.TestCase):
    def test_real_public_pr_api_identity_but_never_fix_verified(self):
        h = fixture()
        row = rows(h)[0]
        called = []
        def fake(url):
            called.append(url)
            return checked_json(url)
        out = inspect_public_source_revision(row, fetch_json=fake)
        self.assertEqual(len(called), 1)
        self.assertTrue(called[0].startswith("https://api.github.com/repos/"))
        self.assertTrue(out["identity_matched"])
        self.assertEqual(out["status"],
                         "PUBLIC_MERGE_IDENTITY_MATCHED_NOT_FIX_VERIFIED")
        self.assertEqual(out["gates"]["INDEPENDENT_REGRESSION"], "NOT_VERIFIED")
        self.assertFalse(out["fix_verified"])
        self.assertFalse(out["auto_promoted"])
        self.assertNotIn("UNTRUSTED_PR_INSTRUCTION", json.dumps(out))
        changed = inspect_public_source_revision(
            row, fetch_json=lambda url: dict(
                checked_json(url), merge_commit_sha="f"*40))
        self.assertEqual(changed["status"], "PUBLIC_REVISION_MISMATCH_NO_GO")
        self.assertFalse(changed["identity_matched"])
        failed = inspect_public_source_revision(
            row, fetch_json=lambda url: (_ for _ in ()).throw(
                ProbeError("upstream fails")))
        self.assertEqual(failed["status"], "PUBLIC_METADATA_UNAVAILABLE_NO_GO")
        self.assertFalse(failed["metadata_observed"])

    def test_public_endpoint_strict_allowlist_and_no_out_of_scope_open(self):
        h = fixture()
        row = rows(h)[0]
        for bad in (
            dict(row, source_id="repo:nonapproved/project"),
            dict(row, public_url="https://evil.test/private"),
            dict(row, revision_hint="g"*40),
            dict(row, human_approved=True),
            dict(row, public_url="https://github.com/python/cpython/pull/3"
                 "?redirect=https://evil.test"),
        ):
            with self.subTest(bad=bad), self.assertRaises(ProbeError):
                _identity_preflight(bad)
        with self.assertRaises(ProbeError):
            _public_get("https://api.github.com/repos/private/repo/pulls/2",
                        max_bytes=1000, json_only=True)
        with self.assertRaises(ProbeError):
            _public_get("https://127.0.0.1/private",
                        max_bytes=1000, json_only=False)
        with self.assertRaises(ProbeError):
            _public_get("https://docs.python.org.evil.test/3/library/",
                        max_bytes=1000, json_only=False)
        with self.assertRaises(ProbeError):
            _public_get("https://docs.python.org/3/../private",
                        max_bytes=1000, json_only=False)
        with self.assertRaises(ProbeError):
            _public_get("https://docs.python.org/3/library/?url=x",
                        max_bytes=1000, json_only=False)

    def test_independent_http_response_digest_not_license_approval(self):
        row = rows(fixture())[0]
        claim = public_doc_claim(row)
        observed = inspect_claimed_official_document(
            claim, row, fetch_bytes=lambda url: b"public docs")
        self.assertTrue(observed["claimed_sha_matched"])
        self.assertTrue(observed["public_content_checked"])
        self.assertEqual(observed["status"],
                         "OFFICIAL_RESPONSE_BYTES_SHA_MATCH_NOT_TRUST_SIGNOFF")
        self.assertFalse(observed["fix_verified"])
        self.assertFalse(observed["license_signoff"])
        self.assertFalse(observed["released_version_verified"])
        self.assertFalse(observed["external_content_stored"])
        mismatch = inspect_claimed_official_document(
            claim, row, fetch_bytes=lambda url: b"other doc")
        self.assertFalse(mismatch["claimed_sha_matched"])
        self.assertEqual(mismatch["status"],
                         "OFFICIAL_RESPONSE_BYTES_SHA_MISMATCH_NO_GO")
        unavailable = inspect_claimed_official_document(
            claim, row, fetch_bytes=lambda url: (_ for _ in ()).throw(
                ProbeError("timeout")))
        self.assertEqual(unavailable["status"], "PUBLIC_DOCUMENT_UNAVAILABLE_NO_GO")
        with self.assertRaises(ProbeError):
            inspect_claimed_official_document(
                claim, row, fetch_bytes=lambda url: b"x" * (DOC_SIZE + 1))
        with self.assertRaises(ProbeError):
            inspect_claimed_official_document(
                dict(claim, source_sha256="f"*64), row,
                fetch_bytes=lambda url: b"public docs")
        with self.assertRaises(ProbeError):
            inspect_claimed_official_document(
                dict(claim, public_evidence_url="https://evil.test/"), row,
                fetch_bytes=lambda url: b"public docs")
        with self.assertRaises(ProbeError):
            inspect_claimed_official_document(
                dict(claim, independent_verification=True), row,
                fetch_bytes=lambda url: b"public docs")

    def test_bounded_opt_in_single_pass_and_repeatable_report(self):
        h = fixture()
        row = rows(h)[0]
        claim = public_doc_claim(row)
        observed = []
        def fetch_json(url):
            observed.append(("github", url))
            return checked_json(url)
        def fetch_bytes(url):
            observed.append(("docs", url))
            return b"public docs"
        handoff_calls = []
        receipt_calls = []
        with synthetic_root() as root:
            def handoff_f(root_arg):
                handoff_calls.append(root_arg)
                return h
            def receipts_f(folder):
                receipt_calls.append(folder)
                return [claim]
            report = perform_public_probe_batch(
                root, item_id=row["library_item_id"], top=1,
                fetch_json=fetch_json, fetch_bytes=fetch_bytes,
                handoff_factory=handoff_f, receipt_reader=receipts_f)
            self.assertEqual(len(handoff_calls), 1)
            self.assertEqual(len(receipt_calls), 1)
            self.assertEqual(report["schema"], SCHEMA)
            self.assertEqual(report["status"],
                             "PUBLIC_SOURCE_OBSERVATION_REVIEW_REQUIRED_NO_GO")
            self.assertEqual(report["observed_candidate_count"], 1)
            self.assertEqual(report["source_linked_candidate_count"], 26)
            self.assertEqual(report["v05_receipts_reviewed"], 1)
            self.assertEqual(report["public_source_metadata_responses"], 1)
            self.assertEqual(report["public_revision_identity_matches"], 1)
            self.assertEqual(report["official_document_http_bodies_checked"], 1)
            self.assertEqual(report["submitted_document_digests_matching_response"], 1)
            self.assertLessEqual(len(observed), report["max_external_public_requests"])
            self.assertEqual(report["approved_rule_count"], 0)
            self.assertEqual(report["deployed_rule_count"], 0)
            self.assertFalse(report["auto_promoted"])
            self.assertFalse(report["external_source_code_executed"])
            self.assertFalse((root / "runtime").exists())
            self.assertEqual(report["results"][0]["inert_rule_review_draft"][
                "type"], "REVIEW_ONLY_INERT_PREVENTION_OUTLINE")
            self.assertIsNone(report["results"][0]["inert_rule_review_draft"][
                "executable_command"])
            again = perform_public_probe_batch(
                root, item_id=row["library_item_id"], top=1,
                fetch_json=fetch_json, fetch_bytes=fetch_bytes,
                handoff_factory=handoff_f, receipt_reader=receipts_f)
            self.assertEqual(report["audit_report_sha256"],
                             again["audit_report_sha256"])

    def test_batch_capacity_source_diversity_and_conflicted_receipts_stop(self):
        h = fixture()
        called = []
        with synthetic_root() as root:
            def fetch(url):
                called.append(url)
                return checked_json(url)
            report = perform_public_probe_batch(
                root, top=5, fetch_json=fetch, fetch_bytes=lambda url: b"",
                handoff_factory=lambda root: h, receipt_reader=lambda loc: [])
            self.assertEqual(report["observed_candidate_count"], 5)
            self.assertEqual(len(called), 5)
            self.assertGreaterEqual(
                len({x["source_id"] for x in report["results"]}), 3)
            self.assertTrue(all(not x["source_metadata_is_fix_verification"]
                                for x in report["results"]))
            for bad in (0, 6, True):
                with self.subTest(top=bad), self.assertRaises(BatchError):
                    perform_public_probe_batch(root, top=bad)
            row = rows(h)[0]
            claimed = public_doc_claim(row)
            stale = dict(claimed, receipt_id="b"*64,
                         source_sha256="f"*64)
            with self.assertRaises(BatchError):
                perform_public_probe_batch(
                    root, top=1, item_id=row["library_item_id"],
                    handoff_factory=lambda root: h,
                    receipt_reader=lambda loc: [claimed, stale],
                    fetch_json=fetch)
            self.assertFalse((root / "runtime").exists())

    def test_windows_loopback_rejected_post_bodies_never_run_public_probe(self):
        h = fixture()
        row = rows(h)[0]
        calls = []
        def deny_probe(*_args, **_kwargs):
            calls.append(True)
            raise AssertionError("POST must never trigger a public probe")
        with browser(h, deny_probe) as url:
            for size in (1, 512, 8192):
                for iteration in range(4):
                    with self.subTest(size=size, iteration=iteration):
                        request = Request(
                            url + "/public-check/" + row["library_item_id"],
                            data=b"x" * size, method="POST")
                        with self.assertRaises(HTTPError) as error:
                            urlopen(request, timeout=5)
                        self.assertEqual(error.exception.code, 405)
        self.assertEqual(calls, [])

    def test_http_explicit_click_required_and_status_retains_not_verified(self):
        h = fixture()
        row = rows(h)[0]
        invoked = []
        def prober(root, *, item_id, top):
            invoked.append((item_id, top))
            with synthetic_root() as fixture_root:
                return perform_public_probe_batch(
                    fixture_root, item_id=item_id, top=top,
                    handoff_factory=lambda root: h,
                    receipt_reader=lambda loc: [],
                    fetch_json=checked_json)
        with browser(h, prober) as url:
            with urlopen(url + "/health", timeout=5) as response:
                receipt = json.load(response)
                self.assertEqual(receipt["schema"], UI_SCHEMA)
                self.assertEqual(receipt["external_requests_without_explicit_click"], 0)
            with urlopen(url + "/audit", timeout=5) as response:
                audit_html = response.read().decode("utf-8")
                self.assertIn("V0.9", audit_html)
                self.assertIn("원장에 결속된 공개 후보", audit_html)
            with urlopen(url + "/audit/item/" + row["library_item_id"],
                         timeout=5) as response:
                item_html = response.read().decode("utf-8")
                self.assertIn("공개 원본 SHA 대조 실행", item_html)
                self.assertIn('href="/public-check/' + row["library_item_id"] + '"',
                              item_html)
            self.assertEqual(invoked, [])
            with urlopen(url + "/public-check/" + row["library_item_id"],
                         timeout=5) as response:
                body = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("공개 원본 대조 결과", body)
                self.assertIn("PUBLIC_MERGE_IDENTITY_MATCHED_NOT_FIX_VERIFIED", body)
                self.assertIn("NOT_VERIFIED", body)
                self.assertIn("검증 완료 규칙: 0", body)
                self.assertIn(UI_SCHEMA, body)
                self.assertNotIn("OWNER_APPROVED", body)
            self.assertEqual(invoked, [(row["library_item_id"], 1)])
            for path in (
                "/public-check/foo", "/public-check/" + "f"*64 + "?url=evil",
                "/public-check/" + "f"*64 + "/../../secrets",
            ):
                with self.subTest(path=path), self.assertRaises(HTTPError) as err:
                    urlopen(url + path, timeout=5)
                self.assertIn(err.exception.code, (400, 404))
            with self.assertRaises(HTTPError) as err:
                urlopen(Request(url + "/public-check/" + row["library_item_id"],
                                data=b"x", method="POST"), timeout=5)
            self.assertEqual(err.exception.code, 405)
            with self.assertRaises(HTTPError) as err:
                urlopen(Request(url + "/public-check/" + row["library_item_id"],
                                headers={"Host":"evil.example"}), timeout=5)
            self.assertEqual(err.exception.code, 403)
            self.assertEqual(invoked, [(row["library_item_id"], 1)])


if __name__ == "__main__":
    unittest.main()
