"""UCIE V0.2 ranked/paged search and local UI: synthetic public metadata only."""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
import json
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ucie_miner.library_explore import (
    INCOMPLETE, READY, ExploreError, explore_linked_public_candidates,
)
from ucie_miner.library_browser_v02 import (
    SCHEMA, read_filters, render_results, make_handler, UIError,
)
from ucie_miner.public_discovery import SOURCE_SKILL
from ucie_public.policy import PolicyError


def fixture():
    sources = ("python/cpython", "PowerShell/PowerShell", "git/git")
    tasks = []
    for idx in range(26):
        source = sources[idx % len(sources)]
        n = idx + 1
        purpose = "API_CONTRACT" if n % 2 else "CONCURRENCY"
        tasks.append({
            "source": source,
            "reference": "pr:" + str(n) + ":" + ("a" * 40),
            "skill_id": SOURCE_SKILL[source],
            "pattern_code": purpose,
            "evidence_sha256": sha256(("evidence:" + str(idx)).encode()).hexdigest(),
            "candidate_id_sha256": sha256(("candidate:" + str(idx)).encode()).hexdigest(),
            "status": "UNVERIFIED_CANDIDATE_ONLY",
            "approval": False,
            "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
            "stage6_candidate": None,
        })
    return {
        "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
        "status": "LINKED_UNVERIFIED_NO_GO",
        "tasks": tasks,
        "source_revisions": len(tasks), "linked_revisions": len(tasks),
        "pending_source_revisions": 0, "approved_rules": 0,
        "auto_promoted": False, "production_approved": False, "deploy_allowed": False,
    }


@contextmanager
def local_browser(handoff):
    def explorer(root, **args):
        return explore_linked_public_candidates(handoff, **args)
    with HTTPServer(("127.0.0.1", 0),
                    make_handler(Path("Z:/synthetic/UCIE"), explorer=explorer)) as server:
        t = Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            yield "http://127.0.0.1:" + str(server.server_port)
        finally:
            server.shutdown()
            t.join(timeout=5)


