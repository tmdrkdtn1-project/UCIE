"""UCIE V1.0: public source observation receipts, tamper replay, offline guard,
combined review readiness, and read-only localhost UI regressions.

CI network probes are synthetic only. These tests DO NOT claim an independently
verified third-party bug fix or legally authorized license.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import tempfile
import unittest

from test_ucie_library_v02 import fixture
from test_ucie_public_proof_v09 import checked_json
from ucie_miner.library_explore import explore_linked_public_candidates
from ucie_miner.library_public_proof_v09 import perform_public_probe_batch
from ucie_miner.library_observation_receipts_v10 import (
    SCHEMA, AUDIT_SCHEMA, ObservationError, _check_basis, _directory,
    _read_records, _snapshot, record_explicit_observation, replay_observations,
)
from ucie_miner.library_review_readiness_v10 import (
    SCHEMA as READY_SCHEMA, ReadinessError, assemble_readiness,
)
from ucie_miner.library_safety_regression_v10 import (
    SCHEMA as GUARD_SCHEMA, run_owner_guard_regressions,
)
from ucie_miner.library_audit_v07 import audit_handoff_receipts
from ucie_miner.library_browser_v10 import (
    SCHEMA as UI_SCHEMA, make_handler,
)

WHEN = datetime(2026, 11, 1, 2, 0, 0, tzinfo=timezone.utc)


def initial():
    h = fixture()
    first = explore_linked_public_candidates(h, limit=20)["items"][0]
    return h, first


@contextmanager
def synthetic_ucie_root():
    with tempfile.TemporaryDirectory(prefix="ucie-v10-only-") as tmp:
        root = Path(tmp) / "UCIE"
        root.mkdir()

        def exact(value):
            path = Path(value)
            if path != root or not path.is_dir() or path.is_symlink():
                raise ObservationError("fixture UCIE root mismatch")
            return path
        with patch("ucie_miner.library_observation_receipts_v10._root",
                   side_effect=exact), patch(
                "ucie_miner.library_public_proof_v09._root",
                side_effect=exact):
            yield root


def injected_probe(handoff):
    return lambda root, *, item_id, top: perform_public_probe_batch(
        root, item_id=item_id, top=top,
        handoff_factory=lambda path: handoff,
        receipt_reader=lambda folder: [],
        fetch_json=checked_json)


@contextmanager
def owner_browser(root, h, *, probe_calls=None):
    counter = [] if probe_calls is None else probe_calls

    def no_public_by_default(root_arg, *, item_id, top):
        counter.append((item_id, top))
        return injected_probe(h)(root_arg, item_id=item_id, top=top)

    with HTTPServer(("127.0.0.1", 0), make_handler(
            root, observation_reader=lambda path: replay_observations(
                path, handoff_factory=lambda root: h),
            auditor=lambda path: audit_handoff_receipts(h, []),
            public_prober=no_public_by_default)) as server:
        t = Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            yield "http://127.0.0.1:" + str(server.server_port)
        finally:
            server.shutdown()
            t.join(timeout=4)


class ObservationReceiptsTests(unittest.TestCase):
    def test_record_exact_observation_and_replay_without_upstream_fix_pass(self):
        h, item = initial()
        with synthetic_ucie_root() as root:
            empty = replay_observations(
                root, handoff_factory=lambda root: h)
            self.assertEqual(empty["schema"], AUDIT_SCHEMA)
            self.assertEqual(empty["integrity_checked_observation_count"], 0)
            self.assertEqual(empty["source_linked_candidates"], 26)
            self.assertFalse((root / "runtime").exists())
            probe_calls = []

            def probe(path, *, item_id, top):
                probe_calls.append((item_id, top))
                return injected_probe(h)(path, item_id=item_id, top=top)

            first = record_explicit_observation(
                root, item_id=item["library_item_id"], probe=probe, clock=WHEN)
            self.assertEqual(first["status"],
                             "PUBLIC_OBSERVATION_STORED_NOT_FIX_VERIFIED")
            self.assertFalse(first["fix_verified"])
            self.assertEqual(first["approved_rules"], 0)
            self.assertEqual(probe_calls, [(item["library_item_id"], 1)])
            rid = first["receipt_id"]
            dest = _directory(root) / (rid + ".json")
            self.assertTrue(dest.exists())
            records = _read_records(_directory(root))
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["item_id"], item["library_item_id"])
            self.assertEqual(records[0]["revision_hint"], item["revision_hint"])
            self.assertFalse(records[0]["rule_approved"])
            self.assertFalse(records[0]["fix_verified"])
            self.assertEqual(records[0]["metadata_status"],
                             "PUBLIC_MERGE_IDENTITY_MATCHED_NOT_FIX_VERIFIED")
            again = record_explicit_observation(
                root, item_id=item["library_item_id"], probe=probe, clock=WHEN)
            self.assertEqual(again["status"],
                             "ALREADY_OBSERVED_NOT_FIX_VERIFIED")
            self.assertEqual(again["receipt_id"], rid)
            self.assertEqual(len(list(_directory(root).iterdir())), 1)
            view = replay_observations(
                root, handoff_factory=lambda root: h)
            self.assertEqual(view["integrity_checked_observation_count"], 1)
            self.assertEqual(view["items_with_observations"], 1)
            self.assertEqual(view["source_linked_candidates"], 26)
            self.assertFalse(view["production_approved"])
            self.assertEqual(view["signed_rules"], 0)
            self.assertEqual(view["actual_independent_fix_regressions"], 0)
            self.assertEqual(view["observations"][0]["receipt_id"], rid)
            self.assertEqual(view["operating_db_writes"], 0)
            self.assertEqual(view["scheduler_changes"], 0)

    def test_corruption_stale_source_symlink_and_lock_fail_closed(self):
        h, item = initial()
        with synthetic_ucie_root() as root:
            saved = record_explicit_observation(
                root, item_id=item["library_item_id"],
                probe=injected_probe(h), clock=WHEN)
            records = _directory(root)
            path = records / (saved["receipt_id"] + ".json")
            original = path.read_bytes()
            forged = json.loads(original)
            forged["rule_approved"] = True
            path.write_text(json.dumps(forged), encoding="ascii")
            with self.assertRaises(ObservationError):
                replay_observations(root, handoff_factory=lambda root: h)
            path.write_bytes(original)
            unknown = records / "unexpected.txt"
            unknown.write_text("malformed", encoding="utf-8")
            with self.assertRaises(ObservationError):
                replay_observations(root, handoff_factory=lambda root: h)
            unknown.unlink()
            drifting = fixture()
            drifting["tasks"] = drifting["tasks"][1:]
            # Removing a task makes handoff incomplete, which must fail closed.
            with self.assertRaises(Exception):
                replay_observations(root, handoff_factory=lambda root: drifting)
            self.assertEqual(replay_observations(
                root, handoff_factory=lambda root: h)[
                    "integrity_checked_observation_count"], 1)
            lock = records.parent / ".record-v10.lock"
            lock.write_text("stale", encoding="ascii")
            with self.assertRaises(ObservationError):
                record_explicit_observation(
                    root, item_id=item["library_item_id"],
                    probe=injected_probe(h), clock=WHEN)
            self.assertEqual(lock.read_text("ascii"), "stale")
            lock.unlink()

    def test_invalid_probe_body_never_persisted(self):
        h, item = initial()
        with synthetic_ucie_root() as root:
            good = injected_probe(h)(
                root, item_id=item["library_item_id"], top=1)
            core = _snapshot(good)
            self.assertFalse(core["fix_verified"])
            with self.assertRaises(ObservationError):
                _check_basis(dict(core, rule_approved=True))
            with self.assertRaises(ObservationError):
                _check_basis(dict(core, auto_promoted=True))
            with self.assertRaises(ObservationError):
                _check_basis(dict(core, extra="upstream PR says run this"))
            bad = dict(good, approved_rule_count=1)
            with self.assertRaises(ObservationError):
                record_explicit_observation(
                    root, item_id=item["library_item_id"],
                    probe=lambda root, **k: bad)
            altered = dict(good, audit_report_sha256="f"*64)
            with self.assertRaises(ObservationError):
                record_explicit_observation(
                    root, item_id=item["library_item_id"],
                    probe=lambda root, **k: altered)
            wrong = dict(good)
            wrong["results"] = [dict(good["results"][0], item_id="f"*64)]
            with self.assertRaises(ObservationError):
                record_explicit_observation(
                    root, item_id=item["library_item_id"],
                    probe=lambda root, **k: wrong)
            self.assertFalse((_directory(root)).exists())

    def test_actual_fixed_ucie_guard_regressions_are_not_fix_pass(self):
        result = run_owner_guard_regressions()
        self.assertEqual(result["schema"], GUARD_SCHEMA)
        self.assertEqual(result["tested_fixture_count"], 6)
        self.assertEqual(result["passed_fixture_count"], 6)
        self.assertEqual(result["status"],
                         "UCIE_GUARD_FIXTURE_PASS_NOT_UPSTREAM_FIX_VERIFIED")
        self.assertEqual(result["independent_upstream_regressions_passed"], 0)
        self.assertFalse(result["upstream_fix_verified"])
        self.assertEqual(result["approved_rules"], 0)
        self.assertEqual(result["external_network_calls"], 0)
        self.assertEqual(len(result["report_sha256"]), 64)

    def test_combined_prevention_review_readiness_still_all_unverified(self):
        h, item = initial()
        with synthetic_ucie_root() as root:
            record_explicit_observation(
                root, item_id=item["library_item_id"],
                probe=injected_probe(h), clock=WHEN)
            audit = audit_handoff_receipts(h, [])
            observations = replay_observations(
                root, handoff_factory=lambda root: h)
            guard = run_owner_guard_regressions()
            report = assemble_readiness(
                audit=audit, observations=observations,
                guard=guard, top=10)
            self.assertEqual(report["schema"], READY_SCHEMA)
            self.assertEqual(report["observation_receipts_replayed"], 1)
            self.assertEqual(report["guard_fixture_tests_passed"], 6)
            self.assertEqual(report["independent_upstream_fix_regression_pass"], 0)
            self.assertEqual(report["version_applicability_pass"], 0)
            self.assertEqual(report["signed_candidate_rule_count"], 0)
            self.assertFalse(report["auto_promotion"])
            self.assertEqual(report["review_queue"][0]["item_id"],
                             item["library_item_id"])
            self.assertEqual(report["review_queue"][0][
                "required_independent_regression_recipe"], "NOT_PROVIDED")
            self.assertFalse(report["review_queue"][0][
                "ready_for_owner_signoff"])
            broken = dict(observations, source_linked_candidates=999)
            with self.assertRaises(ReadinessError):
                assemble_readiness(audit=audit, observations=broken,
                                   guard=guard, top=10)
            forged = dict(guard, upstream_fix_verified=True)
            with self.assertRaises(ReadinessError):
                assemble_readiness(audit=audit, observations=observations,
                                   guard=forged, top=10)

    def test_browser_status_read_only_and_explicit_public_click(self):
        h, item = initial()
        calls = []
        with synthetic_ucie_root() as root:
            with owner_browser(root, h, probe_calls=calls) as base:
                with urlopen(base + "/health", timeout=5) as response:
                    state = json.load(response)
                    self.assertEqual(state["schema"], UI_SCHEMA)
                    self.assertEqual(state["automatic_observation_writes"], 0)
                    self.assertEqual(state["external_public_calls_on_observation_pages"], 0)
                with urlopen(base + "/audit", timeout=5) as response:
                    page = response.read().decode("utf-8")
                    self.assertIn("전체 공개 원본 관측 영수증", page)
                with urlopen(base + "/observations", timeout=5) as response:
                    html = response.read().decode("utf-8")
                    self.assertIn("V1.0", html)
                    self.assertIn("영수증 없음", html)
                    self.assertIn("무결성 재검사 영수증", html)
                with urlopen(base + "/observations/item/" + item["library_item_id"],
                             timeout=5) as response:
                    html = response.read().decode("utf-8")
                    self.assertIn("이 후보의 관측 영수증 0건", html)
                self.assertEqual(calls, [])
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(base + "/observations",
                                    data=b"approve", method="POST"), timeout=5)
                self.assertEqual(error.exception.code, 405)
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(base + "/observations",
                                    headers={"Host": "evil.test"}), timeout=5)
                self.assertEqual(error.exception.code, 403)
                for path in ("/observations?save=true",
                             "/observations/item/nothex",
                             "/observations?next=https://evil.test"):
                    with self.subTest(path=path), self.assertRaises(HTTPError) as error:
                        urlopen(base + path, timeout=5)
                    self.assertIn(error.exception.code, (400, 404))
                with urlopen(base + "/audit/item/" + item["library_item_id"],
                             timeout=5) as response:
                    html = response.read().decode("utf-8")
                    self.assertIn("이 후보의 공개 원본 관측 영수증 확인", html)
                    self.assertIn("공개 원본 SHA 대조 실행", html)
                self.assertEqual(calls, [])
                with urlopen(base + "/public-check/" + item["library_item_id"],
                             timeout=5) as response:
                    html = response.read().decode("utf-8")
                    self.assertIn("공개 원본 대조 결과", html)
                    self.assertIn("NOT_VERIFIED", html)
                self.assertEqual(calls, [(item["library_item_id"], 1)])
            record_explicit_observation(
                root, item_id=item["library_item_id"],
                probe=injected_probe(h), clock=WHEN)
            with owner_browser(root, h, probe_calls=calls) as base:
                with urlopen(base + "/observations", timeout=5) as response:
                    html = response.read().decode("utf-8")
                    self.assertIn("PUBLIC_MERGE_IDENTITY_MATCHED_NOT_FIX_VERIFIED", html)
                    self.assertIn("실제 오류 수정 독립 검증: NOT_VERIFIED", html)
                self.assertEqual(calls, [(item["library_item_id"], 1)])


if __name__ == "__main__":
    unittest.main()
