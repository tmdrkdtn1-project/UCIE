"""UCIE V1.1: offline synthetic release graph and safe review browser E2E.

No network to real GitHub in CI. No upstream code, commands, source checkout,
unapproved repo data, credentials or operating DB changes.
"""
from __future__ import annotations

from contextlib import contextmanager
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import unittest

from test_ucie_library_v02 import fixture
from ucie_miner.library_explore import explore_linked_public_candidates
from ucie_miner.library_audit_v07 import audit_handoff_receipts
from ucie_miner.library_safety_regression_v10 import run_owner_guard_regressions
from ucie_miner.library_release_ancestry_v11 import (
    SCHEMA as RELEASE_SCHEMA, ReleaseEvidenceError,
    _official_release_json, check_current_public_release,
    inspect_release_ancestry,
)
from ucie_miner.library_upstream_review_v11 import (
    SCHEMA as REVIEW_SCHEMA, ReviewBundleError, assemble_review_bundle,
)
from ucie_miner.library_browser_v11 import (
    SCHEMA as UI_SCHEMA, make_handler, render_review,
)


def materials():
    h = fixture()
    candidate = explore_linked_public_candidates(h, limit=20)["items"][0]
    obs = {
        "schema": "UCIE_PUBLIC_OBSERVATION_REPLAY_V10",
        "status": "PUBLIC_OBSERVATIONS_INTEGRITY_ONLY_NOT_FIX_VERIFIED",
        "source_linkage_valid": True,
        "production_approved": False,
        "source_linked_candidates": 26,
        "integrity_checked_observation_count": 1,
        "items_with_observations": 1,
        "observations": [{
            "item_id": candidate["library_item_id"],
            "source_id": candidate["source_id"],
            "revision_hint": candidate["revision_hint"],
            "identity_matched": True,
            "metadata_status": "PUBLIC_MERGE_IDENTITY_MATCHED_NOT_FIX_VERIFIED",
            "receipt_id": "e" * 64,
            "recorded_utc": "2026-11-01T00:00:00+00:00",
            "independently_verified_fix": False,
            "owner_approved": False,
        }],
    }
    return h, candidate, obs


def fake_github(row, tag="v1.2.3", *, graph="ahead", merge_base=None,
                draft=False, observed=True):
    repo = row["source_id"].removeprefix("repo:")
    sha = row["revision_hint"]
    called = []
    def fetch(url):
        called.append(url)
        assert url.startswith("https://api.github.com/repos/" + repo)
        if "/releases/tags/" in url:
            return {
                "id": 123, "tag_name": tag, "draft": draft,
                "prerelease": False,
                "published_at": "2026-10-10T00:00:00Z",
                "html_url": "https://github.com/" + repo + "/releases/tag/" + tag,
            }
        if "/compare/" in url:
            return {
                "base_commit": {"sha": sha},
                "merge_base_commit": {"sha": sha if merge_base is None else merge_base},
                "head_commit": {"sha": "f"*40},
                "status": graph,
                "behind_by": 0 if graph in ("ahead", "identical") else 2,
                "ahead_by": 5 if graph == "ahead" else 0,
                "commits": [{"message": "UNTRUSTED_DO_NOT_EXECUTE"}],
            }
        raise AssertionError("unexpected API request")
    return fetch, called


@contextmanager
def loopback_ui(h, report):
    public_calls = []
    def offline(root, *, item_id):
        if item_id != report["item_id"]:
            raise ReviewBundleError("unknown source identity")
        return report
    with HTTPServer(("127.0.0.1", 0), make_handler(
            Path("Z:/UCIE/synthetic"),
            bundle_reader=offline, auditor=lambda root: audit_handoff_receipts(h, []),
            public_prober=lambda *a, **kw: public_calls.append((a,kw)))) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield ("http://127.0.0.1:" + str(server.server_port),
                   public_calls)
        finally:
            server.shutdown()
            worker.join(timeout=5)


