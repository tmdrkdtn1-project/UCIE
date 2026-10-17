"""First portable public prevention rule: signing is explicit and nonproduction.

No private data and no external code, files or projects. All tests use disposable
first-party fixtures; a signature alone does not make a rule production-approved.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
import zipfile

from ucie_public.policy import PolicyError
from ucie_public.rulepack import (
    canonical_json, digest, generate_keys, _private_key,
)
from ucie_public.prevention_rulepack import (
    CONFIRM, RULE, publish_prevention_review, verify_prevention_review,
)


class FirstPreventionReviewPackTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "build").mkdir()
        self.key, self.pub = generate_keys(
            self.root / "prevention", purpose="prevention")
        self.path = self.root / "build" / "first-review.zip"

    def publish(self):
        return publish_prevention_review(
            self.root, self.key, self.path, serial=7, confirmation=CONFIRM)

    def test_manual_sign_then_consumer_verify_is_review_only(self):
        with self.assertRaises(PolicyError):
            publish_prevention_review(
                self.root, self.key, self.path,
                serial=7, confirmation="AUTOMATIC")
        self.assertFalse(self.path.exists())
        self.publish()
        result = verify_prevention_review(self.path, self.pub, min_serial=7)
        self.assertEqual(result["result"],
                         "SIGNED_PUBLIC_PREVENTION_REVIEW_PACK_VERIFIED")
        self.assertEqual(result["rule_id"], RULE["rule_id"])
        self.assertIn("-X disable-remote-debug", result["safe_guidance"])
        self.assertEqual(result["signature"], "VALID")
        self.assertFalse(result["production_approved"])
        self.assertFalse(result["deploy_allowed"])
        self.assertFalse(result["auto_promoted"])
        with self.assertRaises(PolicyError):
            self.publish()

    def test_separate_keys_and_trust_anchor(self):
        demo_key, demo_pub = generate_keys(self.root / "demo")
        self.assertNotEqual(demo_key.name, self.key.name)
        self.publish()
        with self.assertRaises(PolicyError):
            verify_prevention_review(self.path, demo_pub)
        with self.assertRaises(PolicyError):
            generate_keys(self.root / "prevention", purpose="prevention")

    def test_expiry_and_rollback_rejected(self):
        self.publish()
        with self.assertRaises(PolicyError):
            verify_prevention_review(self.path, self.pub, min_serial=8)
        with self.assertRaises(PolicyError):
            verify_prevention_review(
                self.path, self.pub,
                at_time=datetime.now(timezone.utc) + timedelta(days=10))

    def test_changed_rule_and_extra_files_are_rejected(self):
        self.publish()
        altered = self.root / "build" / "changed.zip"
        with zipfile.ZipFile(self.path) as original:
            data = {n: original.read(n) for n in original.namelist()}
        rule = json.loads(data["rules/prevention.json"].decode("utf-8"))
        rule[0]["safe_guidance"] = "unsafe command"
        data["rules/prevention.json"] = canonical_json(rule)
        with zipfile.ZipFile(altered, "w") as out:
            for name, value in data.items():
                out.writestr(name, value)
        with self.assertRaises(PolicyError):
            verify_prevention_review(altered, self.pub)

        extra = self.root / "build" / "extra.zip"
        with zipfile.ZipFile(extra, "w") as out:
            for name, value in data.items():
                out.writestr(name, value)
            out.writestr("../../other", b"NEVER")
        with self.assertRaises(PolicyError):
            verify_prevention_review(extra, self.pub)

    def test_even_validly_signed_forged_approval_or_guidance_fails(self):
        self.publish()
        with zipfile.ZipFile(self.path) as src:
            raw = {name: src.read(name) for name in src.namelist()}
        manifest = json.loads(raw["manifest.json"])
        manifest["production_approved"] = True
        raw["manifest.json"] = canonical_json(manifest)
        raw["signatures/manifest.sig"] = _private_key(self.key).sign(
            raw["manifest.json"])
        forged = self.root / "build" / "forged.zip"
        with zipfile.ZipFile(forged, "w") as out:
            for name, val in raw.items():
                out.writestr(name, val)
        with self.assertRaises(PolicyError):
            verify_prevention_review(forged, self.pub)

        manifest["production_approved"] = False
        rule = json.loads(raw["rules/prevention.json"])
        rule[0]["automation"] = "AUTO_APPLY"
        raw["rules/prevention.json"] = canonical_json(rule)
        manifest["rules_sha256"] = digest(raw["rules/prevention.json"])
        raw["manifest.json"] = canonical_json(manifest)
        raw["signatures/manifest.sig"] = _private_key(self.key).sign(
            raw["manifest.json"])
        changed = self.root / "build" / "signed-change.zip"
        with zipfile.ZipFile(changed, "w") as out:
            for name, val in raw.items():
                out.writestr(name, val)
        with self.assertRaises(PolicyError):
            verify_prevention_review(changed, self.pub)


if __name__ == "__main__":
    unittest.main()
