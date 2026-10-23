"""Selected public Library revision identity: isolated synthetic API tests.

All network transport and public API replies are injected; real live GET is
not performed by CI or by this suite. No outside files, source code execution,
MCP modification, DB creation outside TemporaryDirectory, or releases.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ucie_public.rulepack import canonical_json
from ucie_miner.public_batch import build_public_batch
from ucie_miner.public_discovery import DiscoveryError
from ucie_miner.public_git_commit_skills import GIT_COMMITS_URL
from ucie_miner.public_library_graph import preview_library_knowledge_graph
from ucie_miner.public_library_review_store import (
    ZERO_HEAD, append_local_library_review_history,
)
from ucie_miner.public_library_signed_review import EVENT_SCHEMA
from ucie_miner.public_library_upstream_recheck import (
    _canonical_endpoint, _fetch_public_exact,
    recheck_library_candidate_public_identity,
)
from test_ucie_stage9_batch import NOW, metadata, evidence
from test_ucie_stage10_git_commit_skills import git_commit

STAMP = datetime(2026, 10, 22, 5, tzinfo=timezone.utc)


def research_batch(*, with_git=False):
    def git_fetch(url):
        assert url == GIT_COMMITS_URL
        return [git_commit(42)]
    return build_public_batch(
        metadata_fetch=metadata, evidence_fetch=evidence, now=NOW,
        max_enrich=1 if with_git else 2,
        include_git_commits=with_git, git_commit_fetch=git_fetch)


class LibraryUpstreamRecheckTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        self.owner = Ed25519PrivateKey.generate()
        self.qa = Ed25519PrivateKey.generate()
        self.trust = {
            "owner_trust": self.owner.public_key(),
            "qa_trust": self.qa.public_key(),
            "at_time": STAMP,
            "expected_head_sha256": ZERO_HEAD,
        }
        self.current = research_batch()
        self.card = next(
            n for n in preview_library_knowledge_graph(self.current)["nodes"]
            if n["kind"] == "UNVERIFIED_PUBLIC_RESEARCH_REFERENCE"
        )

    def pr_reply(self, sha=None):
        url = self.card["public_url"]
        source = self.card["source"]
        n = int(url.rsplit("/", 1)[1])
        return {
            "number": n, "html_url": url, "state": "closed",
            "base": {"repo": {"full_name": source}},
            "merge_commit_sha": sha or self.card["pinned_revision_sha"],
            "merged_at": "2026-10-10T10:00:00Z", "changed_files": 2,
        }

    def recheck(self, *, fetch, **kwargs):
        return recheck_library_candidate_public_identity(
            self.root, self.current, self.card["public_url"],
            live=True, fetch=fetch, **{**self.trust, **kwargs})

    def test_pr_response_exact_public_sha_pending_not_qa(self):
        urls = []
        def fake(url):
            urls.append(url)
            return self.pr_reply(), 999
        result = self.recheck(fetch=fake)
        self.assertEqual(urls, [
            f"https://api.github.com/repos/{self.card['source']}"
            f"/pulls/{self.card['public_url'].rsplit('/', 1)[1]}"
        ])
        self.assertEqual(result["status"],
                         "PUBLIC_UPSTREAM_PINNED_IDENTITY_OBSERVED_QA_PENDING_NO_GO")
        self.assertTrue(result["public_revision_matches"])
        self.assertTrue(result["test_transport_injected"])
        self.assertFalse(result["public_metadata_api_response_observed"])
        self.assertFalse(result["release_inclusion_independently_verified"])
        self.assertFalse(result["candidate_specific_regression_qa_verified"])
        self.assertEqual(result["automatic_rule_promotions"], 0)
        self.assertEqual(result["persistent_writes"], 0)
        self.assertFalse(result["production_approved"])

    def test_mismatched_sha_and_rate_limit_do_not_get_approved(self):
        different = "b" * 40
        if different == self.card["pinned_revision_sha"]:
            different = "a" * 40
        mismatch = self.recheck(fetch=lambda _: (self.pr_reply(different), 999))
        self.assertEqual(mismatch["status"],
                         "PUBLIC_PINNED_REVISION_SHA_MISMATCH_NO_GO")
        self.assertFalse(mismatch["public_revision_matches"])
        low_budget = self.recheck(fetch=lambda _: (self.pr_reply(), 2))
        self.assertEqual(low_budget["status"],
                         "PUBLIC_API_RATE_LIMIT_PAUSED_NO_GO")
        self.assertFalse(low_budget["public_metadata_api_response_observed"])

    def test_permission_and_candidate_scope_fail_before_transport(self):
        def no_network(_):
            raise AssertionError("transport called without permission")
        with self.assertRaises(DiscoveryError):
            recheck_library_candidate_public_identity(
                self.root, self.current, self.card["public_url"],
                live=False, fetch=no_network, **self.trust)
        with self.assertRaises(DiscoveryError):
            recheck_library_candidate_public_identity(
                self.root, self.current, "https://github.com/git/git/pull/99999",
                live=True, fetch=no_network, **self.trust)

    def test_foreign_metadata_identity_fails_closed(self):
        cases = [
            {"html_url": "https://github.com/foreign/repo/pull/5"},
            {"base": {"repo": {"full_name": "foreign/repo"}}},
            {"state": "open"},
            {"merged_at": "2029-01-01T00:00:00Z"},
            {"number": 99},
        ]
        for delta in cases:
            with self.subTest(delta=delta), self.assertRaises(DiscoveryError):
                self.recheck(fetch=lambda _, d=delta: (
                    {**self.pr_reply(), **d}, 999))

    def test_invalid_transport_envelope_and_url_denied(self):
        for reply in (self.pr_reply(), (self.pr_reply(), True),
                      (self.pr_reply(), -1), (["data"], 10)):
            with self.subTest(reply=type(reply)), self.assertRaises(DiscoveryError):
                self.recheck(fetch=lambda _, r=reply: r)
        for url in (
            "https://api.github.com/repos/git/git/commits?per_page=100",
            "https://api.github.com/repos/foreign/private/pulls/5",
            "http://api.github.com/repos/python/cpython/pulls/3",
            "https://api.github.com/repos/python/cpython/pulls/3/files",
        ):
            with self.subTest(url=url), self.assertRaises(DiscoveryError):
                _fetch_public_exact(url)

    def test_git_direct_commit_exact_and_merge_denial(self):
        current = research_batch(with_git=True)
        graph = preview_library_knowledge_graph(current)
        card = next(n for n in graph["nodes"]
                    if n["revision_kind"] == "GIT_DIRECT_COMMIT_SHA")
        endpoint, kind, number = _canonical_endpoint({
            "source": card["source"], "public_url": card["public_url"],
            "pinned_revision_sha": card["pinned_revision_sha"],
        })
        self.assertEqual(
            endpoint, "https://api.github.com/repos/git/git/commits/"
                      + card["pinned_revision_sha"])
        self.assertEqual(kind, "COMMIT")
        self.assertIsNone(number)

        def fake(_):
            return git_commit(42), 50
        kwargs = {**self.trust, "live": True, "fetch": fake}
        result = recheck_library_candidate_public_identity(
            self.root, current, card["public_url"], **kwargs)
        self.assertTrue(result["public_revision_matches"])
        self.assertFalse(result["candidate_specific_regression_qa_verified"])
        with self.assertRaises(DiscoveryError):
            recheck_library_candidate_public_identity(
                self.root, current, card["public_url"],
                **{**kwargs, "fetch": lambda _: (
                    git_commit(42, merged=True), 60)})

    def test_owner_revoked_candidate_cannot_be_unblocked_by_public_sha(self):
        issued = STAMP - timedelta(hours=2)
        def entry(action, serial):
            reviewed = action == "REVIEW_ATTESTED"
            claim = {
                "schema": EVENT_SCHEMA, "action": action,
                "public_url": self.card["public_url"],
                "pinned_revision_sha": self.card["pinned_revision_sha"],
                "evidence_sha256": self.card["evidence_fingerprint_sha256"],
                "version_claim": "3.15" if reviewed else None,
                "review_evidence_sha256": "f" * 64 if reviewed else None,
                "review_claims": {
                    "source_license": True, "security": True,
                    "regression": True, "release_version": True,
                } if reviewed else None,
                "serial": serial,
                "issued_utc": issued.isoformat().replace("+00:00", "Z"),
                "expires_utc": (issued + timedelta(days=1)).isoformat()
                    .replace("+00:00", "Z") if reviewed else None,
            }
            raw = canonical_json(claim)
            return {
                "claim": claim, "owner_signature_hex": self.owner.sign(raw).hex(),
                "qa_signature_hex": self.qa.sign(raw).hex() if reviewed else None,
            }
        first = append_local_library_review_history(
            self.root, self.current, [entry("REVIEW_ATTESTED", 1)],
            expected_head_sha256=ZERO_HEAD, allow_disk_write=True,
            owner_trust=self.owner.public_key(),
            qa_trust=self.qa.public_key(), at_time=STAMP)
        revoked = append_local_library_review_history(
            self.root, self.current, [entry("REVOKE", 2)],
            expected_head_sha256=first["head_sha256"],
            allow_disk_write=True, owner_trust=self.owner.public_key(),
            qa_trust=self.qa.public_key(), at_time=STAMP)
        got = self.recheck(
            fetch=lambda _: (self.pr_reply(), 100),
            expected_head_sha256=revoked["head_sha256"])
        self.assertTrue(got["public_revision_matches"])
        self.assertEqual(got["review_state"], "OWNER_REVOKED_BLOCKED_NO_GO")
        self.assertTrue(got["owner_revocation_kept_blocking"])
        self.assertFalse(got["production_approved"])


if __name__ == "__main__":
    unittest.main()
