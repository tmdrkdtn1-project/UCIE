"""ACG zero-Draft source contract: no GitHub call, no customer data."""
from pathlib import Path
from unittest import TestCase

WF = Path(__file__).resolve().parents[1] / ".github/workflows/stage1-offline-tests.yml"


def should_run(event, action="", draft=False, label=""):
    return event == "push" or (event == "pull_request" and (
        (action == "labeled" and label == "ucie-full-ci") or
        (action == "ready_for_review" and not draft) or
        (not draft and action in ("opened", "reopened", "synchronize"))
    ))


class ACGDraftZeroTests(TestCase):
    def test_draft_updates_no_runner(self):
        for action in ("opened", "reopened", "synchronize", "unlabeled"):
            self.assertFalse(should_run("pull_request", action, True))

    def test_old_label_draft_synchronize_no_repeat(self):
        self.assertFalse(should_run("pull_request", "synchronize", True, "ucie-full-ci"))

    def test_exact_checkpoint_new_label_only(self):
        self.assertTrue(should_run("pull_request", "labeled", True, "ucie-full-ci"))
        self.assertFalse(should_run("pull_request", "labeled", True, "other"))

    def test_nondraft_recheck_every_revision(self):
        for action in ("opened", "reopened", "synchronize", "ready_for_review"):
            self.assertTrue(should_run("pull_request", action, False))

    def test_main_push(self):
        self.assertTrue(should_run("push"))

    def test_workflow_matches_model(self):
        text = WF.read_text(encoding="utf-8")
        self.assertIn("github.event.action == 'ready_for_review' && !github.event.pull_request.draft", text)
        self.assertIn("github.event.action == 'labeled' && github.event.label.name == 'ucie-full-ci'", text)
        self.assertIn("!github.event.pull_request.draft", text)
        self.assertIn("fromJSON", text)
        self.assertNotIn("unlabeled, ready_for_review", text)
        self.assertIn("os: [ubuntu-latest, windows-latest]", text)
        self.assertIn("python-version: ['3.13', '3.15']", text)
        self.assertIn("branches: [main]", text)

    def test_original_full_suite_retained(self):
        text = WF.read_text(encoding="utf-8")
        for token in (
            "python -m unittest discover -s tests -v",
            "tests/runtime_ucie_v1_real_shell_acceptance.ps1",
            "tests/runtime_python_probes.py",
            "tests/runtime_powershell_probes.ps1",
            "powershell.exe -NoProfile -NonInteractive",
        ):
            self.assertIn(token, text)
