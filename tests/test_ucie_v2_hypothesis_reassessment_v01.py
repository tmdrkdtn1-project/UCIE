"""Review-only UCIE improvement feedback: no erased failures or fake promotions."""
from copy import deepcopy
from unittest import TestCase

from ucie_miner import ucie_v2_library_revision_ledger_v01 as history
from ucie_miner import ucie_v2_original_library_assets_v01 as original
from ucie_miner import ucie_v2_hypothesis_reassessment_v01 as improve
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5
from ucie_miner import ucie_v2_revision_impact_v01 as b3


def row(method):
    return {"study_id": b5.STUDY_ID, "case_id": b5.CASE_ID,
            "anonymous_trial_token": "F01", "method": method,
            "cohort": "FIRST_TIME_CODER", "first_safe_action_time_ms": 850,
            "correct_safe_action": True, "false_version_or_rights_claim": False,
            "evidence_detail_found": False, "origin": b5.SYNTHETIC_ORIGIN}


def changed(source):
    return {"source_id": source, "previous_pin": b3.PINS[source],
            "candidate_pin": "f"*len(b3.PINS[source])}


def rehash(history_obj):
    for i, event in enumerate(history_obj["events"]):
        event["event_hash"] = history._hash({
            k:v for k,v in event.items() if k != "event_hash"
        })
        if i:
            event["previous_hash"] = history_obj["events"][i-1]["event_hash"]
            event["event_hash"] = history._hash({
                k:v for k,v in event.items() if k != "event_hash"
            })
    history_obj["latest_hash"] = (history_obj["events"][-1]["event_hash"]
                                   if history_obj["events"] else None)
    history_obj["content_sha256"] = history._hash({
        k:v for k,v in history_obj.items() if k != "content_sha256"
    })
    return history_obj


