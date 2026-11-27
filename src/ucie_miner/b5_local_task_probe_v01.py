"""UCIE B5 bounded owner-local technical probe, not a human usability study.

Measures repeatable rendered-route tasks against exact expected content. No
visitor tracking, persistent telemetry, external network, private data, or
claim of free-doc/tool/UCIE competitive superiority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from statistics import median
from time import perf_counter_ns, process_time_ns

from .b1_b4_skillbook_capsule_link_v01 import build_pinned_b1_capsules
from .local_v1_priority_v01 import require_local_work

SCHEMA = "UCIE_B5_OFFLINE_TASK_PROBE_V01"
ROUTE = "/v2/library"
SCENARIOS = (
    ("supported", "검토 후보 · 미승인"),
    ("missing_permission", "권한이 부족해 전이 후보를 거부했습니다"),
    ("unapproved_target", "현재 근거에 없는 기술이므로 전이를 거부했습니다"),
)


class B5ProbeError(ValueError):
    pass


def run_b5_local_probe(repetitions: int = 3) -> dict:
    """Execute only fixed local render paths, with bounded timing samples.

    This measures Python rendering and fixed-content correctness, not actual
    novice comprehension, browser navigation time, peak RAM or buyer demand.
    """
    require_local_work("VIRTUAL_LIBRARY")
    if type(repetitions) is not int or not 1 <= repetitions <= 5:
        raise B5ProbeError("INVALID_REPETITIONS")
    from .v2_b1_b4_explorer_v01 import route_v2_request

    capsules = build_pinned_b1_capsules()
    if len(capsules) != 2:
        raise B5ProbeError("EXPECTED_TWO_CASES")
    rows = []
    # Include start page and each fixed scenario for both pinned techniques.
    tasks = [("landing", ROUTE, "기술 근거에서 재사용 가능한 원리까지")]
    for capsule in capsules:
        for scenario, expected in SCENARIOS:
            tasks.append((capsule["source_id"] + ":" + scenario,
                          ROUTE + "?case=" + capsule["case_id"]
                          + "&review=" + scenario, expected))
    for task, path, expected in tasks:
        ms = []
        cpu_ms = []
        for _ in range(repetitions):
            wall_start, cpu_start = perf_counter_ns(), process_time_ns()
            status, html = route_v2_request("GET", path)
            cpu_ms.append((process_time_ns() - cpu_start) / 1_000_000)
            ms.append((perf_counter_ns() - wall_start) / 1_000_000)
            if (status != 200 or expected not in html
                    or "REVIEW_ONLY_UNVERIFIED" not in html
                       and task != "landing"
                    or "<form" in html or "fetch(" in html
                    or "자동 코드 실행 없음" not in html
                       and task != "landing"):
                raise B5ProbeError("FIXED_TASK_UNEXPECTED_OUTPUT")
        rows.append({
            "task": task,
            "samples": repetitions,
            "route_render_wall_median_ms": round(median(ms), 3),
            # Windows process CPU clocks can quantize short calls to zero. Do
            # not misrepresent an unresolved duration as genuine 0 ms CPU.
            "route_render_cpu_median_ms": (
                round(median(cpu_ms), 3) if median(cpu_ms) > 0 else None
            ),
            "cpu_measurement_status": (
                "MEASURED" if median(cpu_ms) > 0 else "BELOW_TIMER_RESOLUTION"
            ),
            "expected_content_found": True,
            "approval_overclaim_detected_by_fixed_checks": False,
        })
    result = {
        "schema": SCHEMA, "status": "FIRST_PARTY_OFFLINE_TECHNICAL_PROBE_ONLY",
        "task_count": len(rows), "task_observations": len(rows) * repetitions,
        "rows": rows,
        "scope": "PYTHON_IN_PROCESS_ROUTE_RENDERING_NOT_EDGE_NAVIGATION",
        "official_documentation_baseline": "NOT_MEASURED",
        "normal_tools_baseline": "NOT_MEASURED",
        "novice_first_action_within_10s": "NOT_MEASURED",
        "human_comprehension": "NOT_MEASURED",
        "human_task_completion": "NOT_MEASURED",
        "buyer_willingness": "NOT_MEASURED",
        "peak_ram": "NOT_MEASURED",
        "retest_cost": "NOT_MEASURED",
        "false_confidence_human_observations": "NOT_MEASURED",
        "independent_qa": "NOT_RUN",
        "network_requests": 0,
        "persistent_usage_logs": False,
        "operating_database_writes": 0,
        "customer_code_access": False,
        "export_allowed": False,
        "owner_approved": False,
    }
    if len(json.dumps(result, ensure_ascii=True)) > 8000:
        raise B5ProbeError("RECEIPT_TOO_LARGE")
    return result
