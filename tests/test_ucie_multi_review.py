"""Synthetic-only two-rule signed review pack and inert receipt consumer tests.

No owner keys, actual production releases, external source or private input.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from ucie_public.policy import PolicyError
from ucie_public.rulepack import canonical_json, generate_keys, _private_key
from ucie_public.multi_review import (
    CONFIRM, RULES, publish_multi_review, verify_multi_review,
    scan_multi_review_receipt,
)


def scanner_receipt():
    codes = [
        ("PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO",
         "https://github.com/python/cpython/pull/159014",
         "Use Python -X disable-remote-debug (hyphens), not disable_remote_debug; confirm target interpreter setting"),
        ("PS_RESOLVE_PATH_DOT_PREFIX",
         "https://github.com/PowerShell/PowerShell/pull/28087",
         "Review dot-prefixed relative paths and use an anchored base-directory conversion if needed"),
    ]
    return {
        "schema": "UCIE_POWERSHELL_STATIC_CANDIDATES_V1",
        "source_sha256": hashlib.sha256(b"UCIE synthetic source only").hexdigest(),
        "findings": [
            {"pattern_code": code, "line": i + 1, "column": 1,
             "confidence": "STATIC_HEURISTIC_REVIEW_REQUIRED",
             "safe_fix_guidance": guidance,
             "public_evidence": url, "runtime_bug_reproduced": False}
            for i, (code, url, guidance) in enumerate(codes)
        ],
        "finding_count": 2, "parser_executed_supplied_code": False,
        "confidence": "HUMAN_REVIEW_REQUIRED", "approved_rules": 0,
        "source_files_read": 0, "persistent_writes": 0,
        "production_approved": False,
    }


class TwoRuleReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "build").mkdir()
        self.private, self.public = generate_keys(self.root / "keys", purpose="prevention")
        self.pack = self.root / "build" / "two-rule-review.zip"

    def create(self, **kw):
        args = dict(serial=9, confirmation=CONFIRM)
        args.update(kw)
        return publish_multi_review(self.root, self.private, self.pack, **args)

    def test_both_signed_rules_are_recognized_but_not_approved(self):
        self.create()
        verified = verify_multi_review(self.pack, self.public, min_serial=9)
        self.assertEqual(verified["rule_ids"],
                         ["PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO",
                          "PS_RESOLVE_PATH_DOT_PREFIX"])
        self.assertEqual(verified["rules_verified"], 2)
        self.assertFalse(verified["production_approved"])
        receipt = scan_multi_review_receipt(self.pack, self.public, scanner_receipt(),
                                            min_serial=9)
        self.assertEqual(receipt["finding_count"], 2)
        self.assertEqual([i["rule_id"] for i in receipt["findings"]],
                         verified["rule_ids"])
        self.assertTrue(all(i["approved"] is False for i in receipt["findings"]))
        self.assertFalse(receipt["production_approved"])
        self.assertFalse(receipt["deploy_allowed"])
        self.assertFalse(receipt["auto_apply"])
        self.assertFalse(receipt["parser_executed_supplied_code"])
        self.assertEqual(receipt["persistent_writes"], 0)

    def test_review_requires_explicit_invocation_and_no_overwrite(self):
        with self.assertRaises(PolicyError):
            self.create(confirmation="AUTOMATIC")
        self.assertFalse(self.pack.exists())
        self.create()
        with self.assertRaises(PolicyError):
            self.create()

    def test_invalid_serial_expiry_trust_and_wrong_first_rule_pack_fail(self):
        self.create()
        with self.assertRaises(PolicyError):
            verify_multi_review(self.pack, self.public, min_serial=10)
        with self.assertRaises(PolicyError):
            verify_multi_review(self.pack, self.public,
                                at_time=datetime.now(timezone.utc) + timedelta(days=8))
        _, other = generate_keys(self.root / "other", purpose="prevention")
        with self.assertRaises(PolicyError):
            verify_multi_review(self.pack, other)

    def test_tampered_signed_rules_and_claimed_approval_fail(self):
        self.create()
        with zipfile.ZipFile(self.pack) as z:
            blobs = {name: z.read(name) for name in z.namelist()}
        for which in ("guidance", "approval", "count"):
            copy = dict(blobs)
            if which == "guidance":
                rules = deepcopy(RULES)
                rules[1]["safe_guidance"] = "Run this command automatically"
                copy["rules/prevention.json"] = canonical_json(rules)
            else:
                manifest = json.loads(blobs["manifest.json"])
                if which == "approval":
                    manifest["production_approved"] = True
                else:
                    manifest["rule_count"] = 3
                # Re-sign forged metadata with the correct test key. Receiver
                # still checks the hard-coded review-only safety contract.
                copy["manifest.json"] = canonical_json(manifest)
                copy["signatures/manifest.sig"] = _private_key(self.private).sign(
                    copy["manifest.json"])
            dst = self.root / "build" / ("tampered-" + which + ".zip")
            with zipfile.ZipFile(dst, "w") as z:
                for name, data in copy.items():
                    z.writestr(name, data)
            with self.assertRaises(PolicyError):
                verify_multi_review(dst, self.public)

    def test_duplicate_zip_member_rejected(self):
        self.create()
        with zipfile.ZipFile(self.pack) as z:
            original = {name: z.read(name) for name in z.namelist()}
        bad = self.root / "build" / "duplicate.zip"
        with zipfile.ZipFile(bad, "w") as z:
            for name, content in original.items():
                z.writestr(name, content)
            with self.assertWarns(UserWarning):
                z.writestr("manifest.json", original["manifest.json"])
        with self.assertRaises(PolicyError):
            verify_multi_review(bad, self.public)

    def test_forged_static_receipt_cannot_promote_or_misbind(self):
        self.create()
        for change in ("approved", "fake_evidence", "unknown", "bad_count"):
            scan = scanner_receipt()
            if change == "approved":
                scan["approved_rules"] = 1
            elif change == "fake_evidence":
                scan["findings"][1]["public_evidence"] = (
                    "https://github.com/PowerShell/PowerShell/pull/28042")
            elif change == "unknown":
                scan["findings"][1]["pattern_code"] = "EXECUTE_ANYTHING"
            else:
                scan["finding_count"] = 1
            with self.subTest(change=change), self.assertRaises(PolicyError):
                scan_multi_review_receipt(self.pack, self.public, scan)

    def test_non_matching_inert_receipt_is_not_a_clean_code_claim(self):
        self.create()
        scan = scanner_receipt()
        scan["findings"] = []
        scan["finding_count"] = 0
        result = scan_multi_review_receipt(self.pack, self.public, scan)
        self.assertEqual(result["finding_count"], 0)
        self.assertFalse(result["source_authentication_verified"])
        self.assertEqual(result["status"], "REVIEW_CANDIDATES_ONLY")


if __name__ == "__main__":
    unittest.main()
