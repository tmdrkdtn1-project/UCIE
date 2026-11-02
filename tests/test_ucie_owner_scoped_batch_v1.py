"""UCIE-only scoped consent and transaction offline safety tests."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import owner_scoped_batch_v1 as s

NOW = datetime(2026, 11, 2, 4, 0, tzinfo=timezone.utc)
HEAD = "a" * 40


def item(name="src/ucie_miner/scoped_example_v1.py", data=b"VALUE = 1\n", before="ABSENT"):
    return {"path": name, "before_sha256": before,
            "after_sha256": sha256(data).hexdigest(),
            "content_b64": base64.b64encode(data).decode("ascii")}


def bundle(*files):
    return {"schema": "UCIE_PINNED_DEV_QA_BUNDLE_V1", "commit_sha": HEAD,
            "files": list(files or (item(),))}


class ScopedUnitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ucie-scoped-tests-")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root, self.hub = base / "UCIE", base / "UCIE_HUB"
        for path in (self.root / "src/ucie_miner", self.root / "tests",
                     self.hub / "04_MIGRATION/UCIE_OWNER_SCOPED_QA_V1"):
            path.mkdir(parents=True)

    def enroll(self):
        return s.enroll(self.root, self.hub, consent=s.CONSENT,
                        now=NOW, test_mode=True)

    @staticmethod
    def good_ci(commit, hashes):
        if commit != HEAD or not hashes:
            raise AssertionError("trusted fake wrong")
        return True

    def apply(self, b, **kwargs):
        return s.apply_verified_batch(
            self.root, self.hub, b, verify_ci_and_sources=self.good_ci,
            now=NOW, test_mode=True, **kwargs)

    def test_inert_import_without_grant(self):
        b = bundle()
        with self.assertRaises(s.ScopeError):
            self.apply(b)
        self.assertFalse((self.root / b["files"][0]["path"]).exists())

    def test_explicit_consent_enroll(self):
        grant = self.enroll()
        self.assertEqual(grant["max_batches"], 12)
        self.assertEqual(grant["used_batches"], 0)
        self.assertFalse(grant["revoked"])
        self.assertEqual(grant["schema"], s.SCHEMA)

    def test_enroll_denies_bad_phrase(self):
        with self.assertRaises(s.ScopeError):
            s.enroll(self.root, self.hub, consent="yes", now=NOW, test_mode=True)

    def test_enroll_denies_duplicate(self):
        self.enroll()
        with self.assertRaises(s.ScopeError):
            self.enroll()

    def test_production_host_paths_rejected_off_windows(self):
        if __import__("os").name != "nt":
            with self.assertRaises(s.ScopeError):
                s.enroll(self.root, self.hub, consent=s.CONSENT)

    def test_bundle_unknown_fields_rejected(self):
        with self.assertRaises(s.ScopeError):
            s.validate_bundle(dict(bundle(), auto_approved=True))

    def test_commit_sha_enforced(self):
        b = bundle()
        b["commit_sha"] = "not-a-commit"
        with self.assertRaises(s.ScopeError):
            s.validate_bundle(b)

    def test_path_traversal_rejected(self):
        for name in ("../secrets.py", "src/ucie_miner/../worker.py",
                     "/src/ucie_miner/x.py", "src\\ucie_miner\\bad.py",
                     "src/ucie_miner/worker.py", "scripts/new_task.py",
                     "runtime/something.py", ".github/workflows/anything.yml",
                     "tests/test_other.py"):
            with self.subTest(name=name), self.assertRaises(s.ScopeError):
                s.validate_bundle(bundle(item(name=name)))

    def test_duplicate_target_rejected(self):
        with self.assertRaises(s.ScopeError):
            s.validate_bundle(bundle(item(), item()))

    def test_excessive_entries_rejected(self):
        files = [item(f"src/ucie_miner/qa_test_{i:02}.py") for i in range(7)]
        with self.assertRaises(s.ScopeError):
            s.validate_bundle(bundle(*files))

    def test_empty_and_wrong_type_rejected(self):
        for data in ([], {}, None, [None]):
            with self.subTest(data=data), self.assertRaises(s.ScopeError):
                s.validate_bundle({"schema": "UCIE_PINNED_DEV_QA_BUNDLE_V1",
                                   "commit_sha": HEAD, "files": data})

    def test_sha_mutation_rejected(self):
        record = item()
        record["after_sha256"] = "b" * 64
        with self.assertRaises(s.ScopeError):
            s.validate_bundle(bundle(record))

    def test_invalid_utf8_rejected(self):
        with self.assertRaises(s.ScopeError):
            s.validate_bundle(bundle(item(data=b"\xff\xfe")))

    def test_binary_nul_rejected(self):
        with self.assertRaises(s.ScopeError):
            s.validate_bundle(bundle(item(data=b"A\x00B")))

    def test_max_bytes_rejected(self):
        with self.assertRaises(s.ScopeError):
            s.validate_bundle(bundle(item(data=b"a" * (s.MAX_FILE_BYTES + 1))))

    def test_untrusted_ci_no_files_changed(self):
        self.enroll()
        self.assertRaises(s.ScopeError, s.apply_verified_batch,
                          self.root, self.hub, bundle(),
                          verify_ci_and_sources=lambda *_: False,
                          now=NOW, test_mode=True)
        self.assertFalse((self.root / "src/ucie_miner/scoped_example_v1.py").exists())

    def test_insert_and_consumption(self):
        self.enroll()
        result = self.apply(bundle())
        self.assertEqual(result["files_changed"], 1)
        self.assertFalse(result["auto_promoted"])
        self.assertFalse(result["code_executed_after_sync"])
        self.assertEqual((self.root / "src/ucie_miner/scoped_example_v1.py").read_bytes(), b"VALUE = 1\n")
        _, grant = s._grant(self.hub, now=NOW)
        self.assertEqual(grant["used_batches"], 1)

    def test_reject_unknown_live_change_without_overwriting(self):
        self.enroll()
        target = self.root / "src/ucie_miner/scoped_example_v1.py"
        target.write_bytes(b"LOCAL_EDIT = 1\n")
        with self.assertRaises(s.ScopeError):
            self.apply(bundle())
        self.assertEqual(target.read_bytes(), b"LOCAL_EDIT = 1\n")

    def test_authorized_exact_replacement(self):
        self.enroll()
        target = self.root / "src/ucie_miner/scoped_example_v1.py"
        target.write_bytes(b"VALUE = 0\n")
        before = sha256(target.read_bytes()).hexdigest()
        self.apply(bundle(item(before=before)))
        self.assertEqual(target.read_bytes(), b"VALUE = 1\n")

    def test_reject_replay_by_batch_id(self):
        self.enroll()
        b = bundle()
        self.apply(b)
        with self.assertRaises(s.ScopeError):
            self.apply(b)

    def test_rollback_new_file_when_second_fails(self):
        self.enroll()
        b = bundle(item(), item(name="tests/test_ucie_extra_qa.py"))
        with self.assertRaises(OSError):
            self.apply(b, fail_after=2)
        for rec in b["files"]:
            self.assertFalse((self.root / rec["path"]).exists())
        _, grant = s._grant(self.hub, now=NOW)
        self.assertEqual(grant["used_batches"], 0)

    def test_rollback_existing_file_bytes(self):
        self.enroll()
        target = self.root / "src/ucie_miner/scoped_example_v1.py"
        target.write_bytes(b"ORIGINAL_BYTES\r\n")
        original = target.read_bytes()
        b = bundle(item(before=sha256(original).hexdigest()))
        with self.assertRaises(OSError):
            self.apply(b, fail_after=1)
        self.assertEqual(target.read_bytes(), original)

    def test_grant_expired_rejected(self):
        self.enroll()
        with self.assertRaises(s.ScopeError):
            s.apply_verified_batch(self.root, self.hub, bundle(),
                                   verify_ci_and_sources=self.good_ci,
                                   now=NOW + timedelta(days=15), test_mode=True)

    def test_grant_future_dated_rejected(self):
        self.enroll()
        with self.assertRaises(s.ScopeError):
            s._grant(self.hub, now=NOW - timedelta(minutes=1))

    def test_revoked_denied(self):
        self.enroll()
        grant_path = s._grant_path(self.hub)
        grant = json.loads(grant_path.read_bytes())
        grant["revoked"] = True
        grant_path.write_bytes(s._json_bytes(grant))
        with self.assertRaises(s.ScopeError):
            self.apply(bundle())

    def test_grant_overextended_denied(self):
        self.enroll()
        grant_path = s._grant_path(self.hub)
        grant = json.loads(grant_path.read_bytes())
        grant["expires_utc"] = (NOW + timedelta(days=60)).isoformat().replace("+00:00", "Z")
        grant_path.write_bytes(s._json_bytes(grant))
        with self.assertRaises(s.ScopeError):
            self.apply(bundle())

    def test_batch_count_exhaustion(self):
        self.enroll()
        grant_path = s._grant_path(self.hub)
        grant = json.loads(grant_path.read_bytes())
        grant["used_batches"] = 12
        grant_path.write_bytes(s._json_bytes(grant))
        with self.assertRaises(s.ScopeError):
            self.apply(bundle())

    def test_mutex_blocks_second_apply(self):
        self.enroll()
        with s._exclusive_scope_lock(self.hub):
            with self.assertRaises(s.ScopeError):
                self.apply(bundle())

    def test_symbolic_link_path_rejected(self):
        self.enroll()
        with patch.object(Path, "is_symlink", autospec=True,
                          side_effect=lambda p: str(p).endswith("scoped_example_v1.py")):
            with self.assertRaises(s.ScopeError):
                self.apply(bundle())

    def _github_fixture(self, *, incomplete=False, source_changed=False):
        data = b"VALUE = 1\n"
        source_path = "src/ucie_miner/scoped_example_v1.py"
        blob = __import__("hashlib").sha1(
            ("blob " + str(len(data)) + "\x00").encode("ascii") + data).hexdigest()
        contents = {"encoding": "base64", "content": base64.b64encode(
            data if not source_changed else b"MALICIOUS = 1\n").decode("ascii"),
                    "sha": blob}
        run = {"id": 123, "head_sha": HEAD, "path": s.WORKFLOW,
               "status": "completed", "conclusion": "success",
               "head_repository": {"full_name": s.REPO}}
        jobs = [{"name": name, "conclusion": "success", "status": "completed"}
                for name in sorted(s.JOBS)]
        if incomplete:
            jobs.pop()
        def fake(endpoint):
            if "actions/runs?head_sha=" in endpoint:
                return {"workflow_runs": [run]}
            if "actions/runs/123/jobs" in endpoint:
                return {"jobs": jobs, "total_count": len(jobs)}
            if "contents/" in endpoint:
                self.assertIn(source_path, endpoint)
                return contents
            raise AssertionError("unexpected remote URL")
        return fake

    def test_github_exact_ci_and_blob(self):
        with patch.object(s, "_github_json", side_effect=self._github_fixture()):
            self.assertTrue(s.verify_github_ci_and_source_blobs(
                HEAD, {"src/ucie_miner/scoped_example_v1.py": sha256(b"VALUE = 1\n").hexdigest()}))

    def test_github_partial_matrix_rejected(self):
        with patch.object(s, "_github_json", side_effect=self._github_fixture(incomplete=True)):
            with self.assertRaises(s.ScopeError):
                s.verify_github_ci_and_source_blobs(
                    HEAD, {"src/ucie_miner/scoped_example_v1.py": sha256(b"VALUE = 1\n").hexdigest()})

    def test_github_content_mismatch_rejected(self):
        with patch.object(s, "_github_json", side_effect=self._github_fixture(source_changed=True)):
            with self.assertRaises(s.ScopeError):
                s.verify_github_ci_and_source_blobs(
                    HEAD, {"src/ucie_miner/scoped_example_v1.py": sha256(b"VALUE = 1\n").hexdigest()})

    def test_github_wrong_repo_or_sha_rejected(self):
        def fake(endpoint):
            return {"workflow_runs": [{"id": 1, "head_sha": "b" * 40,
                      "path": s.WORKFLOW, "status": "completed",
                      "conclusion": "success", "head_repository": {"full_name": s.REPO}}]}
        with patch.object(s, "_github_json", side_effect=fake):
            with self.assertRaises(s.ScopeError):
                s.verify_github_ci_and_source_blobs(
                    HEAD, {"src/ucie_miner/scoped_example_v1.py": sha256(b"VALUE = 1\n").hexdigest()})

    def test_github_duplicate_qualified_run_rejected(self):
        def fake(endpoint):
            good = {"id": 1, "head_sha": HEAD, "path": s.WORKFLOW,
                    "status": "completed", "conclusion": "success",
                    "head_repository": {"full_name": s.REPO}}
            return {"workflow_runs": [good, good]}
        with patch.object(s, "_github_json", side_effect=fake):
            with self.assertRaises(s.ScopeError):
                s.verify_github_ci_and_source_blobs(
                    HEAD, {"src/ucie_miner/scoped_example_v1.py": sha256(b"VALUE = 1\n").hexdigest()})

    def test_github_unapproved_source_path_rejected_preflight(self):
        with self.assertRaises(s.ScopeError):
            s.verify_github_ci_and_source_blobs(HEAD, {"scripts/install_hourly_task.ps1": "a"*64})

    def test_real_ci_callback_blocked_on_exception(self):
        self.enroll()
        with patch.object(s, "verify_github_ci_and_source_blobs", side_effect=s.ScopeError("HTTP_DOWN")):
            with self.assertRaises(s.ScopeError):
                s.apply_verified_batch(self.root, self.hub, bundle(),
                    verify_ci_and_sources=s.verify_github_ci_and_source_blobs,
                    now=NOW, test_mode=True)
        self.assertFalse((self.root / "src/ucie_miner/scoped_example_v1.py").exists())

    def test_no_exec_or_scheduler_in_tested_source(self):
        text = Path(s.__file__).read_text(encoding="utf-8")
        self.assertNotIn("subprocess.run(", text)
        self.assertNotIn("subprocess.Popen(", text)
        self.assertNotIn("schtasks", text)
        self.assertNotIn("sqlite3.connect", text)


if __name__ == "__main__":
    unittest.main()