class ReassessmentTests(TestCase):
    @classmethod
    def setUpClass(cls):
        records = tuple(row(m) for m in b5.METHODS)
        cls.clean = original.assemble_original_library_assets(records, ())
        cls.revised = original.assemble_original_library_assets(
            records, (changed("doc:git/git"),))
        cls.incomplete = original.assemble_original_library_assets(
            (row(b5.METHODS[0]),), ())
        cls.base = history.new_review_history()

    def make(self, *bundles):
        h = self.base
        for bundle in bundles:
            h = history.append_review_bundle(h, bundle)
        return h

    def test_empty_history_produces_no_invented_hypothesis(self):
        x = improve.reassess_library_hypotheses(self.base)
        self.assertEqual(x["review_lifecycle"], "EMPTY_HISTORY_NO_HYPOTHESIS")
        self.assertEqual(x["generated_candidates_count"], 0)

    def test_one_valid_synthetic_history_produces_two_narrowed_drafts(self):
        x = improve.reassess_library_hypotheses(self.make(self.clean))
        self.assertEqual(x["generated_candidates_count"], 2)
        self.assertEqual(x["review_lifecycle"], "BASELINE_SYNTHETIC_REVIEW_ONLY")
        self.assertTrue(all(not c["automatic_promotion"] for c in
                            x["original_falsifiable_candidates"]))
        self.assertIn("ALL_BOUNDED_METADATA_PROCESSES_HIDE_SOURCE_NAMES",
                      x["reusable_failed_transfer_claim"])

    def test_deterministic_idempotent_hashes(self):
        h = self.make(self.clean, self.incomplete)
        a = improve.reassess_library_hypotheses(h)
        b = improve.reassess_library_hypotheses(h)
        self.assertEqual(a,b)
        self.assertEqual(a["content_sha256"], improve._hash({
            k:v for k,v in a.items() if k != "content_sha256"
        }))

    def test_change_hold_survives_later_synthetic_clean_result(self):
        x = improve.reassess_library_hypotheses(
            self.make(self.revised, self.clean))
        self.assertEqual(x["review_lifecycle"],
                         "SOURCE_REVISION_HOLD_NOT_CLEARED_BY_SYNTHETIC_REPLAY")
        self.assertTrue(all(c["status"] == "HOLD_UNRESOLVED_SOURCE_REVISION"
                            for c in x["original_falsifiable_candidates"]))
        self.assertIn("doc:git/git", x["unresolved_changed_sources"])

    def test_incomplete_latest_holds_narrowed_candidates(self):
        x = improve.reassess_library_hypotheses(self.make(self.clean,self.incomplete))
        self.assertEqual(x["review_lifecycle"],
                         "INCOMPLETE_LATEST_PAIRED_SYNTHETIC_STUDY_HOLD")
        self.assertEqual(x["historical_source_change_hold_count"],0)
        self.assertFalse(x["original_falsifiable_candidates"][0]["export_allowed"])

    def test_revised_candidate_retains_affected_only_tests(self):
        x = improve.reassess_library_hypotheses(self.make(self.revised))
        tests = x["bounded_retest_proposal"]
        self.assertIn("test_ucie_v2_generalization_transfer_v01.py", tests)
        self.assertNotIn("test_ucie_v2_capsule_v01.py", tests)
        self.assertEqual(len(tests),len(set(tests)))

    def test_prior_events_not_mutated(self):
        h = self.make(self.clean, self.revised)
        before = deepcopy(h)
        improve.reassess_library_hypotheses(h)
        self.assertEqual(h,before)

    def test_duplicate_history_not_silent_new_candidate(self):
        h = self.make(self.clean,self.clean)
        self.assertEqual(improve.reassess_library_hypotheses(h)["observed_review_events"],1)

    def test_forged_source_version_even_rehashed_denied(self):
        h = self.make(self.clean)
        h["events"][0]["bundle"]["chapter"]["source_lineage"][0]["document_sha256"] = "a"*64
        h["events"][0]["bundle"]["content_sha256"] = original._digest({
            k:v for k,v in h["events"][0]["bundle"].items() if k != "content_sha256"
        })
        rehash(h)
        with self.assertRaises(history.ReviewHistoryError):
            improve.reassess_library_hypotheses(h)

    def test_fake_retest_name_even_rehashed_denied(self):
        h = self.make(self.revised)
        h["events"][0]["bundle"]["revision"]["proposed_affected_only_tests"].append(
            "execute_anything.py")
        h["events"][0]["bundle"]["content_sha256"] = original._digest({
            k:v for k,v in h["events"][0]["bundle"].items() if k != "content_sha256"
        })
        rehash(h)
        with self.assertRaises(improve.HypothesisImprovementError):
            improve.reassess_library_hypotheses(h)

    def test_fake_active_after_incomplete_even_rehashed_denied(self):
        h = self.make(self.incomplete)
        h["events"][0]["bundle"]["revision"]["review_status"] = "REVIEW_ACTIVE_UNVERIFIED"
        h["events"][0]["bundle"]["content_sha256"] = original._digest({
            k:v for k,v in h["events"][0]["bundle"].items() if k != "content_sha256"
        })
        rehash(h)
        with self.assertRaises(improve.HypothesisImprovementError):
            improve.reassess_library_hypotheses(h)

    def test_fake_source_change_hold_with_no_changed_source_denied(self):
        h = self.make(self.revised)
        h["events"][0]["bundle"]["revision"]["changed_source_ids"] = []
        h["events"][0]["bundle"]["content_sha256"] = original._digest({
            k:v for k,v in h["events"][0]["bundle"].items() if k != "content_sha256"
        })
        rehash(h)
        with self.assertRaises(improve.HypothesisImprovementError):
            improve.reassess_library_hypotheses(h)

    def test_no_real_qa_rights_release_or_side_effect_claims(self):
        x = improve.reassess_library_hypotheses(self.make(self.clean))
        for key in ("source_revision_authenticated","real_user_study_completed",
                    "independent_qa_verified","rights_approved",
                    "automatic_experiment_scheduled","model_training_performed",
                    "customer_release_authorized"):
            self.assertFalse(x[key])
        self.assertEqual(x["operating_database_writes"],0)
        self.assertEqual(x["network_requests"],0)
        for c in x["original_falsifiable_candidates"]:
            self.assertFalse(c["actual_tests_executed"])
            self.assertFalse(c["real_new_principle_discovered_by_model"])
