"""Regression: browsing unverified public evidence must not import vendor signing.

Signed verification remains strict and cannot become an unsigned fallback.
Public candidate metadata/approval gates must be identical for CLI and browser.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

from ucie_public.policy import PolicyError
from ucie_miner.verification_handoff import _checked_handoff as pure_handoff
from ucie_miner.automated_candidate_qa import _checked_handoff as qa_handoff


class PureReadOnlyPublicCandidateGateTests(unittest.TestCase):
    def test_single_shared_strict_candidate_handoff_validation(self):
        self.assertIs(pure_handoff, qa_handoff)

    def test_missing_review_ledger_is_not_approval(self):
        read = {
            "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
            "status": "REVIEW_LEDGER_ABSENT_NO_GO",
            "auto_promoted": False,
            "production_approved": False,
            "deploy_allowed": False,
            "tasks": [],
        }
        self.assertEqual(pure_handoff(read), (False, []))
        for key in ("auto_promoted", "production_approved", "deploy_allowed"):
            bad = dict(read, **{key: True})
            with self.assertRaises(PolicyError):
                pure_handoff(bad)
        bad = dict(read, tasks=[{"approval": True}])
        with self.assertRaises(PolicyError):
            pure_handoff(bad)

    def test_linked_review_cannot_be_unpinned(self):
        data = {
            "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
            "status": "LINKED_UNVERIFIED_NO_GO",
            "auto_promoted": False, "production_approved": False,
            "deploy_allowed": False,
            "source_revisions": 1, "linked_revisions": 1,
            "pending_source_revisions": 0,
            "tasks": [{
                "status": "UNVERIFIED_CANDIDATE_ONLY",
                "approval": False, "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
                "candidate_id_sha256": "a"*64, "evidence_sha256": "b"*64,
                "stage6_candidate": {
                    "status": "UNVERIFIED_CANDIDATE_ONLY",
                    "required_gates": {"human_review": "NOT_VERIFIED"},
                    "executable_command": None,
                    "rule_code": "NOT_ON_APPROVED_UCIE_PUBLIC_SOURCE_LIST",
                },
            }],
        }
        with self.assertRaises(PolicyError):
            pure_handoff(data)

    def test_clean_child_public_ui_import_without_crypto_and_signed_no_bypass(self):
        root = Path(__file__).resolve().parents[1]
        code = (
            "import sys,builtins,json\n"
            "sys.path.insert(0,sys.argv[1])\n"
            "original=builtins.__import__\n"
            "def block(name,*a,**kw):\n"
            " if name=='cryptography' or name.startswith('cryptography.'):\n"
            "  raise ModuleNotFoundError('optional signed vendor absent',name='cryptography')\n"
            " return original(name,*a,**kw)\n"
            "builtins.__import__=block\n"
            "from ucie_miner.library_search import search_linked_public_candidates\n"
            "from ucie_miner.local_v1_app_v01 import make_handler\n"
            "try:\n"
            " import ucie_public.mixed_release\n"
            "except ModuleNotFoundError as exc:\n"
            " print(json.dumps({'read_only_import':True,"
            "'signed_verifier_missing_vendor_denied':exc.name=='cryptography',"
            "'customer_distribution_authorized':False}))\n"
            "else:\n"
            " raise RuntimeError('signed verifier bypassed vendor dependency')\n"
        )
        proc = subprocess.run(
            [sys.executable, "-I", "-B", "-c", code, str(root / "src")],
            cwd=root, env={"PYTHONDONTWRITEBYTECODE":"1"},
            capture_output=True, text=True, timeout=15,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr[:500])
        out = json.loads(proc.stdout)
        self.assertTrue(out["read_only_import"])
        self.assertTrue(out["signed_verifier_missing_vendor_denied"])
        self.assertFalse(out["customer_distribution_authorized"])


if __name__ == "__main__":
    unittest.main()
