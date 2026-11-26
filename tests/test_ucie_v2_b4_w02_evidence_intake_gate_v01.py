"""W02 intake never silently promotes public metadata to verified B4."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from ucie_miner import ucie_v2_b4_w02_evidence_intake_gate_v01 as gate


def _powershell():
    return {
        "kind": "TEST_RECIPE",
        "source_id": "repo:PowerShell/PowerShell",
        "evidence_reference":
            "pr:28087:373f6a7b7972a0a4b73bfd9737a0d768d28b347e",
        "evidence_sha256":
            "bfb46af89433268872ddb43d1ca7a3f433452ee91ed356a9786940f90118e285",
        "purpose_code": "BOUNDED_VERSION_TEST",
        "version_scope": "7.6.6",
        "dependencies": [],
    }


def _python():
    return {
        "kind": "TEST_RECIPE",
        "source_id": "repo:python/cpython",
        "evidence_reference":
            "pr:153462:999a046b24cff4ba0e72b574196721f66bd08237",
        "evidence_sha256": "a" * 64,
        "purpose_code": "BOUNDED_VERSION_TEST",
        "version_scope": "3.15.0",
        "dependencies": [],
    }


class W02IntakeGateTests(TestCase):
    def test_one_real_preexisting_public_record_held(self):
        result = gate.triage_w02_evidence([_powershell()])
        self.assertEqual(result["unique_count"], 1)
        self.assertEqual(result["hypothesis_count"], 0)
        self.assertFalse(result["review_queue"][0]["hypothesis_created"])
        self.assertEqual(result["review_queue"][0]["triage_status"],
                         "HOLD_MECHANISM_NOT_REVIEWED")

    def test_two_approved_sources_same_purpose_do_not_prove_mechanism(self):
        result = gate.triage_w02_evidence([_powershell(), _python()])
        self.assertEqual(result["unique_count"], 2)
        self.assertEqual(result["cross_source_purpose_matches"][0]
                         ["distinct_sources"], 2)
        self.assertEqual(result["hypothesis_count"], 0)

    def test_duplicate_not_counted_twice(self):
        x = _powershell()
        result = gate.triage_w02_evidence([x, deepcopy(x)])
        self.assertEqual(result["submitted_count"], 2)
        self.assertEqual(result["duplicate_count"], 1)
        self.assertEqual(result["unique_count"], 1)

    def test_source_order_deterministic(self):
        self.assertEqual(gate.triage_w02_evidence([_python(), _powershell()])
                         ["content_sha256"],
                         gate.triage_w02_evidence([_powershell(), _python()])
                         ["content_sha256"])

    def test_same_revision_conflicting_evidence_blocked(self):
        x = _powershell()
        y = deepcopy(x)
        y["evidence_sha256"] = "f" * 64
        with self.assertRaises(gate.IntakeGateError):
            gate.triage_w02_evidence([x, y])

    def test_same_identity_different_version_is_not_silent_duplicate(self):
        x = _powershell()
        y = deepcopy(x)
        y["version_scope"] = "7.6.7"
        with self.assertRaises(gate.IntakeGateError):
            gate.triage_w02_evidence([x, y])

    def test_unapproved_repository_blocked(self):
        x = _powershell()
        x["source_id"] = "repo:unknown/secret"
        with self.assertRaises(gate.IntakeGateError):
            gate.triage_w02_evidence([x])

    def test_fake_approval_field_blocked(self):
        x = _powershell()
        x["owner_signed"] = True
        with self.assertRaises(gate.IntakeGateError):
            gate.triage_w02_evidence([x])

    def test_invalid_sha_blocked(self):
        x = _powershell()
        x["evidence_sha256"] = "bad"
        with self.assertRaises(gate.IntakeGateError):
            gate.triage_w02_evidence([x])

    def test_empty_and_oversize_blocked(self):
        with self.assertRaises(gate.IntakeGateError):
            gate.triage_w02_evidence([])
        with self.assertRaises(gate.IntakeGateError):
            gate.triage_w02_evidence([_powershell()] * (gate.MAX_ITEMS + 1))

    def test_unsupported_version_blocked(self):
        x = _powershell()
        x["version_scope"] = "<unspecified>"
        with self.assertRaises(gate.IntakeGateError):
            gate.triage_w02_evidence([x])

    def test_false_w02_qa_escalation_blocked(self):
        from ucie_miner import library_entry as original
        real = original.build_library_entry(_powershell())
        forged = deepcopy(real)
        forged["independent_qa_status"] = "PASSED"
        with patch.object(gate, "build_library_entry", return_value=forged):
            with self.assertRaises(gate.IntakeGateError):
                gate.triage_w02_evidence([_powershell()])

    def test_no_implicit_network_approval_or_release(self):
        result = gate.triage_w02_evidence([_powershell()])
        self.assertFalse(result["source_fetch_performed"])
        self.assertFalse(result["source_code_executed"])
        self.assertFalse(result["rights_approved"])
        self.assertFalse(result["customer_release_authorized"])
        self.assertFalse(result["auto_promoted"])
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["operating_database_writes"], 0)

    def test_curated_and_new_unreviewed_evidence_stay_separate(self):
        result = gate.combined_curated_and_unreviewed([_powershell(), _python()])
        self.assertEqual(result["pending_intake"]["hypothesis_count"], 0)
        self.assertEqual(result["curated_review"]
                         ["source_pinned_synthesis"]["record_count"], 4)
        self.assertFalse(result["unreviewed_evidence_used_as_hypothesis_proof"])
