"""Stage 7 synthetic-only public PR provenance regression tests."""
from pathlib import Path
import hashlib
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.review import ReviewError
from ucie_miner.provenance_review import inspect_public_prs


def candidate(source="python/cpython", number=42):
    return {
        "source": source, "pr_number": number,
        "public_url": f"https://github.com/{source}/pull/{number}",
        "merged_at": "2026-10-01T00:00:00Z",
        "evidence_sha256": hashlib.sha256(b"synthetic-only").hexdigest(),
    }


def upstream(n=42, repo="python/cpython", merged=True):
    return {
        "number": n, "merged": merged,
        "merged_at": "2026-10-01T00:00:00Z",
        "html_url": f"https://github.com/python/cpython/pull/{n}",
        "base": {"repo": {"full_name": repo}},
        "merge_commit_sha": "a" * 40,
    }


class ProvenanceTests(unittest.TestCase):
    def test_default_no_network_or_approval(self):
        calls = []
        receipt = inspect_public_prs([candidate()], fetch=lambda url: calls.append(url))
        self.assertEqual(calls, [])
        self.assertEqual(receipt["items"][0]["source_check"], "NOT_CHECKED")
        self.assertFalse(receipt["live_checked"])
        self.assertFalse(receipt["production_approved"])
        self.assertEqual(receipt["persistent_writes"], 0)

    def test_matching_mock_is_not_independently_verified(self):
        seen = []
        def fake(url):
            seen.append(url)
            return upstream()
        receipt = inspect_public_prs([candidate()], verify_live=True, fetch=fake)
        self.assertEqual(seen, ["https://api.github.com/repos/python/cpython/pulls/42"])
        item = receipt["items"][0]
        self.assertEqual(item["source_check"], "SYNTHETIC_METADATA_MATCHED")
        self.assertFalse(receipt["live_checked"])
        self.assertFalse(item["fix_independently_reproduced"])
        self.assertFalse(item["license_verified"])
        self.assertFalse(item["approved"])
        self.assertEqual(len(item["comparison_sha256"]), 64)

    def test_wrong_base_owner_fails(self):
        result = inspect_public_prs([candidate()], verify_live=True,
                                   fetch=lambda _: upstream(repo="unapproved/repo"))
        self.assertEqual(result["items"][0]["source_check"], "SOURCE_MISMATCH")

    def test_unmerged_fails(self):
        result = inspect_public_prs([candidate()], verify_live=True,
                                   fetch=lambda _: upstream(merged=False))
        self.assertEqual(result["items"][0]["source_check"], "SOURCE_MISMATCH")

    def test_bad_merge_sha_fails(self):
        data = upstream()
        data["merge_commit_sha"] = "../repo"
        result = inspect_public_prs([candidate()], verify_live=True,
                                   fetch=lambda _: data)
        self.assertEqual(result["items"][0]["source_check"], "SOURCE_MISMATCH")

    def test_public_source_failure_is_not_pass(self):
        def unavailable(_):
            raise OSError("synthetic unavailable")
        result = inspect_public_prs([candidate()], verify_live=True,
                                   fetch=unavailable)
        self.assertEqual(result["items"][0]["source_check"], "SOURCE_UNAVAILABLE")

    def test_unapproved_source_is_blocked_before_fetch(self):
        calls = []
        with self.assertRaises(ReviewError):
            inspect_public_prs([candidate("unknown/private")],
                               verify_live=True, fetch=lambda x: calls.append(x))
        self.assertEqual(calls, [])

    def test_duplicate_and_bad_snapshot_denied(self):
        with self.assertRaises(ReviewError):
            inspect_public_prs([candidate(), candidate()])
        record = candidate()
        record["evidence_sha256"] = "unverified"
        with self.assertRaises(ReviewError):
            inspect_public_prs([record])

    def test_bounded_review(self):
        with self.assertRaises(ReviewError):
            inspect_public_prs([candidate(number=n) for n in range(1, 42)])


if __name__ == "__main__":
    unittest.main()
