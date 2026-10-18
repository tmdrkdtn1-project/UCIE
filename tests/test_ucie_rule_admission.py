"""Synthetic-only candidate/owner-signed rule reconciliation regression tests."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_ucie_owner_risk_release import RUN, SHA, fake_api
from test_ucie_multi_owner_release import fake_second
from ucie_public.multi_owner_release import (
    CONFIRM, RISK, SECOND_RISK, publish_two_rule_owner_release,
)
from ucie_public.rulepack import generate_keys
from ucie_public.policy import PolicyError
from ucie_public.rule_admission import reconcile_existing_signed_rules


PINS = [
    ("python/cpython", 159014,
     "91248026c8a41910098032dd23f9a05ad2d9b513",
     "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO"),
    ("PowerShell/PowerShell", 28087,
     "373f6a7b7972a0a4b73bfd9737a0d768d28b347e",
     "PS_RESOLVE_PATH_DOT_PREFIX"),
]


def staged():
    tasks = []
    for index, (source, pr, sha, code) in enumerate(PINS):
        tasks.append({
            "candidate_id_sha256": format(index + 1, "064x"),
            "evidence_sha256": format(index + 15, "064x"),
            "source": source, "reference": f"pr:{pr}:{sha}",
            "status": "UNVERIFIED_CANDIDATE_ONLY",
            "approval": False, "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
            "stage6_candidate": {
                "source": source, "canonical_pr_number": pr,
                "rule_code": code, "status": "UNVERIFIED_CANDIDATE_ONLY",
                "executable_command": None,
                "required_gates": {"source_authenticated": "NOT_VERIFIED",
                                   "human_approved": "NOT_VERIFIED"},
            },
        })
    return {
        "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
        "status": "LINKED_UNVERIFIED_NO_GO", "tasks": tasks,
        "pending_source_revisions": 0, "auto_promoted": False,
        "production_approved": False, "deploy_allowed": False,
    }


class SignedCandidateAdmissionTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)
        (self.root / "build").mkdir()
        private, self.trust = generate_keys(
            self.root / "test_key_only", purpose="production")
        self.pack = self.root / "build" / "synthetic-owner.zip"
        main, jobs = fake_api()
        second, sjobs = fake_second()
        with (
            patch("ucie_public.multi_owner_release._local_clean_sha",
                  return_value=SHA),
            patch("ucie_public.owner_release._public_json",
                  side_effect=[main, jobs]),
            patch("ucie_public.multi_owner_release._public_json",
                  side_effect=[second, sjobs]),
        ):
            publish_two_rule_owner_release(
                self.root, private, self.pack,
                run_id=RUN, serial=7, confirmation=CONFIRM,
                risk_acceptance=RISK,
                second_risk_acceptance=SECOND_RISK)

    def evaluate(self, report):
        with patch("ucie_miner.verification_handoff.prepare_verification_handoff",
                   return_value=report):
            return reconcile_existing_signed_rules(
                self.root, self.pack, self.trust, min_serial=7)

    def test_both_existing_signed_rules_match_without_new_approval(self):
        result = self.evaluate(staged())
        self.assertEqual(result["matched_existing_rules"], 2)
        self.assertEqual(result["previously_signed_rule_count"], 2)
        self.assertEqual(result["new_rules_approved"], 0)
        self.assertFalse(result["production_approved_for_new_candidates"])
        self.assertFalse(result["deploy_allowed"])
        self.assertFalse(result["auto_promoted"])
        self.assertEqual(result["persistent_writes"], 0)
        self.assertTrue(all(x["staged_match"] == "SINGLE_SOURCE_REVISION"
                            for x in result["results"]))
        self.assertTrue(all(not x["new_candidate_owner_approved"]
                            for x in result["results"]))

    def test_unlinked_or_stale_ledger_stays_no_go(self):
        for status in ("REVIEW_LEDGER_ABSENT_NO_GO",
                       "SOURCE_REVISIONS_PENDING_NO_GO"):
            r = staged()
            r["status"] = status
            result = self.evaluate(r)
            self.assertEqual(result["status"],
                             "CANDIDATE_LEDGER_INCOMPLETE_NO_GO")
            self.assertEqual(result["matched_existing_rules"], 0)
            self.assertEqual(result["new_rules_approved"], 0)

    def test_unsigned_other_rule_is_not_approved(self):
        r = staged()
        third = deepcopy(r["tasks"][1])
        third["candidate_id_sha256"] = "f" * 64
        third["reference"] = "pr:28042:bd8cb01a7d5b86129c45eaa14ab5830a63b1283f"
        third["stage6_candidate"]["rule_code"] = "PS_FUZZY_GET_COMMAND_DUPLICATES"
        third["stage6_candidate"]["canonical_pr_number"] = 28042
        r["tasks"].append(third)
        result = self.evaluate(r)
        self.assertEqual(result["matched_existing_rules"], 2)
        self.assertEqual(result["new_rules_approved"], 0)

    def test_ambiguous_revision_blocks_existing_match(self):
        r = staged()
        dup = deepcopy(r["tasks"][1])
        dup["candidate_id_sha256"] = "f" * 64
        dup["evidence_sha256"] = "e" * 64
        r["tasks"].append(dup)
        result = self.evaluate(r)
        self.assertEqual(result["matched_existing_rules"], 1)
        self.assertEqual(result["results"][1]["staged_match"],
                         "AMBIGUOUS_REVISIONS_NO_GO")

    def test_forged_candidate_approval_and_source_rejected(self):
        for change in ("approval", "no_gate", "merge", "source",
                       "executing", "fingerprint"):
            r = staged()
            row = r["tasks"][1]
            if change == "approval":
                row["approval"] = True
            elif change == "no_gate":
                row["stage6_candidate"]["required_gates"]["human_approved"] = "PASS"
            elif change == "merge":
                row["reference"] = "pr:28087:" + "f" * 40
            elif change == "source":
                row["stage6_candidate"]["source"] = "git/git"
            elif change == "executing":
                row["stage6_candidate"]["executable_command"] = "Invoke-Code"
            else:
                row["candidate_id_sha256"] = r["tasks"][0]["candidate_id_sha256"]
            with self.subTest(change=change), self.assertRaises(PolicyError):
                self.evaluate(r)

    def test_wrong_owner_trust_or_expired_serial_is_rejected(self):
        _, wrong = generate_keys(self.root / "other", purpose="production")
        with self.assertRaises(PolicyError):
            with patch("ucie_miner.verification_handoff.prepare_verification_handoff",
                       return_value=staged()):
                reconcile_existing_signed_rules(
                    self.root, self.pack, wrong, min_serial=7)
        with self.assertRaises(PolicyError):
            with patch("ucie_miner.verification_handoff.prepare_verification_handoff",
                       return_value=staged()):
                reconcile_existing_signed_rules(
                    self.root, self.pack, self.trust, min_serial=8)


if __name__ == "__main__":
    unittest.main()
