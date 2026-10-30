"""UCIE V1 exact-selected W04 public version/rights review; no approvals."""
from __future__ import annotations

from copy import deepcopy
import unittest

from ucie_miner.product_v1 import (
    ProductIntegrationError, _selected_public_release_rights_review,
)
from ucie_miner.p9_pinned_public_review import lookup_pinned_review


class SelectedPublicReleaseRightsTests(unittest.TestCase):
    def _case(self, repo: str, pr: int, merge: str, *, pinned: bool = True):
        source = "repo:" + repo
        url = f"https://github.com/{repo}/pull/{pr}"
        library_id = "a" * 64
        selection = {
            "library_item_id": library_id,
            "shelf": "PUBLIC_CANDIDATE",
            "selection_status": "CANDIDATE_OR_EXPERIENCE_REUSE_BLOCKED",
            "new_generic_package_export_allowed": False,
            "production_auto_apply_allowed": False,
            "version_scope": "UNDETERMINED",
            "source_license_status": "NOT_ATTESTED_PER_REVISION",
        }
        row = {
            "shelf": "W04_PUBLIC_CANDIDATE",
            "library_item_id": library_id,
            "source_id": source, "public_url": url,
            "revision_hint": merge, "evidence_sha256": "b" * 64,
            "version_scope_claim": "UNDETERMINED",
            "source_license_status": "NOT_ATTESTED_PER_REVISION",
            "local_source_linkage_checked": True,
            "runtime_version_applicability_verified": False,
            "source_rights_for_export_verified": False,
            "independent_qa_verified": False, "export_allowed": False,
            "pinned_public_revision_review": (
                lookup_pinned_review(
                    source_id=source, public_url=url, merge_sha=merge)
                if pinned else None),
        }
        readiness = {
            "schema": "UCIE_P9_SOURCE_VERSION_RIGHTS_QA_READINESS_V1",
            "status": "INSPECTED_EVIDENCE_PENDING_REVIEW_NO_GO",
            "rows": [row],
            "all_required_evidence_accepted": False,
            "source_window_truncated": True,
        }
        return selection, readiness

    def test_real_public_release_bug_reproduced_specific_scopes_only(self):
        selected, evidence = self._case(
            "PowerShell/PowerShell", 28087,
            "373f6a7b7972a0a4b73bfd9737a0d768d28b347e")
        output = _selected_public_release_rights_review(
            selection=selected, evidence=evidence)
        self.assertEqual(
            output["status"],
            "EXACT_RELEASE_BUG_REPRODUCED_MANUAL_REVIEW_NO_GO")
        self.assertEqual(output["reproduced_release_binary_scope_count"], 2)
        self.assertEqual(
            {row["platform"] for row in
             output["reproduced_one_release_binary_scopes"]},
            {"linux-x64", "windows-x64"})
        self.assertEqual(output["examined_release_tag"], "v7.6.6")
        for row in output["reproduced_one_release_binary_scopes"]:
            self.assertEqual(row["specific_binary_runtime"], "7.6.6")
            self.assertEqual(
                row["observed_behavior"], "DOT_PREFIX_BUG_REPRODUCED_ONLY")
            self.assertFalse(row["fix_available_in_version_verified"])
            self.assertFalse(row["authorizes_package_distribution"])
            self.assertIn("/actions/runs/", row["observed_ci_job_url"])
        self.assertEqual(output["repository_license_family_observed"], "MIT")
        self.assertTrue(output["repository_license_observed"])
        self.assertFalse(output["exact_runtime_fix_coverage_verified"])
        self.assertFalse(output["all_runtime_versions_supported_verified"])
        self.assertFalse(output["per_revision_redistribution_rights_cleared"])
        self.assertFalse(output["per_file_license_and_notices_review_completed"])
        self.assertFalse(output["external_independent_qa_attested"])
        self.assertFalse(output["new_package_export_allowed"])
        self.assertFalse(output["package_released"])
        self.assertFalse(output["v1_accepted"])
        self.assertEqual(output["network_requests"], 0)
        self.assertEqual(output["operating_database_writes"], 0)
        self.assertTrue(output["source_window_truncated"])
        self.assertEqual(output, _selected_public_release_rights_review(
            selection=selected, evidence=evidence))

    def test_other_exact_pinned_merges_have_no_runtime_version_grant(self):
        for repo, pr, merge, license in (
            ("python/cpython", 153462,
             "999a046b24cff4ba0e72b574196721f66bd08237",
             "PSF-2.0_WITH_COMPONENT_EXCEPTIONS"),
            ("PowerShell/PowerShell", 28042,
             "bd8cb01a7d5b86129c45eaa14ab5830a63b1283f",
             "MIT"),
        ):
            with self.subTest(pr=pr):
                selection, evidence = self._case(repo, pr, merge)
                output = _selected_public_release_rights_review(
                    selection=selection, evidence=evidence)
                self.assertEqual(
                    output["status"],
                    "MERGE_LICENSE_PINNED_RUNTIME_APPLICABILITY_UNKNOWN_NO_GO")
                self.assertEqual(output["repository_license_family_observed"],
                                 license)
                self.assertEqual(output["reproduced_release_binary_scope_count"], 0)
                self.assertFalse(output["exact_runtime_fix_coverage_verified"])
                self.assertFalse(output["per_revision_redistribution_rights_cleared"])
                self.assertFalse(output["v1_accepted"])

    def test_unpinned_or_outside_window_do_not_inherit_release_evidence(self):
        selection, evidence = self._case(
            "python/cpython", 153462, "c" * 40, pinned=False)
        report = _selected_public_release_rights_review(
            selection=selection, evidence=evidence)
        self.assertEqual(
            report["status"], "UNPINNED_PUBLIC_MERGE_NEEDS_MANUAL_REVIEW_NO_GO")
        self.assertIsNone(report["repository_license_family_observed"])
        self.assertEqual(report["reproduced_release_binary_scope_count"], 0)
        self.assertFalse(report["new_package_export_allowed"])
        self.assertIsNone(_selected_public_release_rights_review(
            selection=None, evidence=evidence))
        with self.assertRaises(ProductIntegrationError):
            _selected_public_release_rights_review(
                selection={**selection, "library_item_id": "d" * 64},
                evidence=evidence)
        self.assertIsNone(_selected_public_release_rights_review(
            selection={**selection, "shelf": "SIGNED_MANUAL_RULE"},
            evidence=evidence))

    def test_authorization_forgeries_and_mismatched_revisions_fail_closed(self):
        selection, evidence = self._case(
            "PowerShell/PowerShell", 28087,
            "373f6a7b7972a0a4b73bfd9737a0d768d28b347e")
        for key, forged in (
            ("new_generic_package_export_allowed", True),
            ("production_auto_apply_allowed", True),
            ("source_license_status", "LICENSE_APPROVED"),
            ("version_scope", "7.6.6"),
            ("selection_status", "APPROVED"),
        ):
            with self.subTest(selection=key):
                with self.assertRaises(ProductIntegrationError):
                    _selected_public_release_rights_review(
                        selection={**selection, key: forged}, evidence=evidence)
        for key, forged in (
            ("runtime_version_applicability_verified", True),
            ("source_rights_for_export_verified", True),
            ("independent_qa_verified", True),
            ("export_allowed", True),
            ("revision_hint", "e" * 40),
            ("evidence_sha256", "not-a-hash"),
        ):
            with self.subTest(row=key):
                altered = deepcopy(evidence)
                altered["rows"][0][key] = forged
                with self.assertRaises(ProductIntegrationError):
                    _selected_public_release_rights_review(
                        selection=selection, evidence=altered)
        altered = deepcopy(evidence)
        altered["rows"][0]["pinned_public_revision_review"][
            "official_windows_release_runtime_observation"][
            "production_approved"] = True
        with self.assertRaises(ProductIntegrationError):
            _selected_public_release_rights_review(
                selection=selection, evidence=altered)
        altered = deepcopy(evidence)
        altered["rows"][0]["pinned_public_revision_review"][
            "per_file_third_party_license_cleared"] = True
        with self.assertRaises(ProductIntegrationError):
            _selected_public_release_rights_review(
                selection=selection, evidence=altered)


if __name__ == "__main__":
    unittest.main()
