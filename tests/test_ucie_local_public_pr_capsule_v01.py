"""UCIE B2 real localhost PUBLIC-ONLY metadata import, source review and rejects."""
from __future__ import annotations

import http.client
from hashlib import sha256
from http.server import HTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch

from ucie_miner import local_v1_app_v01 as local
from ucie_miner import local_public_pr_capsule_v01 as cap
from ucie_miner.public_discovery import SOURCE_SKILL

FIXTURES = (
    ("python/cpython", "pr:153462:999a046b24cff4ba0e72b574196721f66bd08237",
     "PY_SCANDIR_SHARED_ITERATOR_RACE", "a"),
    ("PowerShell/PowerShell", "pr:28042:bd8cb01a7d5b86129c45eaa14ab5830a63b1283f",
     "PS_FUZZY_GET_COMMAND_DUPLICATES", "b"),
    ("git/git", "pr:45984:" + "c"*40, "GIT_PORCELAIN_SAFE", "c"),
    ("modelcontextprotocol/python-sdk", "pr:3696:" + "d"*40,
     "MCP_PROMPT_MISSING_ARGUMENT", "d"),
    ("actions/runner-images", "pr:13333:" + "e"*40,
     "RUNNER_ENVIRONMENT_DRIFT", "e"),
)


def synthetic_handoff(count: int = 5):
    tasks = []
    for source, reference, purpose, token in FIXTURES[:count]:
        tasks.append({
            "source": source, "reference": reference,
            "pattern_code": purpose,
            "skill_id": SOURCE_SKILL[source],
            "evidence_sha256": token*64,
            "candidate_id_sha256": token*64,
            "stage6_candidate": None,
            "status": "UNVERIFIED_CANDIDATE_ONLY", "approval": False,
            "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
        })
    return {
        "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
        "status": "LINKED_UNVERIFIED_NO_GO",
        "source_revisions": count, "linked_revisions": count,
        "pending_source_revisions": 0,
        "tasks": tasks,
        "auto_promoted": False, "production_approved": False,
        "deploy_allowed": False,
    }


def change_snapshot(data: bytes, fn):
    val = json.loads(data)
    fn(val)
    val["items_sha256"] = sha256(cap._canonical(val["items"])).hexdigest()
    result = cap._canonical(val)
    return result, sha256(result).hexdigest()


