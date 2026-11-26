"""Offline regression for UCIE cost router; no GitHub calls or Actions triggering."""
import unittest
from scripts.ucie_actions_cost_router_v01 import classify


class RouterTests(unittest.TestCase):
    def test_docs_fast_not_merge(self):
        r = classify(["docs/README.md"])
        self.assertEqual(r["checks_required"], ["FAST_PY315"])
        self.assertFalse(r["release_authorized"])
        self.assertFalse(r["github_checks_run"])

    def test_docs_full_merge(self):
        self.assertEqual(len(classify(["docs/README.md"], "MERGE_CANDIDATE")["checks_required"]), 4)

    def test_core_requires_four(self):
        self.assertEqual(len(classify(["src/ucie_miner/core.py"])["checks_required"]), 4)

    def test_unknown_extension_requires_four(self):
        self.assertEqual(len(classify(["brand-new/build.toml"])["checks_required"]), 4)

    def test_actions_changes_require_four(self):
        self.assertEqual(len(classify([".github/workflows/stage1-offline-tests.yml"])["checks_required"]), 4)

    def test_b4_powershell_requires_native_and_matrix(self):
        r = classify(["src/ucie_miner/ucie_v2_b4_powershell_heldout_v01.py"])
        self.assertEqual(len(r["checks_required"]), 5)
        self.assertIn("NATIVE_POWERSHELL", r["checks_required"])

    def test_browser_and_mcp_merge_native(self):
        r = classify(["src/ucie_miner/ucie_v2_beginner_preview_v01.py",
                      "src/ucie_miner/mcp_prompt_regression_v01.py"], "MERGE_CANDIDATE")
        self.assertIn("NATIVE_BROWSER", r["checks_required"])
        self.assertIn("NATIVE_MCP", r["checks_required"])

    def test_selected_native_requires_a_match(self):
        with self.assertRaises(ValueError):
            classify(["docs/README.md"], "MANUAL_SPECIALIZED")

    def test_native_only_not_full_release(self):
        r = classify(["tests/test_ucie_v2_g3_isolated_browser_v01.py"], "MANUAL_SPECIALIZED")
        self.assertEqual(r["checks_required"], ["NATIVE_BROWSER"])
        self.assertFalse(r["release_authorized"])

    def test_reject_traversal(self):
        for path in ("../x", "src/../x", "/tmp/x", "C:/x", "x\\evil.py",
                     "a//b", ".", "", "~/.secret"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                classify([path])

    def test_reject_duplicate(self):
        with self.assertRaises(ValueError):
            classify(["docs/a.md", "docs/a.md"])

    def test_reject_empty_and_too_many(self):
        for paths in ([], [f"docs/d{i}.md" for i in range(201)]):
            with self.assertRaises(ValueError):
                classify(paths)

    def test_reject_invalid_mode(self):
        with self.assertRaises(ValueError):
            classify(["docs/a.md"], "SKIP_ALL")

    def test_never_claims_ci_or_owner_authority(self):
        for mode in ("PR_ITERATION", "MERGE_CANDIDATE"):
            r = classify(["tests/test_a.py"], mode)
            for key in ("github_checks_run", "native_browser_or_owner_qa_pass",
                        "auto_promoted", "owner_activation_approved", "release_authorized",
                        "required_check_skipped_as_pass", "operating_database_written"):
                self.assertIs(r[key], False)


if __name__ == "__main__":
    unittest.main()
