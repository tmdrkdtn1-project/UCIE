"""Synthetic UCIE first-rule release preflight tests: no network or keys."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import json
import unittest

from ucie_public.owner_release import JOBS, REPO, MODE, SCOPE
from ucie_public.owner_risk_preflight_v01 import (
    NO_GO, READY, inspect_owner_release_preflight, main,
)
from ucie_public.policy import PolicyError

HEAD = "a" * 40
ROOT = Path("D:/UCIE")
RUN_ID = 444555666


def sample_evidence():
    return {
        "repository": REPO,
        "event": "push", "branch": "main",
        "job_names": sorted(JOBS),
        "independent_human_qa": False,
        "legal_license_signoff": False,
        "head_sha": HEAD,
        "run_url": f"https://github.com/{REPO}/actions/runs/{RUN_ID}",
    }


class OwnerRiskPreflightTests(unittest.TestCase):
    def test_disallows_wrong_root_and_never_calls_git_or_network(self):
        with (patch("ucie_public.owner_risk_preflight_v01._local_clean_sha") as git,
              patch("ucie_public.owner_risk_preflight_v01.validate_live_automated_qa") as ci):
            r = inspect_owner_release_preflight(Path("D:/UNRELATED"), run_id=RUN_ID)
            self.assertEqual(r["status"], NO_GO)
            self.assertEqual(r["reason_codes"], ["NOT_EXACT_UCIE_OWNER_ROOT"])
            git.assert_not_called()
            ci.assert_not_called()

    def test_dirty_owner_checkout_blocks_before_calling_ci(self):
        with (patch("ucie_public.owner_risk_preflight_v01._local_clean_sha",
                    side_effect=PolicyError("dirty")),
              patch("ucie_public.owner_risk_preflight_v01.validate_live_automated_qa") as ci):
            r = inspect_owner_release_preflight(ROOT, run_id=RUN_ID)
            self.assertEqual(r["status"], NO_GO)
            self.assertIn("OWNER_MAIN_NOT_CLEAN_OR_UNATTESTED", r["reason_codes"])
            ci.assert_not_called()
            self.assertFalse(r["owner_signature_created"])

    def test_missing_main_push_id_blocks_even_with_clean_checkout(self):
        with (patch("ucie_public.owner_risk_preflight_v01._local_clean_sha",
                    return_value=HEAD),
              patch("ucie_public.owner_risk_preflight_v01.validate_live_automated_qa") as ci):
            r = inspect_owner_release_preflight(ROOT)
            self.assertTrue(r["clean_owner_main_verified"])
            self.assertEqual(r["status"], NO_GO)
            self.assertIn("EXACT_MAIN_PUSH_CI_RUN_ID_REQUIRED", r["reason_codes"])
            ci.assert_not_called()

    def test_fake_or_failed_public_ci_rejected(self):
        with (patch("ucie_public.owner_risk_preflight_v01._local_clean_sha",
                    return_value=HEAD),
              patch("ucie_public.owner_risk_preflight_v01.validate_live_automated_qa",
                    side_effect=PolicyError("not a main push"))):
            r = inspect_owner_release_preflight(ROOT, run_id=RUN_ID)
            self.assertEqual(r["reason_codes"], ["MAIN_PUSH_CI_NOT_VERIFIED"])
            self.assertFalse(r["ci_four_jobs_verified"])

    def test_head_sha_must_match_exact_owner_main(self):
        ev = sample_evidence()
        ev["head_sha"] = "b" * 40
        with (patch("ucie_public.owner_risk_preflight_v01._local_clean_sha",
                    return_value=HEAD),
              patch("ucie_public.owner_risk_preflight_v01.validate_live_automated_qa",
                    return_value=ev)):
            r = inspect_owner_release_preflight(ROOT, run_id=RUN_ID)
            self.assertIn("CI_COMMIT_DOES_NOT_MATCH_OWNER_CHECKOUT", r["reason_codes"])

    def test_drifted_evidence_does_not_pass(self):
        ev = sample_evidence()
        ev["legal_license_signoff"] = True
        with (patch("ucie_public.owner_risk_preflight_v01._local_clean_sha",
                    return_value=HEAD),
              patch("ucie_public.owner_risk_preflight_v01.validate_live_automated_qa",
                    return_value=ev)):
            r = inspect_owner_release_preflight(ROOT, run_id=RUN_ID)
            self.assertEqual(r["status"], NO_GO)
            self.assertEqual(r["reason_codes"], ["CI_EVIDENCE_CONTRACT_DRIFT"])

    def test_valid_automated_qa_is_only_ready_for_manual_signing(self):
        with (patch("ucie_public.owner_risk_preflight_v01._local_clean_sha",
                    return_value=HEAD),
              patch("ucie_public.owner_risk_preflight_v01.validate_live_automated_qa",
                    return_value=sample_evidence())):
            r = inspect_owner_release_preflight(ROOT, run_id=RUN_ID)
        self.assertEqual(r["status"], READY)
        self.assertEqual(r["reason_codes"], [])
        self.assertEqual(r["scope"], SCOPE)
        self.assertEqual(r["approval_mode"], MODE)
        self.assertTrue(r["ci_four_jobs_verified"])
        self.assertTrue(r["ci_push_main_verified"])
        self.assertEqual(r["source_commit_sha"], HEAD)
        for field in ("owner_explicit_authorization_recorded",
                      "independent_human_qa_attested",
                      "legal_license_signoff_attested",
                      "owner_production_key_read",
                      "owner_signature_created",
                      "package_created",
                      "package_distributed",
                      "automatic_rule_promotion",
                      "task_scheduler_mutated",
                      "operating_database_modified"):
            self.assertIs(r[field], False)

    def test_cli_missing_ci_returns_nonzero_machine_readable_no_go(self):
        with (patch("ucie_public.owner_risk_preflight_v01._local_clean_sha",
                    return_value=HEAD),
              redirect_stdout(StringIO()) as out):
            code = main(["--ucie-root", str(ROOT)])
        self.assertEqual(code, 2)
        result = json.loads(out.getvalue())
        self.assertEqual(result["status"], NO_GO)
        self.assertEqual(result["source_commit_sha"], HEAD)
        self.assertFalse(result["package_created"])


if __name__ == "__main__":
    unittest.main()
