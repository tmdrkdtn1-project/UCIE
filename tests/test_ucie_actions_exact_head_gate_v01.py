"""Offline only: UCIE exact-HEAD route gate safety regression."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.ucie_actions_exact_head_gate_v01 import classify, run

class Routing(unittest.TestCase):
    def test_fast_docs_not_merge(self):
        r=classify(["docs/notes.md"], "PR_ITERATION")
        self.assertEqual(len(r["matrix"]), 1)
        self.assertFalse(r["merge_accepted"])
    def test_full_merging_docs(self):
        self.assertEqual(len(classify(["docs/notes.md"], "MERGE_CANDIDATE")["matrix"]), 4)
    def test_unreviewed_code_is_full(self):
        self.assertEqual(len(classify(["src/ucie_miner/new.py"], "PR_ITERATION")["matrix"]), 4)
    def test_new_unknown_is_full(self):
        self.assertTrue(classify(["new/unknown.xyz"], "PR_ITERATION")["unknown"])
    def test_scripts_change_is_full(self):
        self.assertEqual(len(classify(["scripts/new_development_task.py"], "PR_ITERATION")["matrix"]), 4)
    def test_workflow_is_full(self):
        self.assertEqual(len(classify([".github/workflows/ucie.yml"], "PR_ITERATION")["matrix"]), 4)
    def test_specialized_native_required(self):
        cases={"BROWSER": "src/ucie_miner/ucie_v2_beginner_preview_v01.py",
               "POWERSHELL": "src/ucie_miner/ucie_v2_b4_powershell_heldout_v01.py",
               "MCP": "src/ucie_miner/mcp_prompt_regression_v01.py"}
        for kind,path in cases.items():
            with self.subTest(kind=kind):
                self.assertIn(kind,classify([path],"PR_ITERATION")["native_required"])
    def test_traversal_and_duplicates_blocked(self):
        for paths in ([],["a/../b"],["src//a"],["-a"],["/etc/a"],
                      ["C:/a"],["a\\b"],["a\0b"],["docs/a","docs/a"]):
            with self.subTest(paths=paths),self.assertRaises(ValueError):
                classify(paths,"PR_ITERATION")
    def test_unsafe_mode_denied(self):
        with self.assertRaises(ValueError):
            classify(["docs/a"],"SKIP_ALL")
    def test_no_forged_authorization(self):
        for mode in ("MERGE_CANDIDATE","PR_ITERATION"):
            r=classify(["src/ucie_miner/core.py"],mode)
            self.assertFalse(r["release_authorized"])
            self.assertFalse(r["owner_host_accepted"])
            self.assertFalse(r["merge_accepted"])

class ExactGit(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.root=Path(self.t.name)
        def git(*args):
            return subprocess.check_output(["git","-C",str(self.root),*args],stderr=subprocess.DEVNULL).decode().strip()
        self.git=git
        git("init","-q")
        git("config","user.name","UCIE-Test")
        git("config","user.email","ucie@example.invalid")
        (self.root/"docs").mkdir()
        (self.root/"docs/a.md").write_text("before")
        git("add",".")
        git("commit","-qm","base")
        self.base=git("rev-parse","HEAD")
        (self.root/"docs/a.md").write_text("after")
        git("add",".")
        git("commit","-qm","next")
        self.head=git("rev-parse","HEAD")
    def tearDown(self):
        self.t.cleanup()
    def test_real_diff_pins(self):
        r=run(self.base,self.head,"PR_ITERATION",str(self.root))
        self.assertEqual(r["changed_paths"],["docs/a.md"])
        self.assertEqual(r["head_sha"],self.head)
    def test_false_head_blocked(self):
        with self.assertRaises(ValueError):
            run(self.head,self.base,"PR_ITERATION",str(self.root))
    def test_stale_or_forged_base(self):
        for base in ("0"*40,"bad",self.head):
            with self.subTest(base=base),self.assertRaises((ValueError,subprocess.CalledProcessError)):
                run(base,self.head,"MERGE_CANDIDATE",str(self.root))

if __name__=="__main__":
    unittest.main()
