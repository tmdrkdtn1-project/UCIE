"""Offline-only Stage 5 pattern grouping tests."""
from pathlib import Path
import hashlib
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.patterns import PatternError, group_patterns


def row(n, canonical=42, pattern="API_CONTRACT", source="python/cpython"):
    return {
        "source": source, "pr_number": n,
        "canonical_pr_number": canonical, "pattern_code": pattern,
        "evidence_sha256": hashlib.sha256(str(n).encode()).hexdigest(),
        "status": "UNVERIFIED_CANDIDATE_ONLY",
    }


class PatternGroupTests(unittest.TestCase):
    def test_backport_grouped_without_promotion(self):
        result = group_patterns([row(42), row(49)])
        self.assertEqual(result["pr_count"], 2)
        self.assertEqual(result["family_count"], 1)
        self.assertEqual(result["families"][0]["pr_numbers"], [42, 49])
        self.assertFalse(result["production_approved"])
        self.assertEqual(result["persistent_writes"], 0)

    def test_reordered_input_is_deterministic(self):
        self.assertEqual(group_patterns([row(49), row(42)]),
                         group_patterns([row(42), row(49)]))

    def test_missing_canonical_rejected(self):
        with self.assertRaises(PatternError):
            group_patterns([row(49)])

    def test_conflicting_family_rejected(self):
        with self.assertRaises(PatternError):
            group_patterns([row(42), row(49, pattern="RESOURCE_CLEANUP")])

    def test_duplicate_identity_rejected(self):
        with self.assertRaises(PatternError):
            group_patterns([row(42), row(42)])

    def test_unknown_source_rejected(self):
        with self.assertRaises(PatternError):
            group_patterns([row(42, source="other/private")])

    def test_status_cannot_claim_verified(self):
        item = row(42)
        item["status"] = "VERIFIED"
        with self.assertRaises(PatternError):
            group_patterns([item])

    def test_invalid_digest_rejected(self):
        item = row(42)
        item["evidence_sha256"] = "not-a-sha"
        with self.assertRaises(PatternError):
            group_patterns([item])


if __name__ == "__main__":
    unittest.main()
