"""No-side-effect Stage 7/8 readiness tests using synthetic receipts."""
from pathlib import Path
import hashlib
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ucie_miner.patterns import PatternError, group_patterns
from ucie_miner.rule_candidates import approval_gate, candidate_rulepack
from ucie_miner.provenance_review import inspect_public_prs
from ucie_miner.preapproval import preapproval_readiness


def fixtures():
    row = {"source": "python/cpython", "pr_number": 42,
           "canonical_pr_number": 42, "pattern_code": "API_CONTRACT",
           "evidence_sha256": hashlib.sha256(b"candidate").hexdigest(),
           "status": "UNVERIFIED_CANDIDATE_ONLY"}
    patterns = group_patterns([row])
    pack = candidate_rulepack(patterns)
    chain = {
        "schema": "UCIE_STAGE4_7_INTEGRATION_PREVIEW_V1",
        "database_writes": 0, "production_approved": False,
        "miner_count": 1, "rulepack_preview": pack,
        "pattern_preview": patterns, "approval_gate": approval_gate(pack),
    }
    miner_row = {
        "source": "python/cpython", "pr_number": 42,
        "public_url": "https://github.com/python/cpython/pull/42",
        "merged_at": "2026-10-01T00:00:00Z",
        "evidence_sha256": row["evidence_sha256"],
    }
    return chain, inspect_public_prs([miner_row])


class ReadinessTests(unittest.TestCase):
    def test_default_no_go(self):
        chain, audit = fixtures()
        result = preapproval_readiness(chain, audit)
        self.assertEqual(result["status"], "NO_GO")
        self.assertIn("PUBLIC_METADATA_RECHECK_REQUIRED", result["pending"])
        self.assertFalse(result["rulepack_signed"])
        self.assertFalse(result["scheduler_registered"])
        self.assertFalse(result["production_approved"])

    def test_forged_live_pass_cannot_authorize(self):
        chain, audit = fixtures()
        audit["live_checked"] = True
        audit["items"][0]["source_check"] = "PUBLIC_API_METADATA_MATCHED"
        result = preapproval_readiness(chain, audit)
        self.assertEqual(result["status"], "NO_GO")
        self.assertNotIn("PUBLIC_METADATA_RECHECK_REQUIRED", result["pending"])
        self.assertIn("OWNER_APPROVAL_AND_AUTHORIZED_SIGNING_REQUIRED",
                      result["pending"])

    def test_missing_coverage_fails_closed(self):
        chain, audit = fixtures()
        audit["items"].clear()
        audit["count"] = 0
        with self.assertRaises(PatternError):
            preapproval_readiness(chain, audit)

    def test_forged_rulepack_signature_rejected(self):
        chain, audit = fixtures()
        chain["rulepack_preview"]["signed"] = True
        with self.assertRaises(PatternError):
            preapproval_readiness(chain, audit)

    def test_untrusted_approval_rejected(self):
        chain, audit = fixtures()
        audit["items"][0]["approved"] = True
        with self.assertRaises(PatternError):
            preapproval_readiness(chain, audit)


if __name__ == "__main__":
    unittest.main()
