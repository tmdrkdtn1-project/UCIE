"""UCIE B4 affected-only source revision review contract tests."""
import unittest

from ucie_miner.b4_transfer_boundary_v01 import build_transfer_hypothesis
from ucie_miner.b4_revision_impact_v01 import (
    RevisionImpactError, propose_affected_retests,
)


def change(source, *, observed_sha=None, observed_tag=None, verified=False):
    return {
        "source_id": source["source_id"],
        "expected_sha256": source["sha256"],
        "observed_sha256": observed_sha if observed_sha is not None else source["sha256"],
        "observed_tag": observed_tag if observed_tag is not None else source["tag"],
        "independently_verified": verified,
    }


class TestB4AffectedOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_a, cls.source_b = build_transfer_hypothesis()["parent_source_refs"]

    def test_no_change_no_retest(self):
        out = propose_affected_retests([change(self.source_a)])
        self.assertEqual(out["retests_proposed"], 0)
        self.assertEqual(out["unchanged_sources"], [self.source_a["source_id"]])
        self.assertEqual(out["affected_sources"], [])

    def test_one_changed_source_only(self):
        out = propose_affected_retests([
            change(self.source_a, observed_sha="a" * 64)])
        self.assertEqual(out["retests_proposed"], 1)
        self.assertEqual([r["source_id"] for r in out["affected_sources"]],
                         [self.source_a["source_id"]])
        self.assertEqual(len(out["affected_sources"][0]["dependent_ids"]), 2)
        self.assertFalse(out["revision_claims_authenticated"])

    def test_tag_changed_alone_flags_review(self):
        out = propose_affected_retests([change(self.source_a, observed_tag="next-version")])
        self.assertEqual(out["retests_proposed"], 1)

    def test_changed_and_unchanged_mixed(self):
        out = propose_affected_retests([
            change(self.source_b),
            change(self.source_a, observed_sha="b" * 64),
        ])
        self.assertEqual(out["retests_proposed"], 1)
        self.assertEqual(out["unchanged_sources"], [self.source_b["source_id"]])

    def test_independently_verified_flag_is_not_approval(self):
        out = propose_affected_retests([
            change(self.source_a, observed_sha="a" * 64, verified=True)])
        self.assertTrue(out["affected_sources"][0]["independently_verified"])
        for key in ("owner_approved", "rights_approved", "export_allowed", "auto_promoted"):
            self.assertIs(out[key], False)
        self.assertEqual(out["test_execution"], "NOT_RUN")

    def test_deterministic(self):
        changes = [change(self.source_a, observed_sha="c" * 64),
                   change(self.source_b, observed_tag="v9")]
        self.assertEqual(propose_affected_retests(changes),
                         propose_affected_retests(list(reversed(changes))))

    def test_wrong_parent_hash_rejects(self):
        item = change(self.source_a)
        item["expected_sha256"] = "a" * 64
        with self.assertRaisesRegex(RevisionImpactError, "PARENT_SHA_MISMATCH"):
            propose_affected_retests([item])

    def test_unknown_source_rejects(self):
        item = change(self.source_a)
        item["source_id"] = "doc:unapproved/vendor"
        with self.assertRaisesRegex(RevisionImpactError, "UNKNOWN_OR_DUPLICATE_SOURCE"):
            propose_affected_retests([item])

    def test_duplicate_source_rejects(self):
        with self.assertRaisesRegex(RevisionImpactError, "UNKNOWN_OR_DUPLICATE_SOURCE"):
            propose_affected_retests([change(self.source_a), change(self.source_a)])

    def test_untrusted_extra_fields_reject(self):
        item = change(self.source_a)
        item["auto_approve"] = True
        with self.assertRaisesRegex(RevisionImpactError, "INVALID_CHANGE_SHAPE"):
            propose_affected_retests([item])

    def test_invalid_digest_and_verification_reject(self):
        item = change(self.source_a)
        item["observed_sha256"] = "Z" * 64
        with self.assertRaisesRegex(RevisionImpactError, "BAD_OBSERVED_SHA"):
            propose_affected_retests([item])
        item = change(self.source_a)
        item["independently_verified"] = 1
        with self.assertRaisesRegex(RevisionImpactError, "INVALID_VERIFICATION_FLAG"):
            propose_affected_retests([item])


if __name__ == "__main__":
    unittest.main()
