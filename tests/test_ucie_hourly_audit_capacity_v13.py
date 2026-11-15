"""Bounded Stage17 audit-capacity recovery; synthetic UCIE-only evidence.

Prior legacy cap of 1000 source-linked groups blocked a 1310-group owner
ledger. Increase only first-party read-only audit capacity to 2000 without
loosening source, licensing, receipt, approval or output safety checks.
No actual DB/task modifications, downloads or external code are performed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from test_ucie_library_v02 import fixture
from ucie_miner.library_audit_v07 import (
    MAX_ROWS, AuditError, STATUS as AUDIT_OK, audit_handoff_receipts)
from ucie_miner.library_quality_loop_v12 import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, OBSERVED, QualityError,
    optional_hourly_library_quality, read_quality_snapshot)
from ucie_miner.public_discovery import SOURCE_SKILL
from ucie_public.policy import PolicyError

NOW = datetime(2026, 11, 15, 0, 37, tzinfo=timezone.utc)


def synthetic_handoff(n: int) -> dict:
    if type(n) is not int or not 1 <= n <= 2100:
        raise ValueError("bounded source fixture required")
    handoff=fixture()
    templates=handoff["tasks"]
    tasks=[]
    sources=("python/cpython","PowerShell/PowerShell","git/git")
    for idx in range(n):
        source=sources[idx%len(sources)]
        row={**templates[idx%len(templates)]}
        row.update({
            "source":source,
            "reference":"pr:"+str(idx+1)+":"+("a"*40),
            "skill_id":SOURCE_SKILL[source],
            "evidence_sha256":sha256(("proof:"+str(idx)).encode()).hexdigest(),
            "candidate_id_sha256":sha256(("review:"+str(idx)).encode()).hexdigest(),
            "pattern_code":"API_CONTRACT" if idx%2 else "CONCURRENCY",
            "stage6_candidate":None,
        })
        tasks.append(row)
    handoff.update({
        "tasks":tasks,"source_revisions":n,
        "linked_revisions":n,"pending_source_revisions":0,
    })
    return handoff


class HourlyAuditCapacityTests(unittest.TestCase):
    def test_01_accepts_1310_and_exact_2000_bounded_linked_candidates(self):
        self.assertEqual(MAX_ROWS,2000)
        for size in (1310,2000):
            with self.subTest(count=size):
                out=audit_handoff_receipts(synthetic_handoff(size), [])
                self.assertEqual(out["source_linked_candidates"],size)
                self.assertEqual(out["status"],AUDIT_OK)
                self.assertEqual(len(out["candidates"]),size)
                self.assertEqual(out["approved_candidates"],0)
                self.assertEqual(out["exportable_rules"],0)
                self.assertFalse(out["auto_promoted"])
                self.assertEqual(out["network_requests"],0)
                self.assertEqual(out["operating_database_writes"],0)

    def test_02_2001_groups_still_stop_before_promotion_or_side_effects(self):
        with self.assertRaisesRegex(AuditError,"public candidate count exceeds bound"):
            audit_handoff_receipts(synthetic_handoff(2001),[])

    def test_03_large_current_hour_updates_only_synthetic_quality_receipt(self):
        with TemporaryDirectory(prefix="UCIE_AUDIT_CAP_SYNTH_") as tmp:
            root=Path(tmp)/"UCIE"
            runtime=root/"runtime"
            runtime.mkdir(parents=True)
            (runtime/OPT_IN_FILENAME).write_text(OPT_IN_TOKEN,encoding="ascii")
            prior=audit_handoff_receipts(synthetic_handoff(992),[])
            current=audit_handoff_receipts(synthetic_handoff(1310),[])
            def validate_root(candidate):
                if candidate != root or root.is_symlink():
                    raise QualityError("not approved temporary synthetic root")
                return root
            with patch("ucie_miner.library_quality_loop_v12._root",
                       side_effect=validate_root):
                first=optional_hourly_library_quality(
                    root,stage12_status="STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO",
                    stage16_status="STAGE16_SAFE_QA_ALREADY_ATTEMPTED_NO_GO",
                    auditor=lambda _:prior,clock=NOW)
                snap=read_quality_snapshot(root)
                next_result=optional_hourly_library_quality(
                    root,stage12_status="STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO",
                    stage16_status="STAGE16_SAFE_QA_ALREADY_ATTEMPTED_NO_GO",
                    auditor=lambda _:current,clock=NOW+timedelta(hours=1))
                final=read_quality_snapshot(root)
                self.assertEqual(first["status"],OBSERVED)
                self.assertEqual(next_result["status"],OBSERVED)
                self.assertEqual(next_result["candidate_delta"],318)
                self.assertEqual(final["source_candidate_count"],1310)
                self.assertEqual(final["previous_quality_sha256"],
                                 snap["snapshot_sha256"])
                self.assertEqual(final["approved_rule_count"],0)
                self.assertFalse(final["auto_promoted"])
                self.assertFalse(final["executed_external_code"])
                self.assertEqual(final["code_changes"],0)
                self.assertEqual(final["database_changes"],0)
                self.assertEqual(final["scheduled_task_changes"],0)

    def test_04_legacy_forged_approval_still_rejected(self):
        malicious=synthetic_handoff(1310)
        malicious["tasks"][0]["approval"]=True
        with self.assertRaises(PolicyError):
            audit_handoff_receipts(malicious,[])

    def test_05_quality_injected_count_over_max_fails_closed(self):
        with TemporaryDirectory(prefix="UCIE_AUDIT_CAP_LIMIT_") as tmp:
            root=Path(tmp)/"UCIE"
            runtime=root/"runtime"
            runtime.mkdir(parents=True)
            (runtime/OPT_IN_FILENAME).write_text(OPT_IN_TOKEN,encoding="ascii")
            fake=audit_handoff_receipts(synthetic_handoff(1310),[])
            fake["source_linked_candidates"]=2001
            def validate_root(candidate):
                if candidate != root or root.is_symlink():
                    raise QualityError("not approved temporary synthetic root")
                return root
            with patch("ucie_miner.library_quality_loop_v12._root",
                       side_effect=validate_root):
                with self.assertRaises(QualityError):
                    optional_hourly_library_quality(
                        root,stage12_status="STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO",
                        stage16_status="STAGE16_SAFE_QA_ALREADY_ATTEMPTED_NO_GO",
                        auditor=lambda _:fake,clock=NOW)
            self.assertFalse((runtime/"quality_v12"/"latest.json").exists())


if __name__=="__main__":
    unittest.main()