class CatalogTests(unittest.TestCase):
    def test_complete_verified_catalog_page_by_page_without_duplicates(self):
        h = fixture()
        pages = []
        for p in range(1, 7):
            result = explore_linked_public_candidates(h, page=p, limit=5)
            self.assertEqual(result["status"], READY)
            self.assertEqual(result["total_matches"], 26)
            self.assertEqual(result["total_pages"], 6)
            self.assertEqual(result["source_linked_count"], 26)
            self.assertFalse(result["auto_promoted"])
            self.assertEqual(result["operating_database_writes"], 0)
            pages.extend(result["items"])
        self.assertEqual(len(pages), 26)
        self.assertEqual(len({r["library_item_id"] for r in pages}), 26)
        # Empty-term ranking is intentionally source-diverse rather than
        # alphabetical, which used to show only PowerShell on page one.
        self.assertEqual(
            len({r["source_id"] for r in pages[:3]}), 3)
        self.assertEqual(
            explore_linked_public_candidates(h, limit=5, page=1)["items"],
            pages[:5])

    def test_facets_ranking_query_and_filters(self):
        h = fixture()
        first = explore_linked_public_candidates(h, limit=10)
        self.assertEqual(sum(first["source_facets"].values()), 26)
        self.assertEqual(sum(first["domain_facets"].values()), 26)
        self.assertEqual(sum(first["kind_facets"].values()), 26)
        python = explore_linked_public_candidates(h, query="Python", limit=5)
        self.assertEqual(python["total_matches"], 9)
        self.assertEqual(python["total_pages"], 2)
        self.assertTrue(all(x["domain"] == "Python" for x in python["items"]))
        self.assertEqual(python["ranking_method"],
                         "BOUNDED_METADATA_LEXICAL_V1_NOT_SEMANTIC")
        purpose = explore_linked_public_candidates(h, query="API_CONTRACT", limit=10)
        self.assertEqual(purpose["total_matches"], 13)
        self.assertTrue(all(r["purpose_code"] == "API_CONTRACT"
                            for r in purpose["items"]))
        filtered = explore_linked_public_candidates(
            h, domain="Git", source_id="repo:git/git", limit=5)
        self.assertEqual(filtered["total_matches"], 8)
        self.assertEqual(filtered["source_facets"].get("repo:git/git"), 8)
        self.assertEqual(filtered["domain_facets"].get("Git"), 8)
        self.assertEqual(filtered["total_pages"], 2)

    def test_detail_exact_and_missing_id(self):
        h = fixture()
        first = explore_linked_public_candidates(h)["items"][0]
        detail = explore_linked_public_candidates(h, item_id=first["library_item_id"])
        self.assertEqual(detail["status"], READY)
        self.assertEqual(detail["detail"]["public_url"], first["public_url"])
        self.assertFalse(detail["detail"]["export_allowed"])
        self.assertEqual(detail["detail"]["version_scope_claim"], "UNDETERMINED")
        self.assertIsNone(explore_linked_public_candidates(h, item_id="f"*64)["detail"])
        with self.assertRaises(ExploreError):
            explore_linked_public_candidates(h, item_id="../../arbitrary")

    def test_partial_ledger_and_forged_approval_fail_closed(self):
        h = fixture()
        h["status"] = "SOURCE_REVISIONS_PENDING_NO_GO"
        h["pending_source_revisions"] = 1
        h["source_revisions"] += 1
        incomplete = explore_linked_public_candidates(h)
        self.assertEqual(incomplete["status"], INCOMPLETE)
        self.assertEqual(incomplete["items"], [])
        self.assertEqual(incomplete["total_matches"], 0)
        forged = fixture()
        forged["tasks"][0]["approval"] = True
        with self.assertRaises(PolicyError):
            explore_linked_public_candidates(forged)
        wrong = fixture()
        wrong["tasks"][0]["skill_id"] = "powershell-safe-calls"
        with self.assertRaises(ExploreError):
            explore_linked_public_candidates(wrong)

    def test_safe_bounds_and_no_fake_lifecycle(self):
        h = fixture()
        for kwargs in ({"page": 0}, {"page": 201}, {"page": True},
                       {"limit": 21}, {"query": "<script>"},
                       {"item_id": "f" * 65}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                explore_linked_public_candidates(h, **kwargs)
        result = explore_linked_public_candidates(h)
        for row in result["items"]:
            self.assertEqual(row["lifecycle"], "UNVERIFIED_CANDIDATE_ONLY")
            self.assertFalse(row["human_approved"])
            self.assertFalse(row["export_allowed"])


class BrowserTests(unittest.TestCase):
    def test_parameters_and_html_escaping(self):
        f = read_filters("q=Python&domain=Python&kind=&source=&limit=5&page=2")
        self.assertEqual(f["page"], 2)
        self.assertEqual(f["query"], "Python")
        for bad in ("foo=bar", "q=x&q=y", "page=201", "limit=21",
                    "q=%3Cscript%3E", "source=repo%3Aunapproved%2Fprivate",
                    "page=-1", "q=x%0Ay"):
            with self.subTest(bad=bad), self.assertRaises(UIError):
                read_filters(bad)
        html = render_results(
            read_filters(""), explore_linked_public_candidates(fixture()))
        self.assertNotIn("<script", html)
        self.assertIn("다음 페이지", html)
        self.assertIn("상세보기", html)
        self.assertIn("출처별 후보", html)

    def test_loopback_http_pages_detail_health_and_security(self):
        h = fixture()
        with local_browser(h) as url:
            with urlopen(url + "/", timeout=5) as r:
                self.assertEqual(r.status, 200)
                self.assertIn("검색 조건을 선택", r.read().decode())
            with urlopen(url + "/?q=&domain=&kind=&source=&limit=5&page=1",
                         timeout=5) as r:
                page = r.read().decode()
                self.assertEqual(r.status, 200)
                self.assertEqual(r.headers["Cache-Control"], "no-store")
                self.assertIn("검색된 후보 26건", page)
                self.assertIn("다음 페이지", page)
                self.assertIn("상세보기", page)
            with urlopen(url + "/?q=&domain=&kind=&source=&limit=5&page=2",
                         timeout=5) as r:
                self.assertIn("2/6", r.read().decode())
            ident = explore_linked_public_candidates(h)["items"][0]["library_item_id"]
            with urlopen(url + "/item/" + ident, timeout=5) as r:
                text = r.read().decode()
                self.assertIn("근거 후보 상세", text)
                self.assertIn("미확인 · 검증된 지원 버전 없음", text)
                self.assertIn("승인된 출처", text)
                self.assertIn("공개 근거 열기", text)
            with urlopen(url + "/health", timeout=5) as r:
                receipt = json.load(r)
                self.assertEqual(receipt["schema"], SCHEMA)
                self.assertEqual(receipt["db_writes"], 0)
            for path in ("/?q=%3Cscript%3E", "/item/../../secret", "/?q=x&q=y",
                         "/item/" + "f"*64, "/other"):
                with self.subTest(path=path), self.assertRaises(HTTPError) as exc:
                    urlopen(url + path, timeout=5)
                self.assertIn(exc.exception.code, (400, 404))
            with self.assertRaises(HTTPError) as exc:
                urlopen(Request(url + "/", data=b"no", method="POST"), timeout=5)
            self.assertEqual(exc.exception.code, 405)
            with self.assertRaises(HTTPError) as exc:
                urlopen(Request(url + "/", headers={"Host": "not-local.invalid"}),
                        timeout=5)
            self.assertEqual(exc.exception.code, 403)

    def test_incomplete_linkage_returns_no_cards_and_no_detail(self):
        h = fixture()
        h["status"] = "SOURCE_REVISIONS_PENDING_NO_GO"
        h["pending_source_revisions"] = 1
        h["source_revisions"] += 1
        with local_browser(h) as url:
            with urlopen(url + "/?q=&limit=10&page=1", timeout=5) as r:
                page = r.read().decode()
                self.assertIn("원장 연결 미완료", page)
                self.assertNotIn("상세보기", page)
            ident = "a" * 64
            with self.assertRaises(HTTPError) as exc:
                urlopen(url + "/item/" + ident, timeout=5)
            self.assertEqual(exc.exception.code, 404)

    def test_forged_approval_is_503_not_search_result(self):
        h = fixture()
        h["tasks"][0]["approval"] = True
        with local_browser(h) as url:
            with self.assertRaises(HTTPError) as exc:
                urlopen(url + "/?q=Python&limit=10&page=1", timeout=5)
            self.assertEqual(exc.exception.code, 503)
            self.assertIn("SOURCE_VALIDATION_FAILED_NO_GO",
                          exc.exception.read().decode())


if __name__ == "__main__":
    unittest.main()
