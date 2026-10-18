"""One-shot CI: real UCIE GitHub QA GETs with inert synthetic Stage12 inputs.

No owner key/real user database, unsafe upstream code, scheduler or writes.
The only mocked input is a synthetic candidate queue; all historical CI
records are fetched and checked LIVE from the public UCIE repository.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys
from unittest.mock import patch

# File-mode execution does not inherit unittest discover's PYTHONPATH setup.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from test_ucie_automated_candidate_qa import RUN_ID, handoff
from ucie_miner.automated_candidate_qa import verify_public_candidate_qa


def main() -> None:
    queue = handoff()
    queue["tasks"].append({
        "candidate_id_sha256": "f" * 64,
        "evidence_sha256": "e" * 64,
        "source": "git/git", "reference": "pr:9999:" + "a" * 40,
        "status": "UNVERIFIED_CANDIDATE_ONLY",
        "approval": False,
        "blocking_reasons": ["VERIFICATION_NOT_PERFORMED",
                             "NO_EXACT_PINNED_RULE_TEMPLATE"],
        "stage6_candidate": None,
    })
    queue["source_revisions"] += 1
    queue["linked_revisions"] += 1
    with patch(
        "ucie_miner.automated_candidate_qa.prepare_verification_handoff",
        return_value=queue,
    ):
        report = verify_public_candidate_qa(".", run_id=RUN_ID)
    if (report["status"] != "SAFE_TEMPLATE_QA_REVIEW_READY_NO_NEW_APPROVAL"
            or report["safe_templates_observed"] != 4
            or report["unknown_or_unmatched"] != 1
            or report["new_rules_approved"] != 0
            or report["auto_promoted"] is not False
            or report["unsafe_external_code_executed"] is not False
            or report["persistent_writes"] != 0):
        raise RuntimeError("live candidate-safe QA contract not satisfied")
    print("UCIE_LIVE_CANDIDATE_QA=" + json.dumps({
        "schema": "UCIE_PUBLIC_AUTOMATED_CANDIDATE_QA_LIVE_PROBE_V1",
        "run_id": RUN_ID,
        "synthetic_known_candidates": 4,
        "synthetic_unknown_candidate": 1,
        "verified_safe_qa_profiles": report["safe_templates_observed"],
        "unverified_unknown_candidates": report["unknown_or_unmatched"],
        "real_public_github_ci_checked": True,
        "staged_owner_candidate_approved": False,
        "new_rules_approved": 0,
        "automatic_promotion": False,
        "external_code_executed": False,
        "persistent_writes": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
