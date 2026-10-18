"""Stage12 public miner -> authenticated four-rule V2 owner-pack reconciliation.

All keys and DB contents are ephemeral synthetic test fixtures only.
No auto approval, private files, code execution, signing with owner PC or
automatic writing of candidate status.
"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_ucie_owner_risk_release import RUN, SHA, fake_api
from ucie_miner.static_rule_bridge import SOURCE_BINDINGS
from ucie_public.mixed_release import (
    CONFIRM, ELIGIBLE, EXPECTED_SECOND_CI, EXPECTED_THIRD_CI,
    FOURTH_CI, RULE_ORDER, publish_mixed_owner_release,
)
from ucie_public.rulepack import generate_keys
from ucie_public.policy import PolicyError
from ucie_public.rule_admission import reconcile_mixed_signed_candidates


def staged(rule_ids=RULE_ORDER):
    tasks = []
    for i, code in enumerate(rule_ids):
        source, pr = SOURCE_BINDINGS[code]
        merge = ELIGIBLE[code][0]["upstream_merge_sha"]
        tasks.append({
            "candidate_id_sha256": f"{i + 1:064x}",
            "evidence_sha256": f"{i + 10:064x}",
            "source": source,
            "reference": f"pr:{pr}:{merge}",
            "status": "UNVERIFIED_CANDIDATE_ONLY",
            "approval": False,
            "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
            "stage6_candidate": {
                "source": source,
                "canonical_pr_number": pr,
                "rule_code": code,
                "status": "UNVERIFIED_CANDIDATE_ONLY",
                "executable_command": None,
                "required_gates": {
                    "source_authenticated": "NOT_VERIFIED",
                    "human_approved": "NOT_VERIFIED",
                },
            },
        })
    return {
        "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
        "status": "LINKED_UNVERIFIED_NO_GO",
        "tasks": tasks,
        "source_revisions": len(tasks),
        "linked_revisions": len(tasks),
        "pending_source_revisions": 0,
        "auto_promoted": False,
        "production_approved": False,
        "deploy_allowed": False,
    }


class SignedMixedCandidatePipelineTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "build").mkdir()
        private, self.trust = generate_keys(
            self.root / "ephemeral-qa", purpose="production")
        self.pack = self.root / "build" / "owner-synthetic.zip"
        main, jobs = fake_api()
        with (
            patch("ucie_public.mixed_release._local_clean_sha",
                  return_value=SHA),
            patch("ucie_public.owner_release._public_json",
                  side_effect=[main, jobs]),
            patch("ucie_public.mixed_release._postfix_ci",
                  return_value=EXPECTED_SECOND_CI),
            patch("ucie_public.mixed_release._third_ci",
                  return_value=EXPECTED_THIRD_CI),
            patch("ucie_public.mixed_release._fourth_ci",
                  return_value=FOURTH_CI),
        ):
            publish_mixed_owner_release(
                self.root, private, self.pack,
                run_id=RUN, serial=4,
                rule_ids=list(RULE_ORDER),
                confirmation=CONFIRM,
                risk_acceptances={
                    code: ELIGIBLE[code][2] for code in RULE_ORDER
                },
            )

    def report(self, source):
        with patch(
            "ucie_miner.verification_handoff.prepare_verification_handoff",
            return_value=source,
        ):
            return reconcile_mixed_signed_candidates(
                self.root, self.pack, self.trust, min_serial=4)

    def test_four_existing_owner_rules_bind_without_new_candidate_approval(self):
        r = self.report(staged())
        self.assertEqual(r["status"],
                         "SIGNED_PACK_AND_LEDGER_RECONCILED_NO_NEW_APPROVAL")
        self.assertEqual(r["signed_rule_count"], 4)
        self.assertEqual(r["matched_signed_rule_revisions"], 4)
        self.assertEqual(r["owner_signature"], "VALID")
        self.assertEqual(r["signed_rule_ids"], list(RULE_ORDER))
        self.assertEqual(r["new_rules_approved"], 0)
        self.assertFalse(r["auto_promoted"])
        self.assertFalse(r["new_production_approval_granted"])
        self.assertFalse(r["automatic_deployment"])
        self.assertEqual(r["persistent_writes"], 0)
        self.assertTrue(all(
            row["miner_provenance"] == "EXACT_SINGLE_REVISION_UNVERIFIED"
            and not row["new_candidate_qa_passed"]
            and not row["new_candidate_owner_approved"]
            for row in r["results"]))

    def test_unknown_fifth_candidate_can_be_staged_but_never_approved(self):
        r = staged()
        r["tasks"].append({
            "candidate_id_sha256": "f" * 64,
            "evidence_sha256": "e" * 64,
            "source": "git/git", "reference": "pr:9999:" + "a" * 40,
            "status": "UNVERIFIED_CANDIDATE_ONLY",
            "approval": False,
            "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
            "stage6_candidate": None,
        })
        r["source_revisions"] += 1
        r["linked_revisions"] += 1
        output = self.report(r)
        self.assertEqual(output["matched_signed_rule_revisions"], 4)
        self.assertEqual(output["unmatched_unsigned_candidate_revisions"], 1)
        self.assertEqual(output["new_rules_approved"], 0)

    def test_missing_or_stale_review_queue_no_go_without_mutating_owner_pack(self):
        report = staged()
        for status in ("REVIEW_LEDGER_ABSENT_NO_GO",
                       "SOURCE_REVISIONS_PENDING_NO_GO"):
            r = deepcopy(report)
            r["status"] = status
            r["pending_source_revisions"] = 1
            result = self.report(r)
            self.assertEqual(result["status"],
                             "SIGNED_PACK_VALID_MINER_LEDGER_NO_GO")
            self.assertEqual(result["matched_signed_rule_revisions"], 0)
            self.assertEqual(result["signed_rule_count"], 4)
            self.assertEqual(result["new_rules_approved"], 0)

    def test_multiple_evidence_revisions_are_not_silently_approved(self):
        r = staged()
        duplicate = deepcopy(r["tasks"][-1])
        duplicate["candidate_id_sha256"] = "e" * 64
        duplicate["evidence_sha256"] = "d" * 64
        r["tasks"].append(duplicate)
        r["source_revisions"] += 1
        r["linked_revisions"] += 1
        result = self.report(r)
        self.assertEqual(result["matched_signed_rule_revisions"], 3)
        self.assertEqual(result["results"][-1]["miner_provenance"],
                         "DUPLICATE_REVISIONS_NO_GO")

    def test_forged_approval_or_source_metadata_rejected(self):
        for kind in ("approval", "source", "sha", "executable",
                     "promotion", "fingerprint", "fake_gate"):
            r = staged()
            row = r["tasks"][-1]
            if kind == "approval":
                row["approval"] = True
            elif kind == "source":
                row["source"] = "git/git"
            elif kind == "sha":
                row["reference"] = "pr:153462:" + "a" * 40
            elif kind == "executable":
                row["stage6_candidate"]["executable_command"] = "Invoke-Expression"
            elif kind == "promotion":
                r["auto_promoted"] = True
            elif kind == "fingerprint":
                row["candidate_id_sha256"] = r["tasks"][0]["candidate_id_sha256"]
            else:
                row["stage6_candidate"]["required_gates"]["human_approved"] = "PASS"
            with self.subTest(kind=kind), self.assertRaises(PolicyError):
                self.report(r)

    def test_old_serial_and_wrong_signer_cannot_be_swapped(self):
        _, other = generate_keys(
            self.root / "untrusted-signer", purpose="production")
        with patch(
            "ucie_miner.verification_handoff.prepare_verification_handoff",
            return_value=staged(),
        ), self.assertRaises(PolicyError):
            reconcile_mixed_signed_candidates(
                self.root, self.pack, other, min_serial=4)
        with patch(
            "ucie_miner.verification_handoff.prepare_verification_handoff",
            return_value=staged(),
        ), self.assertRaises(PolicyError):
            reconcile_mixed_signed_candidates(
                self.root, self.pack, self.trust, min_serial=5)


if __name__ == "__main__":
    unittest.main()
