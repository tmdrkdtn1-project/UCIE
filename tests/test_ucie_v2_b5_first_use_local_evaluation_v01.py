"""B5 three-method, linked B1-B4 local comparison is synthetic-only."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
from ucie_miner import ucie_v2_b5_first_use_local_evaluation_v01 as b5
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as original


class FirstUseEvaluationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=b5.build_b5_readonly_evaluation()

    def test_real_original_comparator_schema_and_methods(self):
        self.assertEqual(self.r["study_id"],original.STUDY_ID)
        self.assertEqual(tuple(x["method"] for x in self.r["comparison_methods"]),
                         original.METHODS)
        self.assertEqual(self.r["case_id"],original.CASE_ID)

    def test_original_b1_b4_capsule_lineage_present(self):
        self.assertEqual(self.r["capsule_id"],
                         "UCIE-CAPSULE-MCP-PROMPTS-GET-20261126-01")
        self.assertEqual(self.r["skillbook_id"],
                         "UCIE-SKILLBOOK-MCP-PROMPTS-003")
        self.assertEqual(len(self.r["lifecycle_sha256"]),64)

    def test_nine_synthetic_rows_do_not_fabricate_comparison_win(self):
        rows=b5.fixed_synthetic_comparison_records()
        self.assertEqual(len(rows),9)
        self.assertEqual(len({(x["method"],x["anonymous_trial_token"])
                              for x in rows}),9)
        result=original.summarize_synthetic_comparison(rows)
        self.assertFalse(result["human_comparison_valid"])
        medians={result["methods"][m]["synthetic_first_action_median_ms"]
                 for m in original.METHODS}
        self.assertEqual(medians,{11000})

    def test_all_methods_same_control_outcome(self):
        for method in self.r["comparison_methods"]:
            stats=method["illustrative_synthetic_only"]
            self.assertEqual(stats["synthetic_count"],3)
            self.assertEqual(stats["synthetic_correct_safe_action_count"],2)
            self.assertEqual(stats["synthetic_false_claim_count"],1)

    def test_human_study_and_buyers_remain_unobserved(self):
        self.assertEqual(self.r["actual_human_trials_collected"],0)
        self.assertEqual(self.r["actual_purchasing_interviews_collected"],0)
        self.assertFalse(self.r["actual_comparative_ux_effect_verified"])
        self.assertTrue(self.r["human_recruitment_and_consent_required"])

    def test_original_b5_target_not_claimed_as_pass(self):
        self.assertEqual(self.r["target_first_safe_action_under_10_seconds_fraction"],0.8)
        self.assertEqual(self.r["material_overclaim_count_target"],0)
        self.assertFalse(self.r["independent_source_qa_verified"])

    def test_render_plain_truthful_table_and_guide(self):
        html=b5.render_b5_evaluation_panel(self.r)
        self.assertIn("실제 비교시험은 아직 수행하지 않았습니다",html)
        self.assertIn("검토용 인공 데이터",html)
        self.assertIn("10초 이내 첫 안전 행동",html)
        self.assertEqual(html.count("<tr>"),4)

    def test_false_human_trial_count_even_rehashed_denied(self):
        bad=deepcopy(self.r)
        bad["actual_human_trials_collected"]=6
        bad["content_sha256"]=b5._sha({k:v for k,v in bad.items()
                                       if k!="content_sha256"})
        with self.assertRaises(b5.B5WalkthroughError):
            b5.render_b5_evaluation_panel(bad)

    def test_false_customer_distribution_even_rehashed_denied(self):
        bad=deepcopy(self.r)
        bad["customer_distribution_authorized"]=True
        bad["content_sha256"]=b5._sha({k:v for k,v in bad.items()
                                       if k!="content_sha256"})
        with self.assertRaises(b5.B5WalkthroughError):
            b5.render_b5_evaluation_panel(bad)

    def test_false_comparison_advantage_even_rehashed_denied(self):
        bad=deepcopy(self.r)
        bad["comparison_methods"][2]["illustrative_synthetic_only"][
            "synthetic_first_action_median_ms"]=1000
        bad["content_sha256"]=b5._sha({k:v for k,v in bad.items()
                                       if k!="content_sha256"})
        with self.assertRaises(b5.B5WalkthroughError):
            b5.render_b5_evaluation_panel(bad)

    def test_no_network_file_or_subprocess(self):
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("network")):
            with patch("subprocess.run",
                       side_effect=AssertionError("subprocess")):
                result=b5.build_b5_readonly_evaluation()
        self.assertEqual(result["operating_database_writes"],0)
        self.assertFalse(result["data_upload_or_post_created"])

    def test_deterministic(self):
        self.assertEqual(self.r,b5.build_b5_readonly_evaluation())
