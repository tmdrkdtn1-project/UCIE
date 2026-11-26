"""Bounded UCIE-only B4 evolution regression and fail-closed controls."""
from copy import deepcopy
from unittest import TestCase

from ucie_miner import ucie_v2_transfer_knowledge_evolution_v01 as e


class KnowledgeEvolutionTests(TestCase):
    def test_deduplicated_three_claims_and_pinned_sources(self):
        idx = e.build_knowledge_index()
        self.assertEqual(len(idx["concepts"]), 3)
        self.assertEqual(len({c["concept_id"] for c in idx["concepts"]}), 3)
        self.assertEqual({c["claim_code"] for c in idx["concepts"]},
                         e.ALLOWED_CLAIMS)
        for concept in idx["concepts"]:
            self.assertEqual(set(concept["source_pins"]), e.SOURCE_IDS)
            self.assertFalse(concept["export_allowed"])
            self.assertFalse(concept["independent_qa_verified"])

    def test_negative_lessons_and_targeted_retest(self):
        idx = e.build_fixed_evolution_demo()
        self.assertEqual(idx["event_count"], 4)
        self.assertEqual([x["decision"] for x in idx["events"]],
                         ["COUNTEREXAMPLE_RETAINED",
                          "COUNTEREXAMPLE_RETAINED",
                          "RETEST_PROPOSED", "NO_CHANGE"])
        self.assertEqual(idx["events"][2]["affected_concepts"],
                         ["BOUNDED_INPUT_AND_EXPLICIT_SCOPE"])
        self.assertEqual(idx["events"][3]["affected_concepts"], [])
        self.assertEqual(sum(x["retest_proposed"] for x in idx["events"]), 1)
        self.assertFalse(idx["source_version_current_verified"])
        self.assertFalse(idx["customer_release_authorized"])

    def test_duplicate_is_not_a_new_event(self):
        state = e.build_fixed_evolution_demo()
        row = state["events"][0]
        self.assertEqual(e.record_review_observation(
            state, source_id=row["source_id"], claim_code=row["claim_code"],
            reason_code=row["reason_code"], observed_pin=row["observed_pin"]),
            state)
        self.assertEqual(state, e.build_fixed_evolution_demo())

    def test_no_approval_no_network_no_operating_db(self):
        state = e.build_fixed_evolution_demo()
        for field in ("independent_qa_verified", "rights_approved",
                      "customer_release_authorized", "auto_promotion",
                      "history_persisted"):
            self.assertIs(state[field], False)
        self.assertEqual(state["operating_database_writes"], 0)
        self.assertEqual(state["network_requests"], 0)

    def test_unapproved_source_rejected(self):
        state = e.build_knowledge_index()
        with self.assertRaises(e.EvolutionError):
            e.record_review_observation(
                state, source_id="repo:unapproved/private",
                claim_code="BOUNDED_INPUT_AND_EXPLICIT_SCOPE",
                reason_code="UNCHANGED_PIN", observed_pin="a" * 40)

    def test_changed_pin_rejected_not_claimed_as_current(self):
        state = e.build_knowledge_index()
        with self.assertRaises(e.EvolutionError):
            e.record_review_observation(
                state, source_id="doc:git/git",
                claim_code="BOUNDED_INPUT_AND_EXPLICIT_SCOPE",
                reason_code="SOURCE_REVALIDATION_NEEDED",
                observed_pin="f" * 64)

    def test_unknown_claim_rejected(self):
        state = e.build_knowledge_index()
        with self.assertRaises(e.EvolutionError):
            e.record_review_observation(
                state, source_id="doc:git/git",
                claim_code="PROMOTE_ANYTHING",
                reason_code="UNCHANGED_PIN",
                observed_pin=state["concepts"][0]["source_pins"]["doc:git/git"])

    def test_invalid_positive_counterexample_rejected(self):
        state = e.build_knowledge_index()
        with self.assertRaises(e.EvolutionError):
            e.record_review_observation(
                state, source_id="doc:git/git",
                claim_code="BOUNDED_INPUT_AND_EXPLICIT_SCOPE",
                reason_code="FIRST_PARTY_COUNTEREXAMPLE",
                observed_pin=state["concepts"][0]["source_pins"]["doc:git/git"])

    def test_unhashable_claim_is_controlled_rejection(self):
        bad = deepcopy(e.build_fixed_evolution_demo())
        bad["events"][0]["claim_code"] = ["ALL_OUTPUTS_ANONYMIZED"]
        with self.assertRaises(e.EvolutionError):
            e.validate_knowledge_index(bad)

    def test_non_boolean_retest_flag_is_controlled_rejection(self):
        bad = deepcopy(e.build_fixed_evolution_demo())
        bad["events"][0]["retest_proposed"] = 0
        with self.assertRaises(e.EvolutionError):
            e.validate_knowledge_index(bad)

    def test_tampered_event_detected(self):
        state = e.build_fixed_evolution_demo()
        bad = deepcopy(state)
        bad["events"][0]["decision"] = "NO_CHANGE"
        with self.assertRaises(e.EvolutionError):
            e.validate_knowledge_index(bad)

    def test_forged_release_even_with_rehashed_content_rejected(self):
        bad = deepcopy(e.build_fixed_evolution_demo())
        bad["customer_release_authorized"] = True
        bad["content_sha256"] = e._digest(e._core(bad))
        with self.assertRaises(e.EvolutionError):
            e.validate_knowledge_index(bad)

    def test_event_reorder_detected(self):
        bad = deepcopy(e.build_fixed_evolution_demo())
        bad["events"].reverse()
        bad["content_sha256"] = e._digest(e._core(bad))
        with self.assertRaises(e.EvolutionError):
            e.validate_knowledge_index(bad)

    def test_deterministic_fixed_replay(self):
        self.assertEqual(e.build_fixed_evolution_demo(),
                         e.build_fixed_evolution_demo())
