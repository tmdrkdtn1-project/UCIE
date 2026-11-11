"""Python four-pillar read-only source-guide integration, no real user data."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote
import json
import unittest

from ucie_miner import local_v1_app_v01 as app
from ucie_miner import python_scandir_guide_v01 as guide


class PythonScandirGuideIntegrationTests(unittest.TestCase):
    def test_guide_model_is_unapproved_and_does_not_execute_trial(self):
        with patch(
            "ucie_miner.python_scandir_review_v01._evaluate_only_ucie_synthetic_inputs",
            side_effect=AssertionError("guide must never launch a test"),
        ) as trial:
            report = guide.build_readonly_guide()
            self.assertEqual(report["schema"], guide.SCHEMA)
            self.assertEqual(len(report["chapters"]), 5)
            self.assertFalse(report["export_allowed"])
            self.assertFalse(report["auto_promoted"])
            self.assertFalse(report["customer_release_authorized"])
            self.assertFalse(report["review_gates"]["source_revision_pinned"])
            self.assertEqual(report["network_requests"], 0)
            self.assertEqual(report["operating_database_writes"], 0)
            self.assertEqual(report["machine_skill_contract"]["synthetic_files"], 4)
            html = app._python_review_guide("")
            self.assertIn("PUBLIC_DOCUMENT_REVISION_NOT_PINNED", html)
            self.assertIn("NOT_ATTESTED_PER_REVISION", html)
            self.assertIn("/local/engine?purpose=PYTHON_SCANDIR_SAFE", html)
            raw = json.loads(app._python_review_guide("", json_mode=True))
            self.assertEqual(raw, report)
            trial.assert_not_called()

    def test_guide_rejects_query_arguments(self):
        with self.assertRaises(app.LocalProductError):
            app._python_review_guide("approved=true")

    def test_tampering_never_turns_draft_into_approval(self):
        original = guide.build_readonly_guide()
        for key, value in (
            ("export_allowed", True),
            ("auto_promoted", True),
            ("customer_release_authorized", True),
        ):
            with self.subTest(key=key):
                forged = dict(original, **{key: value})
                with patch.object(guide, "build_readonly_guide",
                                  return_value=forged):
                    with self.assertRaises(app.LocalProductError):
                        app._python_review_guide("")

    def test_prevention_links_without_promoting(self):
        with patch.object(app, "_paged_evidence", return_value="<p>W04</p>"):
            html = app._error(Path("UCIE"), "q=Python")
        self.assertIn("/local/guide/python-scandir", html)
        self.assertIn("버전·권리·독립 검증은 미완료", html)
        self.assertNotIn("CUSTOMER_RELEASE_GO", html)

    def test_engine_and_library_link_are_explicit(self):
        # Engine uses a previously implemented first-party synthetic fixture.
        with patch(
            "ucie_miner.python_scandir_review_v01._evaluate_only_ucie_synthetic_inputs",
            return_value={
                "synthetic_file_count": 4,
                "concurrent_guarded_consumers": 2,
                "unique_entries_match": True,
                "sequential_control_match": True,
                "closed_iterator_stops": True,
                "temporary_synthetic_files_removed": True,
                "unsafe_raw_iterator_race_executed": False,
                "external_repository_source_executed": False,
                "customer_or_other_project_files_opened": False,
            },
        ):
            html = app._engine("purpose=PYTHON_SCANDIR_SAFE", root=Path("UCIE"))
        self.assertIn("/local/guide/python-scandir", html)

    def test_evolution_links_without_changing_existing_public_search(self):
        from ucie_miner.public_collection_inventory_v01 import SCHEMA
        inventory = {
            "schema": SCHEMA,
            "status": "READ_ONLY_UNVERIFIED",
            "issues": [],
            "legacy_miner": {},
            "stage10_public_candidate_staging": {},
            "operating_database_writes": 0,
        }
        with patch(
            "ucie_miner.public_collection_inventory_v01.collection_inventory",
            return_value=inventory,
        ), patch.object(app, "_paged_evidence", return_value="<p>W04</p>") as search:
            html = app._evolution(Path("UCIE"), "q=Python")
        self.assertIn("/local/guide/python-scandir", html)
        self.assertIn("서로 다른 근거", html)
        search.assert_called_once()

    def test_invalid_guide_source_does_not_render(self):
        with patch(
            "ucie_miner.python_scandir_guide_v01._source_bound_entry",
            return_value=(
                {"source_id": "doc:python/cpython",
                 "source_kind": "OFFICIAL_PUBLIC_DOCUMENT",
                 "public_url": "https://unauthorized.invalid/os.html",
                 "license_verdict": "NOT_ATTESTED_PER_REVISION",
                 "fetch_authorized_by_this_registry": False},
                {},
            ),
        ):
            with self.assertRaises(guide.PythonScandirGuideError):
                guide.build_readonly_guide()


if __name__ == "__main__":
    unittest.main()
