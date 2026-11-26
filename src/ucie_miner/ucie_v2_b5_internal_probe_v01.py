"""UCIE V2 B5: bounded, owner-independent performance and truthfulness probe.

Runs ONLY preexisting UCIE-owned source-pinned read-only logic and fixed
synthetic cases. It does not benchmark real people, official documentation,
customers, upstream SDK behavior or competing services. No network, file,
database, scheduler, signing, source scanning or model training.
"""
from __future__ import annotations

import statistics
import time
import tracemalloc

SCHEMA = "UCIE_V2_B5_INTERNAL_TRUTH_RESOURCE_PROBE_V01"
MIN_RUNS = 2
MAX_RUNS = 12


class B5ProbeError(ValueError):
    """Contract drift or unsupported measurement context: fail closed."""


def _check_once() -> dict:
    from .local_b2_connected_workbench_v01 import evaluate_case
    from .ucie_v2_capsule_v01 import (
        build_from_existing_ucie, evaluate_applicability,
        explain_for_beginner,
    )
    from .ucie_v2_beginner_preview_v01 import render_preview
    from .ucie_v2_revision_impact_v01 import assess_revision_impacts
    from .ucie_v2_generalization_transfer_v01 import (
        build_hypothesis, run_bounded_transfer,
    )
    from .ucie_v2_generalization_review_v01 import render_hypothesis_chapter

    issue = evaluate_case("mcp-prompts", "issue")
    control = evaluate_case("mcp-prompts", "control")
    capsule = build_from_existing_ucie()
    applicability = evaluate_applicability(capsule)
    explanation = explain_for_beginner(capsule, applicability)
    html = render_preview()
    no_change = assess_revision_impacts(())
    hypothesis = build_hypothesis()
    transfer = run_bounded_transfer(hypothesis)
    chapter = render_hypothesis_chapter()

    if (issue.get("result_code") != "CONTRACT_VIOLATION"
            or control.get("result_code") != "CONTRACT_MATCH"
            or issue.get("independent_fix_validated") is not False
            or control.get("independent_fix_validated") is not False
            or issue.get("operating_database_writes") != 0
            or control.get("operating_database_writes") != 0
            or capsule.case_id != "mcp-prompts"
            or explanation.get("case_id") != capsule.case_id
            or explanation.get("capsule_id") != capsule.capsule_id
            or explanation.get("decision") != "HOLD"
            or applicability.get("applicability") != "UNKNOWN_NO_PROOF"
            or applicability.get("decision") != "HOLD"
            or explanation.get("rights") != "NOT_APPROVED"
            or explanation.get("independent_qa") != "NOT_VERIFIED"
            or explanation.get("customer_release") != "NOT_AUTHORIZED"
            or explanation.get("auto_promoted") is not False
            or explanation.get("sdk_reexecuted_now") is not False
            or ('id="ucie-b1-evidence"' not in html)
            or (capsule.capsule_id not in html)
            or no_change.get("affected_assets") != []
            or no_change.get("proposed_test_files") != []
            or no_change.get("automatic_scheduling") is not False
            or no_change.get("global_asset_coverage_verified") is not False
            or transfer.get("hypothesis_id") != hypothesis.get("hypothesis_id")
            or transfer.get("positive_negative_control") !=
               ["CONTRACT_MATCH", "CONTRACT_VIOLATION", "CONTROL_ONLY"]
            or transfer.get("real_upstream_sdk_rerun") is not False
            or transfer.get("independent_qa_verified") is not False
            or transfer.get("export_allowed") is not False
            or hypothesis.get("cross_source_model_generalization_verified") is not False
            or hypothesis.get("export_allowed") is not False
            or hypothesis.get("model_trained") is not False
            or "UCIE 자체 가설" not in chapter
            or "배포 불가" not in chapter):
        raise B5ProbeError("B1-B4 truth, boundary, lineage or hold mismatch")
    return {
        "case_id": capsule.case_id,
        "capsule_id": capsule.capsule_id,
        "hypothesis_id": hypothesis["hypothesis_id"],
        "source_evidence_sha256": hypothesis["content_sha256"],
        "source_retest_proposals": len(no_change["proposed_test_files"]),
        "synthetic_wire_statuses": tuple(transfer["positive_negative_control"]),
        "false_positive_proof_claims": 0,
    }


def run_internal_probe(*, repeats: int = 4) -> dict:
    """Measure reproducible B1-B4 *internal workload*, not human task speed.

    Counts and statuses are asserted in every iteration. Timing/RAM are
    environment-specific and must never become product or competitive claims.
    """
    if type(repeats) is not int or not MIN_RUNS <= repeats <= MAX_RUNS:
        raise B5ProbeError("bounded integer repeat count required")
    if tracemalloc.is_tracing():
        raise B5ProbeError("other memory measurement already active")
    wall_samples: list[int] = []
    cpu_samples: list[int] = []
    identities = set()
    tracemalloc.start()
    try:
        for _ in range(repeats):
            wall_start = time.perf_counter_ns()
            cpu_start = time.process_time_ns()
            values = _check_once()
            cpu_elapsed = time.process_time_ns() - cpu_start
            wall_elapsed = time.perf_counter_ns() - wall_start
            if wall_elapsed < 0 or cpu_elapsed < 0:
                raise B5ProbeError("non-monotonic clock during pilot")
            wall_samples.append(wall_elapsed)
            cpu_samples.append(cpu_elapsed)
            identities.add((values["case_id"], values["capsule_id"],
                            values["hypothesis_id"],
                            values["source_evidence_sha256"]))
            if (values["source_retest_proposals"] != 0
                    or values["false_positive_proof_claims"] != 0
                    or values["synthetic_wire_statuses"] !=
                    ("CONTRACT_MATCH", "CONTRACT_VIOLATION", "CONTROL_ONLY")):
                raise B5ProbeError("false confidence in bounded technical probe")
        _, peak_traced_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    if len(identities) != 1:
        raise B5ProbeError("source-bound identities changed within pilot")
    case_id, capsule_id, hypothesis_id, source_sha = next(iter(identities))
    return {
        "schema": SCHEMA,
        "status": "UCIE_OWNED_INTERNAL_MEASUREMENT_ONLY",
        "workload": "B1_CAPSULE_B2_PREVIEW_B3_NO_CHANGE_B4_TRANSFER",
        "repeats": repeats,
        "case_id": case_id,
        "capsule_id": capsule_id,
        "hypothesis_id": hypothesis_id,
        "source_evidence_sha256": source_sha,
        "wall_ns_samples": wall_samples,
        "cpu_ns_samples": cpu_samples,
        "wall_ns_median": int(statistics.median(wall_samples)),
        "cpu_ns_median": int(statistics.median(cpu_samples)),
        "python_peak_traced_bytes": peak_traced_bytes,
        "resource_scope": "CURRENT_DISPOSABLE_PROCESS_PYTHON_ALLOCATIONS_ONLY",
        "real_user_sample_count": 0,
        "real_customer_pc_tested": False,
        "real_mcp_sdk_rerun": False,
        "official_docs_baseline_measured": False,
        "general_tool_baseline_measured": False,
        "comparative_speedup_claimed": False,
        "human_task_success_claimed": False,
        "independent_qa_verified": False,
        "customer_release_authorized": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "auto_promoted": False,
        "model_trained": False,
    }
