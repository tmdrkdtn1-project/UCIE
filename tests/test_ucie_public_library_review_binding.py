"""Synthetic UCIE Library signed history / exact revision closure tests.

No real signatures, reviewers, independent QA, private projects, production
Rulepacks, runtime databases or external source code are used. Synthetic test
keys live only in an ephemeral test fixture; no key is published by the feature.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ucie_public.policy import PolicyError
from ucie_public.rulepack import canonical_json
from ucie_miner.public_batch import build_public_batch, _fingerprint
from ucie_miner.public_discovery import DiscoveryError
from ucie_miner.public_library_graph import preview_library_knowledge_graph
from ucie_miner.public_library_review_binding import (
    SCHEMA, inspect_library_review_closure,
)
from ucie_miner.public_library_review_store import (
    ZERO_HEAD, DB_NAME, append_local_library_review_history,
)
from ucie_miner.public_library_signed_review import EVENT_SCHEMA
from test_ucie_stage9_batch import NOW, metadata, evidence

NOW_SIGNED = datetime(2026, 10, 22, 5, 0, tzinfo=timezone.utc)


def public_batch(n=2):
    return build_public_batch(
        metadata_fetch=metadata, evidence_fetch=evidence,
        now=NOW, max_enrich=n)


class PublicLibrarySignedBindingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        self.current = public_batch()
        self.owner = Ed25519PrivateKey.generate()
        self.qa = Ed25519PrivateKey.generate()
        graph = preview_library_knowledge_graph(self.current)
        self.card = next(n for n in graph["nodes"]
                         if n["kind"] == "UNVERIFIED_PUBLIC_RESEARCH_REFERENCE")
        self.trust = dict(
            owner_trust=self.owner.public_key(),
            qa_trust=self.qa.public_key(),
            at_time=NOW_SIGNED,
        )

    def signed(self, *, action="REVIEW_ATTESTED", serial=1, expires=None):
        attested = action == "REVIEW_ATTESTED"
        issued = NOW_SIGNED - timedelta(hours=2)
        claim = {
            "schema": EVENT_SCHEMA,
            "action": action,
            "public_url": self.card["public_url"],
            "pinned_revision_sha": self.card["pinned_revision_sha"],
            "evidence_sha256": self.card["evidence_fingerprint_sha256"],
            "version_claim": "3.15.0" if attested else None,
            "review_evidence_sha256": "f" * 64 if attested else None,
            "review_claims": {
                "source_license": True, "security": True,
                "regression": True, "release_version": True,
            } if attested else None,
            "serial": serial,
            "issued_utc": issued.isoformat().replace("+00:00", "Z"),
            "expires_utc": (expires or (issued + timedelta(days=7))).isoformat()
                .replace("+00:00", "Z") if attested else None,
        }
        raw = canonical_json(claim)
        return {
            "claim": claim,
            "owner_signature_hex": self.owner.sign(raw).hex(),
            "qa_signature_hex": self.qa.sign(raw).hex() if attested else None,
        }

    def append(self, entries, expected_head=ZERO_HEAD):
        return append_local_library_review_history(
            self.root, self.current, entries,
            expected_head_sha256=expected_head, allow_disk_write=True,
            **self.trust)

    def inspect(self, head=ZERO_HEAD, **options):
        return inspect_library_review_closure(
            self.root, self.current, expected_head_sha256=head,
            **{**self.trust, **options})

    def test_empty_signed_history_keeps_all_public_candidates_pending(self):
        db = self.root / "runtime" / DB_NAME
        self.assertFalse(db.exists())
        a = self.inspect()
        b = self.inspect()
        self.assertEqual(a, b)
        self.assertEqual(a["schema"], SCHEMA)
        self.assertEqual(a["latest_reference_count"], 2)
        self.assertEqual(a["signed_history_event_count"], 0)
        self.assertEqual(a["states"], {"NO_SIGNED_REVIEW_HISTORY_NO_GO": 2})
        self.assertEqual(a["public_evidence_chain_status"],
                         "STAGE16_INCOMPLETE_LOCAL_EVIDENCE_NO_GO")
        self.assertEqual(len(a["next_manual_reviews"]), 2)
        self.assertFalse(db.exists(), "read-only binding unexpectedly created DB")
        for field in ("production_approved", "distribution_authorized",
                      "closure_sha256_is_signature",
                      "external_checkpoint_independently_anchored"):
            self.assertFalse(a[field])
        self.assertEqual(a["automatic_rule_promotions"], 0)

    def test_valid_dual_signed_claim_is_not_independent_qa_or_release(self):
        prior = self.append([self.signed()])
        db = self.root / "runtime" / DB_NAME
        before = db.read_bytes()
        result = self.inspect(prior["head_sha256"])
        self.assertEqual(db.read_bytes(), before)
        self.assertEqual(result["signed_history_event_count"], 1)
        self.assertEqual(result["states"], {
            "NO_SIGNED_REVIEW_HISTORY_NO_GO": 1,
            "KEYHOLDER_SIGNED_CLAIMS_AWAIT_INDEPENDENT_QA_NO_GO": 1,
        })
        linked = next(x for x in result["review_records"]
                      if x["ledger_claim_revision_matches"])
        self.assertEqual(linked["signed_keyholder_claim_version"], "3.15.0")
        for key in ("source_version_independently_verified",
                    "source_license_independently_verified",
                    "security_independently_verified",
                    "regression_independently_reproduced",
                    "human_qa_independently_confirmed",
                    "owner_release_approval_granted",
                    "rules_may_auto_promote", "can_publish_or_install"):
            self.assertFalse(linked[key], key)
        self.assertEqual(result["independently_approved_rule_count"], 0)

    def test_owner_revocation_blocks_even_pinned_exact_match(self):
        first = self.append([self.signed()])
        revoked = self.append(
            [self.signed(action="REVOKE", serial=2)],
            expected_head=first["head_sha256"])
        result = self.inspect(revoked["head_sha256"])
        entry = next(x for x in result["review_records"]
                     if x["ledger_event_serial"] == 2)
        self.assertEqual(entry["review_state"], "OWNER_REVOKED_BLOCKED_NO_GO")
        self.assertEqual(entry["next_action"],
                         "KEEP_REVOKED_AND_REQUIRE_SEPARATE_RECOVERY_APPROVAL")
        self.assertFalse(entry["can_publish_or_install"])

    def test_updated_evidence_digest_invalidates_old_signed_claim(self):
        first = self.append([self.signed()])
        altered = deepcopy(self.current)
        match = next(x for x in altered["candidate_skill_queue"]
                     if x["public_url"] == self.card["public_url"])
        match["evidence_sha256"] = (
            "e" if match["evidence_sha256"] != "e" * 64 else "d") * 64
        altered["candidate_queue_sha256"] = _fingerprint(
            altered["candidate_skill_queue"])
        report = inspect_library_review_closure(
            self.root, altered, expected_head_sha256=first["head_sha256"],
            previous=self.current, **self.trust)
        matching = next(x for x in report["review_records"]
                        if x["public_url"] == self.card["public_url"])
        self.assertEqual(matching["review_state"],
                         "REVIEW_FOR_OLDER_PINNED_EVIDENCE_NO_GO")
        self.assertFalse(matching["ledger_claim_revision_matches"])
        self.assertIsNone(matching["signed_keyholder_claim_version"])
        self.assertIn("PUBLIC_EVIDENCE_FINGERPRINT_CHANGED",
                      {x["revision_change"] for x in report["review_records"]})

    def test_updated_merge_sha_invalidates_old_signed_claim(self):
        first = self.append([self.signed()])
        altered = deepcopy(self.current)
        match = next(x for x in altered["candidate_skill_queue"]
                     if x["public_url"] == self.card["public_url"])
        match["pinned_merge_commit_sha"] = (
            "a" if match["pinned_merge_commit_sha"] != "a" * 40 else "b") * 40
        altered["candidate_queue_sha256"] = _fingerprint(
            altered["candidate_skill_queue"])
        report = inspect_library_review_closure(
            self.root, altered, previous=self.current,
            expected_head_sha256=first["head_sha256"], **self.trust)
        matching = next(x for x in report["review_records"]
                        if x["public_url"] == self.card["public_url"])
        self.assertEqual(matching["review_state"],
                         "REVIEW_FOR_OLDER_PINNED_EVIDENCE_NO_GO")
        self.assertFalse(matching["can_publish_or_install"])

    def test_expired_claim_never_promotes_even_if_exact_revision(self):
        issued = NOW_SIGNED - timedelta(hours=2)
        expired = self.signed(expires=issued + timedelta(minutes=5))
        head = self.append([expired])["head_sha256"]
        report = self.inspect(head)
        self.assertIn("SIGNED_CLAIMS_EXPIRED_NO_GO", report["states"])
        self.assertEqual(report["automatic_rule_promotions"], 0)

    def test_history_head_rollback_and_wrong_trust_fail_closed(self):
        event = self.append([self.signed()])
        with self.assertRaises(PolicyError):
            self.inspect(ZERO_HEAD)
        with self.assertRaises(PolicyError):
            self.inspect(None)
        with self.assertRaises(PolicyError):
            self.inspect("z" * 64)
        with self.assertRaises(PolicyError):
            inspect_library_review_closure(
                self.root, self.current,
                expected_head_sha256=event["head_sha256"],
                owner_trust=Ed25519PrivateKey.generate().public_key(),
                qa_trust=self.qa.public_key(), at_time=NOW_SIGNED)

    def test_changing_review_scope_cannot_claim_deleted(self):
        prior = self.append([self.signed()])
        smaller = public_batch(1)
        report = inspect_library_review_closure(
            self.root, smaller, previous=self.current,
            expected_head_sha256=prior["head_sha256"], **self.trust)
        self.assertEqual(report["latest_reference_count"], 1)
        self.assertEqual(len(report["previously_selected_not_seen"]), 1)
        self.assertTrue(report["bounded_nonselection_does_not_mean_deleted"])

    def test_forged_batch_approval_and_other_root_blocked(self):
        prior = self.append([self.signed()])
        forged = deepcopy(self.current)
        forged["candidate_skill_queue"][0]["human_approval_received"] = True
        forged["candidate_queue_sha256"] = _fingerprint(
            forged["candidate_skill_queue"])
        with self.assertRaises(DiscoveryError):
            inspect_library_review_closure(
                self.root, forged, expected_head_sha256=prior["head_sha256"],
                **self.trust)
        with self.assertRaises(PolicyError):
            inspect_library_review_closure(
                self.root.parent / "OtherProject", self.current,
                expected_head_sha256=prior["head_sha256"], **self.trust)


if __name__ == "__main__":
    unittest.main()
