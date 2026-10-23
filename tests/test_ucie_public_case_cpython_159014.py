"""Synthetic regression for the fixed CPython documentation-only PR #159014.

No public GET or arbitrary upstream patch execution during unit tests. All
fixtures are UCIE-authored and the current CPython behavior observer is
injected with typed values. A separate workflow-gated disposable runner
performs the actual independent-of-owner-host runtime observation.
"""
from copy import deepcopy
import unittest

from ucie_miner.public_discovery import DiscoveryError
from ucie_miner.public_case_cpython_159014 import (
    API_REQUEST, FILE_REQUEST, FILES, MERGED_UTC, PINNED_MERGE_SHA,
    PR, SCHEMA, SOURCE, URL, inspect_cpython_159014_observation,
)

PATCH_HOWTO = (
    "@@ -16,7 +16,7 @@\n"
    "-* Use the :option:`-X disable_remote_debug` command-line option.\n"
    "+* Use the :option:`-X disable-remote-debug` command-line option."
)
PATCH_CLI = (
    "@@ -652,7 +652,7 @@ Miscellaneous options\n"
    "-   * ``-X disable_remote_debug`` disables the remote debugging support\n"
    "+   * ``-X disable-remote-debug`` disables the remote debugging support"
)


def pr():
    return {
        "number": PR, "state": "closed",
        "html_url": URL, "merged_at": MERGED_UTC,
        "merge_commit_sha": PINNED_MERGE_SHA, "changed_files": 2,
        "base": {"repo": {"full_name": SOURCE}},
    }


def files():
    return [
        {"filename": FILES[0], "status": "modified", "patch": PATCH_HOWTO},
        {"filename": FILES[1], "status": "modified", "patch": PATCH_CLI},
    ]


class KnownCPythonCandidateTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.meta = pr()
        self.changed = files()
        self.runtime_calls = []

    def fetch(self, url):
        self.calls.append(url)
        if url == API_REQUEST:
            return self.meta, 40
        if url == FILE_REQUEST:
            return self.changed, 40
        raise AssertionError("unexpected third/foreign API request")

    def observe(self, args):
        self.runtime_calls.append(args)
        return {(): True,
                ("-X", "disable_remote_debug"): True,
                ("-X", "disable-remote-debug"): False}[tuple(args)]

    def run_candidate(self):
        return inspect_cpython_159014_observation(
            fetch=self.fetch, observe=self.observe,
            runtime_name="CPython", runtime_version="3.15.1",
            platform="linux")

    def test_complete_synthetic_candidate_binding_never_claims_independent_qa(self):
        report = self.run_candidate()
        self.assertEqual(self.calls, [API_REQUEST, FILE_REQUEST])
        self.assertEqual(self.runtime_calls, [
            [], ["-X", "disable_remote_debug"], ["-X", "disable-remote-debug"]])
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["pinned_merge_sha"], PINNED_MERGE_SHA)
        self.assertEqual(report["status"],
                         "SYNTHETIC_PUBLIC_TRANSPORT_RUNTIME_OBSERVATION_NO_GO")
        self.assertTrue(report["documentation_correction_observed"])
        self.assertTrue(report["corrected_documented_option_disabled_remote_debug"])
        self.assertEqual(report["public_api_gets"], 0)
        self.assertFalse(report["receipt_sha256_is_signature"])
        for field in (
            "all_affected_versions_tested",
            "published_release_inclusion_independently_attested",
            "license_independently_signed_off",
            "security_independent_human_review",
            "independent_reviewers_attested",
            "owner_release_authorized",
            "production_approved",
            "untrusted_patch_executed",
        ):
            self.assertFalse(report[field])
        self.assertEqual(report["automatic_rule_promotions"], 0)

    def test_mismatched_source_sha_and_foreign_repo_fail_before_second_fetch(self):
        for changes in ({"merge_commit_sha": "b" * 40},
                        {"base": {"repo": {"full_name": "unknown/repo"}}},
                        {"changed_files": 1000},
                        {"merged_at": "2027-01-01T00:00:00Z"}):
            with self.subTest(changes=changes):
                self.calls = []
                self.meta = {**pr(), **changes}
                with self.assertRaises(DiscoveryError):
                    self.run_candidate()
                self.assertEqual(self.calls, [API_REQUEST])

    def test_wrong_document_paths_and_missing_patch_fail_closed(self):
        for edits in (
            lambda rows: rows[0].update(filename="Lib/private.py"),
            lambda rows: rows[1].update(patch="+ NOT_CORRECTED"),
            lambda rows: rows[0].update(patch=rows[0]["patch"][:10]),
            lambda rows: rows[1].update(status="removed"),
            lambda rows: rows.append(deepcopy(rows[-1])),
        ):
            with self.subTest(edit=edits):
                self.changed = files()
                edits(self.changed)
                with self.assertRaises(DiscoveryError):
                    self.run_candidate()

    def test_wrong_runtime_or_invariant_fails_closed(self):
        for name, version, platform in (
            ("Python", "3.15.1", "linux"),
            ("CPython", "3.13.4", "linux"),
            ("CPython", "3.15.1", "darwin"),
        ):
            with self.subTest(name=name, version=version, platform=platform):
                with self.assertRaises(DiscoveryError):
                    inspect_cpython_159014_observation(
                        fetch=self.fetch, observe=self.observe,
                        runtime_name=name, runtime_version=version,
                        platform=platform)
        with self.assertRaises(DiscoveryError):
            inspect_cpython_159014_observation(
                fetch=self.fetch, observe=lambda args: 1,
                runtime_name="CPython", runtime_version="3.15.1",
                platform="win32")

    def test_rate_pause_and_transport_invalid_are_denied(self):
        def rate(url):
            data, _ = self.fetch(url)
            return data, 4
        with self.assertRaises(DiscoveryError):
            inspect_cpython_159014_observation(
                fetch=rate, observe=self.observe, runtime_name="CPython",
                runtime_version="3.15.1", platform="linux")
        def invalid(url):
            return ({}, True)
        with self.assertRaises(DiscoveryError):
            inspect_cpython_159014_observation(
                fetch=invalid, observe=self.observe, runtime_name="CPython",
                runtime_version="3.15.1", platform="linux")


if __name__ == "__main__":
    unittest.main()
