"""Exact synthetic reviewer packet/byte hashes tied to existing UCIE claim.

Synthetic keys and test artifacts are ephemeral. No real code execution,
remote access, real QA, runner conclusions, or operating ledger writes.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ucie_public.policy import PolicyError
from ucie_public.rulepack import canonical_json
from ucie_miner.public_batch import build_public_batch, _fingerprint
from ucie_miner.public_library_graph import preview_library_knowledge_graph
from ucie_miner.public_library_qa_packet import (
    SCHEMA, BLOB_NAMES, FIXED_CLAIM, inspect_library_candidate_qa_packet,
)
from ucie_miner.public_library_runner_ci import (
    recheck_signed_packet_runner_ci, _fetch_exact_ucie_ci_run, WORKFLOW_PATH,
)
from ucie_miner.public_library_review_store import (
    ZERO_HEAD, DB_NAME, append_local_library_review_history,
)
from ucie_miner.public_library_signed_review import EVENT_SCHEMA
from ucie_miner.skill_profiles import PROFILE
from test_ucie_stage9_batch import NOW, metadata, evidence

STAMP = datetime(2026, 10, 22, 5, 0, tzinfo=timezone.utc)


class LibraryQAPacketTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        self.current = build_public_batch(
            metadata_fetch=metadata, evidence_fetch=evidence,
            now=NOW, max_enrich=2)
        graph = preview_library_knowledge_graph(self.current)
        self.card = next(n for n in graph["nodes"] if n["kind"] ==
                         "UNVERIFIED_PUBLIC_RESEARCH_REFERENCE")
        self.owner = Ed25519PrivateKey.generate()
        self.qa = Ed25519PrivateKey.generate()
        self.trust = {
            "owner_trust": self.owner.public_key(),
            "qa_trust": self.qa.public_key(), "at_time": STAMP,
        }
        self.artifacts = {
            name: ("UCIE_SYNTHETIC_UNVERIFIED_" + name).encode("ascii")
            for name in BLOB_NAMES
        }
        self.packet = {
            "schema": SCHEMA, "public_url": self.card["public_url"],
            "pinned_revision_sha": self.card["pinned_revision_sha"],
            "evidence_sha256": self.card["evidence_fingerprint_sha256"],
            "claimed_version": "3.15.0",
            "first_party_regression_plan": PROFILE[self.card["skill_id"]][
                "recommended_action"],
            "tested_pinned_revision_sha": self.card["pinned_revision_sha"],
            "runner_repository": "tmdrkdtn1-project/UCIE",
            "runner_run_id": 12345,
            "runner_commit_sha": "b" * 40,
            "observation_utc": (
                STAMP - timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
            "artifact_sha256": {
                key: hashlib.sha256(value).hexdigest()
                for key, value in self.artifacts.items()
            },
            "result_claim": FIXED_CLAIM,
        }

    def _sign_event(self, action, serial, *, digest=None, expires=None):
        reviewed = action == "REVIEW_ATTESTED"
        issued = STAMP - timedelta(hours=2)
        claim = {
            "schema": EVENT_SCHEMA,
            "action": action,
            "public_url": self.card["public_url"],
            "pinned_revision_sha": self.card["pinned_revision_sha"],
            "evidence_sha256": self.card["evidence_fingerprint_sha256"],
            "version_claim": "3.15.0" if reviewed else None,
            "review_evidence_sha256": (
                digest if digest is not None else
                hashlib.sha256(canonical_json(self.packet)).hexdigest()
            ) if reviewed else None,
            "review_claims": {
                "source_license": True, "security": True,
                "regression": True, "release_version": True,
            } if reviewed else None,
            "serial": serial,
            "issued_utc": issued.isoformat().replace("+00:00", "Z"),
            "expires_utc": (expires or issued + timedelta(days=7)).isoformat()
                .replace("+00:00", "Z") if reviewed else None,
        }
        blob = canonical_json(claim)
        return {
            "claim": claim, "owner_signature_hex": self.owner.sign(blob).hex(),
            "qa_signature_hex": self.qa.sign(blob).hex() if reviewed else None,
        }

    def _append(self, records, head=ZERO_HEAD):
        return append_local_library_review_history(
            self.root, self.current, records,
            expected_head_sha256=head, allow_disk_write=True, **self.trust)

    def _inspect(self, head, *, packet=None, artifacts=None, current=None, **args):
        return inspect_library_candidate_qa_packet(
            self.root, current if current is not None else self.current,
            self.card["public_url"],
            packet if packet is not None else self.packet,
            artifacts if artifacts is not None else self.artifacts,
            expected_head_sha256=head, **{**self.trust, **args})

    def test_exact_candidate_packet_and_bounded_bytes_bind_to_signature_only(self):
        entry = self._append([self._sign_event("REVIEW_ATTESTED", 1)])
        db = self.root / "runtime" / DB_NAME
        original = db.read_bytes()
        report = self._inspect(entry["head_sha256"])
        self.assertEqual(db.read_bytes(), original)
        self.assertTrue(report["packet_sha256_matches_signed_review"])
        self.assertEqual(report["supplied_artifact_digests_match_bytes"], 6)
        self.assertEqual(report["signed_claim_event_serial"], 1)
        self.assertEqual(report["status"],
                         "SIGNED_QA_PACKET_BYTES_BOUND_AUDIT_PENDING_NO_GO")
        for flag in ("source_release_inclusion_confirmed_by_independent_source",
                     "license_content_reviewed_independently",
                     "security_negative_behavior_independently_reproduced",
                     "regression_affected_and_fixed_behaviors_independently_reproduced",
                     "runner_workflow_conclusion_checked_live",
                     "reviewer_identity_and_independence_verified",
                     "candidate_rule_approval", "production_approved"):
            self.assertFalse(report[flag], flag)
        self.assertEqual(report["automatic_rule_promotions"], 0)
        self.assertEqual(report["operating_database_writes"], 0)
        self.assertEqual(report["network_requests"], 0)

    def test_broken_artifact_bytes_and_packet_hash_rejected(self):
        head = self._append([self._sign_event("REVIEW_ATTESTED", 1)])["head_sha256"]
        corrupt = dict(self.artifacts)
        corrupt["fixed_behavior_observation"] = b"FORGED_PASS"
        with self.assertRaises(PolicyError):
            self._inspect(head, artifacts=corrupt)
        changed = dict(self.packet)
        changed["runner_run_id"] = 88888
        with self.assertRaises(PolicyError):
            self._inspect(head, packet=changed)
        extra = dict(self.packet)
        extra["run_command"] = "powershell Invoke-Expression remote-code"
        with self.assertRaises(PolicyError):
            self._inspect(head, packet=extra)
        massive = dict(self.artifacts)
        massive["license_review_observation"] = b"a" * 8193
        with self.assertRaises(PolicyError):
            self._inspect(head, artifacts=massive)

    def test_packet_claim_must_match_a_signed_review_hash(self):
        head = self._append([
            self._sign_event("REVIEW_ATTESTED", 1, digest="a" * 64)
        ])["head_sha256"]
        with self.assertRaises(PolicyError):
            self._inspect(head)

    def test_packet_is_blocked_by_revocation_expiry_and_wrong_head(self):
        initial = self._append([self._sign_event("REVIEW_ATTESTED", 1)])
        head = initial["head_sha256"]
        with self.assertRaises(PolicyError):
            self._inspect(ZERO_HEAD)
        with self.assertRaises(PolicyError):
            self._inspect(head, qa_trust=Ed25519PrivateKey.generate().public_key())
        new = self._append(
            [self._sign_event("REVOKE", 2)], head
        )["head_sha256"]
        with self.assertRaises(PolicyError):
            self._inspect(new)

    def test_expired_signature_is_not_accepted_for_packet(self):
        signed_at = STAMP - timedelta(hours=2)
        expiry = signed_at + timedelta(minutes=10)
        head = self._append([
            self._sign_event("REVIEW_ATTESTED", 1, expires=expiry)
        ])["head_sha256"]
        with self.assertRaises(PolicyError):
            self._inspect(head)

    def test_new_revision_or_evidence_digest_never_inherit_old_packet(self):
        head = self._append([self._sign_event("REVIEW_ATTESTED", 1)])["head_sha256"]
        for changed in ("evidence_sha256", "pinned_merge_commit_sha"):
            altered = deepcopy(self.current)
            item = next(x for x in altered["candidate_skill_queue"]
                        if x["public_url"] == self.card["public_url"])
            item[changed] = ("e" if changed == "evidence_sha256" else "d") * (
                64 if changed == "evidence_sha256" else 40)
            altered["candidate_queue_sha256"] = _fingerprint(
                altered["candidate_skill_queue"])
            with self.subTest(changed=changed), self.assertRaises(PolicyError):
                self._inspect(head, current=altered)

    def _runner_metadata(self, **overrides):
        value = {
            "id": self.packet["runner_run_id"],
            "repository": {"full_name": "tmdrkdtn1-project/UCIE"},
            "html_url": (
                "https://github.com/tmdrkdtn1-project/UCIE/actions/runs/"
                + str(self.packet["runner_run_id"])),
            "path": WORKFLOW_PATH + "refs/pull/77/merge",
            "head_sha": self.packet["runner_commit_sha"],
            "status": "completed", "conclusion": "success",
            "updated_at": (STAMP - timedelta(minutes=1)).isoformat()
                .replace("+00:00", "Z"),
        }
        value.update(overrides)
        return value

    def _runner(self, head, *, fetch, live=True, **opts):
        return recheck_signed_packet_runner_ci(
            self.root, self.current, self.card["public_url"],
            self.packet, self.artifacts,
            expected_head_sha256=head, live=live, fetch=fetch,
            **{**self.trust, **opts})

    def test_generic_runner_ci_can_match_signed_packet_but_never_qa(self):
        head = self._append([self._sign_event("REVIEW_ATTESTED", 1)])["head_sha256"]
        db = self.root / "runtime" / DB_NAME
        before = db.read_bytes()
        urls = []
        def fake(url):
            urls.append(url)
            return self._runner_metadata(), 90
        result = self._runner(head, fetch=fake)
        self.assertEqual(urls, [
            "https://api.github.com/repos/tmdrkdtn1-project/UCIE/actions/runs/12345"
        ])
        self.assertEqual(db.read_bytes(), before)
        self.assertEqual(result["status"],
                         "SYNTHETIC_CI_METADATA_MATCH_NOT_LIVE_NO_GO")
        self.assertTrue(result["runner_commit_sha_matches"])
        self.assertTrue(result["runner_completed_success_claim_matches_metadata"])
        self.assertFalse(result["public_api_response_retrieved_live"])
        self.assertEqual(result["http_get_attempts"], 0)
        self.assertEqual(result["transport_invocations"], 1)
        for flag in (
            "candidate_specific_test_steps_observed",
            "upstream_candidate_revision_tested_by_runner_proven",
            "affected_vs_fixed_behavior_reproduced_independently",
            "release_license_and_security_independently_reviewed",
            "human_reviewer_independence_verified",
            "owner_release_approval", "production_approved",
        ):
            self.assertFalse(result[flag])
        self.assertEqual(result["automatic_rule_promotions"], 0)

    def test_wrong_runner_commit_failed_run_and_rate_pause(self):
        head = self._append([self._sign_event("REVIEW_ATTESTED", 1)])["head_sha256"]
        mismatch = self._runner(
            head, fetch=lambda _: (
                self._runner_metadata(head_sha="a" * 40), 99))
        self.assertEqual(mismatch["status"], "UCIE_RUNNER_CI_SHA_MISMATCH_NO_GO")
        failed = self._runner(
            head, fetch=lambda _: (
                self._runner_metadata(conclusion="failure"), 99))
        self.assertEqual(
            failed["status"], "UCIE_RUNNER_CI_NOT_COMPLETED_SUCCESSFULLY_NO_GO")
        paused = self._runner(
            head, fetch=lambda _: (self._runner_metadata(), 1))
        self.assertEqual(paused["status"], "PUBLIC_RUNNER_API_RATE_PAUSED_NO_GO")
        self.assertFalse(paused["public_api_response_retrieved_live"])

    def test_foreign_runner_identity_and_transport_are_rejected(self):
        head = self._append([self._sign_event("REVIEW_ATTESTED", 1)])["head_sha256"]
        for change in (
            {"repository": {"full_name": "foreign/private"}},
            {"id": 9876},
            {"path": "foreign/private/.github/workflows/attack.yml@main"},
            {"html_url": "https://example.invalid/run/12345"},
            {"updated_at": "2028-01-01T00:00:00Z"},
            {"status": "in_progress", "conclusion": "success"},
        ):
            with self.subTest(change=change), self.assertRaises(PolicyError):
                self._runner(head, fetch=lambda _, x=change: (
                    self._runner_metadata(**x), 80))
        for bad in (self._runner_metadata(),
                    (self._runner_metadata(), True),
                    (self._runner_metadata(), -1),
                    ([], None)):
            with self.subTest(bad=type(bad)), self.assertRaises(PolicyError):
                self._runner(head, fetch=lambda _, x=bad: x)
        for url in (
            "https://api.github.com/repos/foreign/repo/actions/runs/123",
            "http://api.github.com/repos/tmdrkdtn1-project/UCIE/actions/runs/123",
            "https://api.github.com/repos/tmdrkdtn1-project/UCIE/actions/runs/123/jobs",
        ):
            with self.subTest(url=url), self.assertRaises(PolicyError):
                _fetch_exact_ucie_ci_run(url)

    def test_unauthorized_run_or_revoked_packet_never_fetches_ci(self):
        def must_not_run(_):
            raise AssertionError("unauthorized remote call occurred")
        with self.assertRaises(PolicyError):
            self._runner(ZERO_HEAD, fetch=must_not_run, live=False)
        first = self._append([self._sign_event("REVIEW_ATTESTED", 1)])
        revoked = self._append(
            [self._sign_event("REVOKE", 2)],
            first["head_sha256"])
        with self.assertRaises(PolicyError):
            self._runner(revoked["head_sha256"], fetch=must_not_run)

    def test_missing_history_and_foreign_root_fail_closed(self):
        with self.assertRaises(PolicyError):
            self._inspect(ZERO_HEAD)
        temp = self.root.parent / "Foreign"
        with self.assertRaises(PolicyError):
            inspect_library_candidate_qa_packet(
                temp, self.current, self.card["public_url"],
                self.packet, self.artifacts,
                expected_head_sha256=ZERO_HEAD, **self.trust)


if __name__ == "__main__":
    unittest.main()
