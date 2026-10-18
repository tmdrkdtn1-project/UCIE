"""No-side-effect candidate automation with exact safe public CI recipes only."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from ucie_miner.automated_candidate_qa import (
    SCHEMA, SAFE_STEPS, assess_safe_candidate_qa,
    verify_public_candidate_qa,
)
from ucie_miner.__main__ import main as miner_main
from ucie_miner.static_rule_bridge import SOURCE_BINDINGS
from ucie_public.owner_release import JOBS
from ucie_public.policy import PolicyError
from ucie_public.mixed_release import (
    ELIGIBLE, RULE_ORDER, FOURTH_CI,
)
from ucie_public.selected_release import EXPECTED_SECOND_CI, EXPECTED_THIRD_CI


RUN_ID = 39112420369
SHA = "b334d56b9c4ec615450fbb5aee7e2eb1b81ac8ae"


def handoff():
    tasks = []
    for i, code in enumerate(RULE_ORDER):
        source, number = SOURCE_BINDINGS[code]
        sha = ELIGIBLE[code][0]["upstream_merge_sha"]
        tasks.append({
            "candidate_id_sha256": f"{i + 1:064x}",
            "evidence_sha256": f"{i + 10:064x}",
            "source": source, "reference": f"pr:{number}:{sha}",
            "status": "UNVERIFIED_CANDIDATE_ONLY",
            "approval": False,
            "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
            "stage6_candidate": {
                "rule_code": code, "source": source,
                "canonical_pr_number": number,
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
        "source_revisions": len(tasks), "linked_revisions": len(tasks),
        "pending_source_revisions": 0, "tasks": tasks,
        "auto_promoted": False, "production_approved": False,
        "deploy_allowed": False,
    }


def fake_ci():
    main = {
        "schema": "UCIE_OWNER_RELEASE_AUTOMATED_QA_EVIDENCE_V1",
        "repository": "tmdrkdtn1-project/UCIE",
        "run_id": RUN_ID,
        "head_sha": SHA,
        "event": "push", "branch": "main", "conclusion": "success",
        "independent_human_qa": False, "legal_license_signoff": False,
    }
    jobs = []
    for name in sorted(JOBS):
        steps = []
        for step_name, required in SAFE_STEPS.values():
            if name in required:
                steps.append({
                    "name": step_name, "status": "completed",
                    "conclusion": "success",
                })
        jobs.append({
            "name": name, "status": "completed",
            "conclusion": "success", "run_id": RUN_ID,
            "steps": steps,
        })
    return main, {"total_count": 4, "jobs": jobs}


def pinned():
    return {
        "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO": None,
        "PS_RESOLVE_PATH_DOT_PREFIX": EXPECTED_SECOND_CI,
        "PS_FUZZY_GET_COMMAND_DUPLICATES": EXPECTED_THIRD_CI,
        "PY_SCANDIR_SHARED_ITERATOR_RACE": FOURTH_CI,
    }


class CandidateSafeAutomatedQATests(unittest.TestCase):
    def assess(self, queue=None, ci=None, jobs=None, proof=None):
        if ci is None or jobs is None:
            good_ci, good_jobs = fake_ci()
            ci = good_ci if ci is None else ci
            jobs = good_jobs if jobs is None else jobs
        return assess_safe_candidate_qa(
            handoff() if queue is None else queue,
            ci, jobs, pinned() if proof is None else proof)

    def test_all_four_real_safe_profiles_reconciled_but_never_approved(self):
        result = self.assess()
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(
            result["status"],
            "SAFE_TEMPLATE_QA_REVIEW_READY_NO_NEW_APPROVAL")
        self.assertEqual(result["safe_templates_observed"], 4)
        self.assertEqual(result["unknown_or_unmatched"], 0)
        self.assertEqual(result["new_rules_approved"], 0)
        self.assertEqual(len(result["results"]), 4)
        self.assertFalse(result["auto_promoted"])
        self.assertFalse(result["owner_signed"])
        self.assertFalse(result["production_approved"])
        self.assertFalse(result["unsafe_external_code_executed"])
        self.assertEqual(result["persistent_writes"], 0)
        for entry in result["results"]:
            self.assertEqual(entry["status"],
                             "PINNED_SAFE_QA_OBSERVED_REVIEW_REQUIRED")
            self.assertTrue(entry["safe_runtime_template_passed"])
            self.assertFalse(entry["new_candidate_independent_fix_verified"])
            self.assertFalse(entry["full_release_version_coverage_verified"])
            self.assertFalse(entry["owner_approved_new_candidate"])

    def test_unknown_fifth_candidate_stays_unsupported_without_execution(self):
        queue = handoff()
        queue["tasks"].append({
            "candidate_id_sha256": "f" * 64,
            "evidence_sha256": "e" * 64,
            "status": "UNVERIFIED_CANDIDATE_ONLY",
            "approval": False, "source": "git/git",
            "reference": "pr:9999:" + "a" * 40,
            "blocking_reasons": ["VERIFICATION_NOT_PERFORMED",
                                 "NO_EXACT_PINNED_RULE_TEMPLATE"],
            "stage6_candidate": None,
        })
        queue["source_revisions"] += 1
        queue["linked_revisions"] += 1
        result = self.assess(queue=queue)
        self.assertEqual(result["candidate_count"], 5)
        self.assertEqual(result["safe_templates_observed"], 4)
        self.assertEqual(result["unknown_or_unmatched"], 1)
        self.assertEqual(result["new_rules_approved"], 0)

    def test_unlinked_candidate_ledger_prevents_any_qa_ready_status(self):
        for state in ("REVIEW_LEDGER_ABSENT_NO_GO",
                      "SOURCE_REVISIONS_PENDING_NO_GO"):
            q = handoff()
            q["status"] = state
            q["pending_source_revisions"] = 1
            if state == "REVIEW_LEDGER_ABSENT_NO_GO":
                q["tasks"] = []
            out = self.assess(queue=q)
            self.assertEqual(out["status"], "CANDIDATE_LEDGER_INCOMPLETE_NO_GO")
            self.assertEqual(out["safe_templates_observed"], 0)
            self.assertEqual(out["new_rules_approved"], 0)

    def test_duplicate_known_revision_is_never_reported_verified(self):
        q = handoff()
        q["tasks"].append(deepcopy(q["tasks"][-1]))
        q["tasks"][-1]["candidate_id_sha256"] = "e" * 64
        q["tasks"][-1]["evidence_sha256"] = "d" * 64
        q["source_revisions"] += 1
        q["linked_revisions"] += 1
        out = self.assess(queue=q)
        self.assertEqual(out["safe_templates_observed"], 3)
        self.assertEqual(out["ambiguous_revisions"], 2)
        self.assertEqual(out["results"][-1]["status"],
                         "AMBIGUOUS_SOURCE_REVISION_NO_GO")

    def test_forged_source_identity_and_candidate_gate_rejected(self):
        for kind in ("source", "merge", "approval", "execute",
                     "gate", "fingerprint", "auto_promoted", "count"):
            q = handoff()
            last = q["tasks"][-1]
            if kind == "source":
                last["source"] = "git/git"
            elif kind == "merge":
                last["reference"] = "pr:153462:" + "a" * 40
            elif kind == "approval":
                last["approval"] = True
            elif kind == "execute":
                last["stage6_candidate"]["executable_command"] = "Invoke-Expression"
            elif kind == "gate":
                last["stage6_candidate"]["required_gates"]["human_approved"] = "PASS"
            elif kind == "fingerprint":
                last["candidate_id_sha256"] = q["tasks"][0]["candidate_id_sha256"]
            elif kind == "auto_promoted":
                q["auto_promoted"] = True
            else:
                q["pending_source_revisions"] = 10
            with self.subTest(kind=kind), self.assertRaises(PolicyError):
                self.assess(queue=q)

    def test_failed_missing_or_altered_ci_steps_never_pass(self):
        for kind in ("windows", "linux", "job_failed", "wrong_run",
                     "count", "evidence", "no_human_review"):
            main, matrix = fake_ci()
            proof = pinned()
            if kind == "windows":
                selected = next(x for x in matrix["jobs"]
                                if "windows-latest / Python 3.15" in x["name"])
                selected["steps"] = []
            elif kind == "linux":
                selected = next(x for x in matrix["jobs"]
                                if "ubuntu-latest / Python 3.15" in x["name"])
                selected["steps"] = []
            elif kind == "job_failed":
                matrix["jobs"][0]["conclusion"] = "failure"
            elif kind == "wrong_run":
                matrix["jobs"][0]["run_id"] = RUN_ID - 1
            elif kind == "count":
                matrix["total_count"] = 3
            elif kind == "evidence":
                proof["PY_SCANDIR_SHARED_ITERATOR_RACE"] = None
            else:
                main["independent_human_qa"] = True
            with self.subTest(kind=kind), self.assertRaises(PolicyError):
                self.assess(ci=main, jobs=matrix, proof=proof)

    def test_no_ledger_means_no_public_network_get(self):
        q = handoff()
        q["status"] = "REVIEW_LEDGER_ABSENT_NO_GO"
        q["tasks"] = []
        with (
            patch("ucie_miner.automated_candidate_qa.prepare_verification_handoff",
                  return_value=q),
            patch("ucie_miner.automated_candidate_qa.validate_live_automated_qa"
                  ) as github,
        ):
            result = verify_public_candidate_qa(".", run_id=RUN_ID)
            github.assert_not_called()
            self.assertEqual(result["status"],
                             "CANDIDATE_LEDGER_INCOMPLETE_NO_GO")

    def test_cli_requires_explicit_live_opt_in(self):
        with patch("ucie_miner.__main__.verify_public_candidate_qa") as called:
            self.assertEqual(miner_main(
                ["verify-public-candidate-qa", "--run-id", str(RUN_ID)]), 2)
            called.assert_not_called()


if __name__ == "__main__":
    unittest.main()