class PublicOnlyCapsuleUnitTests(unittest.TestCase):
    def setUp(self):
        self.data = cap.build_capsule(synthetic_handoff())
        self.digest = sha256(self.data).hexdigest()

    def test_exact_five_approved_public_metadata_only_and_receipt(self):
        report = cap.inspect_capsule(self.data, self.digest)
        self.assertEqual(report["status"], cap.RECEIVER_STATUS)
        self.assertEqual(report["selected_count"], 5)
        self.assertFalse(report["signature_verified"])
        self.assertFalse(report["source_linkage_independently_attested_on_recipient"])
        self.assertFalse(report["customer_distribution_authorized"])
        self.assertFalse(report["human_approved"])
        self.assertFalse(report["operating_database_writes"])
        self.assertEqual(set(x["source_id"] for x in report["items"]),
                         {"repo:" + x for x in SOURCE_SKILL})
        self.assertFalse(set(cap.ROW_KEYS) & {
            "title", "body", "patch", "source_code", "raw_text", "command",
            "local_path", "email", "credentials", "secret",
        })
        self.assertNotIn("runtime/public_miner", self.data.decode("ascii"))

    def test_deterministic_and_bounded_truncation_is_honest(self):
        content = cap.build_capsule(synthetic_handoff(), limit=2)
        self.assertEqual(content, cap.build_capsule(synthetic_handoff(), limit=2))
        report = cap.inspect_capsule(content, sha256(content).hexdigest())
        self.assertEqual(report["selected_count"], 2)
        self.assertEqual(report["omitted_count"], 3)
        self.assertEqual(report["items"][0]["source_id"], "repo:PowerShell/PowerShell")
        for limit in (0, 49, 1.0, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                cap.build_capsule(synthetic_handoff(), limit=limit)

    def test_large_source_window_selects_approved_domains_fairly(self):
        handoff = synthetic_handoff(0)
        handoff["tasks"] = []
        for i in range(65):
            source, _ref, purpose, _token = FIXTURES[i % len(FIXTURES)]
            handoff["tasks"].append({
                "source": source,
                "reference": "pr:" + str(50000+i) + ":" + f"{i+1:040x}",
                "pattern_code": purpose,
                "skill_id": SOURCE_SKILL[source],
                "evidence_sha256": f"{i+700:064x}",
                "candidate_id_sha256": f"{i+600:064x}",
                "stage6_candidate": None,
                "status": "UNVERIFIED_CANDIDATE_ONLY", "approval": False,
                "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
            })
        handoff["source_revisions"] = 65
        handoff["linked_revisions"] = 65
        blob = cap.build_capsule(handoff)
        report = cap.inspect_capsule(blob, sha256(blob).hexdigest())
        self.assertEqual(report["selected_count"], cap.MAX_ITEMS)
        self.assertEqual(report["omitted_count"], 17)
        counts = {key: sum(
            r["source_id"] == "repo:" + key for r in report["items"])
            for key in SOURCE_SKILL}
        self.assertEqual(sum(counts.values()), cap.MAX_ITEMS)
        self.assertTrue(all(8 <= n <= 11 for n in counts.values()))
        self.assertFalse(report["signature_verified"])

    def test_reject_incomplete_or_forged_source_handoff(self):
        for mutate in (
            lambda x: x.update(status="SOURCE_REVISIONS_PENDING_NO_GO"),
            lambda x: x["tasks"][0].update(approval=True),
            lambda x: x["tasks"][0].update(source="foreign/repo"),
            lambda x: x["tasks"][0].update(skill_id="unregistered"),
            lambda x: x["tasks"][0].update(evidence_sha256="bad"),
            lambda x: x["tasks"][0].update(blocking_reasons=[]),
            lambda x: x["tasks"].append(dict(x["tasks"][0])),
        ):
            handoff = synthetic_handoff()
            mutate(handoff)
            with self.subTest(mutate=repr(mutate)), self.assertRaises(ValueError):
                cap.build_capsule(handoff)

    def test_corruption_wrong_pin_and_dup_fields_fail_closed(self):
        for data, pin in (
            (self.data + b" ", self.digest),
            (self.data, "f"*64),
            (self.data.replace(b"PY_SCANDIR_SHARED", b"PY_SCANDIR_UNKNOWN"),
             self.digest),
            (b"{}", sha256(b"{}").hexdigest()),
            (b"\xff", sha256(b"\xff").hexdigest()),
            (b"0"*cap.MAX_BYTES+b"x", "f"*64),
        ):
            with self.subTest(data=data[:12]), self.assertRaises(ValueError):
                cap.inspect_capsule(data, pin)
        crafted = self.data.replace(
            b'"snapshot_signed":false',
            b'"snapshot_signed":false,"snapshot_signed":true',
        )
        with self.assertRaises(ValueError):
            cap.inspect_capsule(crafted, sha256(crafted).hexdigest())

    def test_reforged_status_source_url_and_metadata_declarations_denied(self):
        transforms = (
            lambda x: x.update(snapshot_signed=True),
            lambda x: x.update(human_approved=True),
            lambda x: x.update(source_linkage_reverified_on_recipient=True),
            lambda x: x["items"][0].update(source_id="repo:OTHER/project"),
            lambda x: x["items"][0].update(public_url="https://evil.invalid/a"),
            lambda x: x["items"][0].update(human_approved=True),
            lambda x: x["items"][0].update(export_allowed=True),
            lambda x: x["items"][0].update(evidence_reference="pr:1:"+("a"*40)),
            lambda x: x["items"][0].update(raw_text="no raw metadata allowed"),
            lambda x: x.update(omitted_count=9),
        )
        for transform in transforms:
            changed, digest = change_snapshot(self.data, transform)
            with self.subTest(fn=repr(transform)), self.assertRaises(ValueError):
                cap.inspect_capsule(changed, digest)

    def test_real_w04_style_search_source_and_pagination(self):
        result = cap.inspect_capsule(self.data, self.digest)
        first = cap.search_capsule(result, query="", limit=2)
        second = cap.search_capsule(result, query="", limit=2, offset=2)
        self.assertEqual(first["total_matches"], 5)
        self.assertEqual(first["returned_count"], 2)
        self.assertEqual(len(second["items"]), 2)
        self.assertFalse(first["independent_upstream_source_attested"])
        self.assertFalse(first["snapshot_signed"])
        self.assertEqual(cap.search_capsule(
            result, query="Python", limit=10)["total_matches"], 2)
        # W04 substring search matches Python itself and MCP python-sdk.
        self.assertEqual(cap.search_capsule(
            result, query="Git", limit=10,
            source_id="repo:git/git")["total_matches"], 1)
        for filters in (
            dict(query="../SECRET"), dict(source_id="repo:private/foo"),
            dict(query="a", offset=-1), dict(query="a", limit=1000),
        ):
            with self.subTest(filters=filters), self.assertRaises(ValueError):
                cap.search_capsule(result, **filters)

    def test_owner_preview_and_export_need_separate_explicit_consent(self):
        with TemporaryDirectory(prefix="UCIE_PUBLIC_CAPSULE_TEST_") as folder:
            root = Path(folder) / "UCIE"
            (root / ".git").mkdir(parents=True)
            with patch.object(cap, "prepare_verification_handoff",
                              return_value=synthetic_handoff()):
                preview = cap.capture_preview(root)
                self.assertEqual(preview["candidate_metadata_rows"], 5)
                self.assertFalse(preview["local_capsule_written"])
                self.assertFalse((root / cap.FILE).exists())
                with self.assertRaises(cap.PublicCapsuleError):
                    cap.export_once(root, consent="yes")
                receipt = cap.export_once(root, consent=cap.CONSENT)
                self.assertEqual(receipt["status"],
                                 "OWNER_LOCAL_ONLY_UNSIGNED_METADATA_FILES_CREATED_NO_GO")
                reread = cap.read_optional_capsule(root)
                self.assertEqual(reread["selected_count"], 5)
                with self.assertRaises(cap.PublicCapsuleError):
                    cap.export_once(root, consent=cap.CONSENT)
            self.assertFalse((root / "runtime").exists())

    def test_partial_or_symlinked_receipt_refused(self):
        with TemporaryDirectory(prefix="UCIE_CAPSULE_TAMPER_") as folder:
            root = Path(folder) / "UCIE"
            (root / ".git").mkdir(parents=True)
            (root / cap.FILE).write_bytes(self.data)
            with self.assertRaises(ValueError):
                cap.read_optional_capsule(root)
            (root / cap.PIN).write_bytes((self.digest + "\n").encode("ascii"))
            self.assertEqual(cap.read_optional_capsule(root)["selected_count"], 5)
            (root / cap.PIN).write_bytes(("a"*64+"\n").encode("ascii"))
            with self.assertRaises(ValueError):
                cap.read_optional_capsule(root)


class PublicOnlyCapsuleRealHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="UCIE_CAPSULE_HTTP_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / ".git").mkdir(parents=True)
        data = cap.build_capsule(synthetic_handoff())
        (self.root / cap.FILE).write_bytes(data)
        (self.root / cap.PIN).write_bytes(
            (sha256(data).hexdigest() + "\n").encode("ascii"))
        self.server = HTTPServer(("127.0.0.1", 0), local.make_handler(self.root))
        thread = Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 3)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, route, *, method="GET", host=None):
        conn = http.client.HTTPConnection("127.0.0.1",
                                          self.server.server_port, timeout=6)
        try:
            conn.request(method, route, headers={
                "Host": host or "127.0.0.1:" + str(self.server.server_port),
            })
            result = conn.getresponse()
            return result.status, result.read().decode("utf-8", "replace"), dict(
                result.getheaders())
        finally:
            conn.close()

    def test_direct_backend_search_preserves_snapshot_marker(self):
        report = local._search(self.root, "Python", limit=10)
        self.assertEqual(report["portable_snapshot_status"], cap.RECEIVER_STATUS)
        self.assertEqual(report["status"],
                         "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO")
        self.assertEqual(report["network_requests"], 0)
        self.assertEqual(report["operating_database_writes"], 0)
        # Call the same page rendering functions directly for useful failure
        # diagnostics without logging any user or private data.
        for renderer in (local._library, local._evolution, local._error):
            with self.subTest(renderer=renderer.__name__):
                page = renderer(self.root, "q=Python")
                self.assertIn('data-public-snapshot-unsigned="true"', page)

    def test_real_library_and_evolution_show_unverified_public_pr_and_docs(self):
        for endpoint in ("/local/library", "/local/evolution", "/local/error"):
            for word in ("Python", "Git", "MCP"):
                route = endpoint + "?q=" + word
                with self.subTest(route=route):
                    status, page, headers = self.request(route)
                    self.assertEqual(status, 200, route)
                    self.assertIn('data-public-snapshot-unsigned="true"', page)
                    self.assertIn("독립 출처 확인 전", page)
                    self.assertIn("UNVERIFIED_CANDIDATE_ONLY", page)
                    self.assertIn("github.com/", page)
                    self.assertNotIn("개선 방향 살펴보기<span", page)
                    self.assertEqual(headers["Cache-Control"], "no-store")
                    self.assertNotIn("customer_distribution_authorized=True", page)
        self.assertFalse((self.root / "runtime").exists())

    def test_review_selection_stays_denied_without_ledger_provenance(self):
        import urllib.parse
        data = cap.read_optional_capsule(self.root)
        record = data["items"][0]
        q = urllib.parse.quote("PowerShell", safe="")
        route = "/local/review?q=" + q + "&id=" + record["library_item_id"]
        code, page, _ = self.request(route)
        self.assertEqual(code, 400)
        self.assertIn("FAIL_CLOSED", page)

    def test_bad_snapshot_or_host_post_rejected(self):
        for route, method, host, code in (
            ("/local/library?q=Python", "POST", None, 405),
            ("/local/evolution?q=Git", "GET", "other.example", 403),
            ("/local/library?q=Python&source=private/repo", "GET", None, 400),
            ("/local/library?q=Python&page=501", "GET", None, 400),
        ):
            with self.subTest(route=route):
                observed, _, _ = self.request(route, method=method, host=host)
                self.assertEqual(observed, code)
        (self.root / cap.PIN).write_bytes(("f"*64+"\n").encode("ascii"))
        observed, body, _ = self.request("/local/library?q=Python")
        self.assertEqual(observed, 400)
        self.assertIn("FAIL_CLOSED", body)

    def test_live_source_artifacts_disable_capsule_fallback(self):
        runtime = self.root / "runtime"
        runtime.mkdir()
        (runtime / "unexpected.db").write_bytes(b"UCIE inert synthetic")
        status, page, _ = self.request("/local/evolution?q=PowerShell")
        self.assertNotIn('data-public-snapshot-unsigned="true"', page)
        self.assertIn(status, (200, 400))


if __name__ == "__main__":
    unittest.main()