class UcieOfficialPublicReleaseTests(unittest.TestCase):
    def test_release_compare_graph_observation_and_no_fix_pass(self):
        h,row,obs = materials()
        fetch,calls = fake_github(row)
        out = inspect_release_ancestry(row, release_tag="v1.2.3",
                                       fetch_json=fetch)
        self.assertEqual(out["schema"], RELEASE_SCHEMA)
        self.assertTrue(out["public_metadata_observed"])
        self.assertTrue(out["tag_contains_exact_source_commit"])
        self.assertEqual(out["status"],
                         "RELEASE_TAG_CONTAINS_SOURCE_COMMIT_NOT_FIX_VERIFIED")
        self.assertEqual(len(calls), 2)
        self.assertIn("/compare/" + row["revision_hint"] + "...tags/v1.2.3", calls[1])
        self.assertEqual(out["gates"]["UPSTREAM_FIX_REGRESSION"], "NOT_VERIFIED")
        self.assertFalse(out["runtime_version_fix_verified"])
        self.assertFalse(out["rule_approved"])
        self.assertEqual(out["local_writes"], 0)
        self.assertNotIn("UNTRUSTED_DO_NOT_EXECUTE", json.dumps(out))
        # Exact source identity must be replayed and checked first.
        with patch("ucie_miner.library_release_ancestry_v11._root",
                   side_effect=lambda path: Path(path)):
            verified = check_current_public_release(
                Path("Z:/UCIE"), item_id=row["library_item_id"],
                release_tag="v1.2.3", source_reader=lambda root: h,
                replay_reader=lambda root: obs, fetch_json=fetch)
        self.assertTrue(verified["tag_contains_exact_source_commit"])
        self.assertEqual(verified["result_sha256"], out["result_sha256"])

    def test_forged_release_draft_or_divergent_graph_fails_closed(self):
        _, row, _ = materials()
        for fake_kwargs in (
            {"draft":True},
            {"graph":"diverged"},
            {"graph":"behind"},
            {"merge_base":"a"*40},
        ):
            with self.subTest(fake_kwargs=fake_kwargs):
                fake,_ = fake_github(row, **fake_kwargs)
                result = inspect_release_ancestry(
                    row, release_tag="v1.2.3", fetch_json=fake)
                self.assertFalse(result["tag_contains_exact_source_commit"])
                self.assertTrue(result["status"].endswith("_NO_GO"))
                self.assertFalse(result["rule_approved"])
        def unavailable(url):
            raise OSError("offline")
        no = inspect_release_ancestry(
            row, release_tag="v1.2.3", fetch_json=unavailable)
        self.assertEqual(no["status"],
                         "PUBLIC_RELEASE_ANCESTRY_UNAVAILABLE_NO_GO")
        self.assertFalse(no["public_metadata_observed"])

    def test_bad_tags_repos_or_endpoints_rejected_before_any_network(self):
        _, row, _ = materials()
        called=[]
        for tag in ("", "../secret", "a/b", "v1?x", "x"*60, "release%2Fbranch"):
            with self.subTest(tag=tag), self.assertRaises(ReleaseEvidenceError):
                inspect_release_ancestry(
                    row, release_tag=tag, fetch_json=lambda url: called.append(url))
        self.assertEqual(called, [])
        for url in (
            "https://api.github.com/repos/private/unknown/releases/tags/v1",
            "https://api.github.com/repos/python/cpython/releases/latest",
            "https://127.0.0.1/repos/python/cpython/releases/tags/v1",
            "https://api.github.com/repos/python/cpython/compare/abc...tags/v1",
            "https://api.github.com/repos/python/cpython/releases/tags/v1?redirect=x",
        ):
            with self.subTest(url=url), self.assertRaises(ReleaseEvidenceError):
                _official_release_json(url)

    def test_missing_prior_verified_observation_is_no_go(self):
        h,row,obs = materials()
        with patch("ucie_miner.library_release_ancestry_v11._root",
                   side_effect=lambda x: Path(x)):
            with self.assertRaises(ReleaseEvidenceError):
                check_current_public_release(
                    Path("Z:/UCIE"), item_id=row["library_item_id"],
                    release_tag="v1.2.3", source_reader=lambda root:h,
                    replay_reader=lambda root:{
                        "observations": []},
                    fetch_json=lambda url: {})
            altered = json.loads(json.dumps(obs))
            altered["observations"][0]["identity_matched"] = False
            with self.assertRaises(ReleaseEvidenceError):
                check_current_public_release(
                    Path("Z:/UCIE"), item_id=row["library_item_id"],
                    release_tag="v1.2.3", source_reader=lambda root:h,
                    replay_reader=lambda root:altered,
                    fetch_json=lambda url: {})

    def test_review_packet_one_observation_six_guard_pass_no_upstream_pass(self):
        h,row,obs = materials()
        audit = audit_handoff_receipts(h, [])
        guard = run_owner_guard_regressions()
        review = assemble_review_bundle(
            audit, obs, guard, item_id=row["library_item_id"])
        self.assertEqual(review["schema"], REVIEW_SCHEMA)
        self.assertEqual(review["observation_count"], 1)
        self.assertEqual(review["ucie_owned_guard_tests_passed"], 6)
        self.assertEqual(review["independent_upstream_regression_passes"], 0)
        self.assertEqual(review["approved_rule_count"], 0)
        self.assertEqual(review["exportable_rule_count"], 0)
        self.assertFalse(review["auto_promotion"])
        self.assertEqual(len(review["requirements"]), 7)
        self.assertTrue(all(not x["automatic_approval"] for x in review["requirements"]))
        self.assertIsNone(review["independent_upstream_test_recipe"])
        self.assertRegex(review["bundle_sha256"], r"^[0-9a-f]{64}$")
        html = render_review(review)
        self.assertIn("UCIE 자체 안전 회귀시험: 6/6 PASS", html)
        self.assertIn("실제 공개 수정 독립 회귀시험: 0 PASS", html)
        self.assertIn("NOT_PERFORMED", html)
        self.assertIn("NOT_APPROVED", html)
        self.assertIn("실행 가능 규칙 생성 없음", html)
        forged = dict(guard, upstream_fix_verified=True)
        with self.assertRaises(ReviewBundleError):
            assemble_review_bundle(audit, obs, forged,
                                   item_id=row["library_item_id"])
        forgedobs = json.loads(json.dumps(obs))
        forgedobs["observations"][0]["owner_approved"] = True
        with self.assertRaises(ReviewBundleError):
            assemble_review_bundle(audit, forgedobs, guard,
                                   item_id=row["library_item_id"])

    def test_live_local_ui_links_and_strict_get_only(self):
        h,row,obs = materials()
        audit = audit_handoff_receipts(h, [])
        review = assemble_review_bundle(audit, obs, run_owner_guard_regressions(),
                                        item_id=row["library_item_id"])
        with loopback_ui(h, review) as (base,calls):
            with urlopen(base+"/health",timeout=5) as r:
                health=json.load(r)
                self.assertEqual(health["schema"], UI_SCHEMA)
                self.assertEqual(health["automatic_public_checks"],0)
            with urlopen(base+"/audit/item/"+row["library_item_id"],
                         timeout=5) as r:
                page=r.read().decode("utf-8")
                self.assertIn("독립 회귀시험·릴리스 검토 준비표",page)
            with urlopen(base+"/review-bundle/"+row["library_item_id"],
                         timeout=5) as r:
                page=r.read().decode("utf-8")
                self.assertIn("V1.1",page)
                self.assertIn("6/6 PASS",page)
                self.assertIn("실제 공개 수정 독립 회귀시험: 0 PASS",page)
            self.assertEqual(calls, [])
            for path in ("/review-bundle/invalid",
                         "/review-bundle/"+row["library_item_id"]+"?approve=true"):
                with self.subTest(path=path), self.assertRaises(HTTPError) as err:
                    urlopen(base+path,timeout=5)
                self.assertIn(err.exception.code,(400,404))
            with self.assertRaises(HTTPError) as err:
                urlopen(Request(base+"/review-bundle/"+row["library_item_id"],
                                data=b"approve",method="POST"),timeout=5)
            self.assertEqual(err.exception.code,405)
            with self.assertRaises(HTTPError) as err:
                urlopen(Request(base+"/review-bundle/"+row["library_item_id"],
                                headers={"Host":"evil.test"}),timeout=5)
            self.assertEqual(err.exception.code,403)
            self.assertEqual(calls,[])


if __name__=="__main__":
    unittest.main()
