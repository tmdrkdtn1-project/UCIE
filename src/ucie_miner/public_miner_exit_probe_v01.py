"""UCIE-only first-party SYNTHETIC subprocess exit probe.

Never runs the real public collector or changes the Windows task. A successful
synthetic subprocess exit proves only this isolated import/run_cycle path can
exit; it does NOT explain a real scheduled task's last termination.
"""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter_ns

SCHEMA = "UCIE_PUBLIC_MINER_SYNTHETIC_EXIT_PROBE_V01"
PREVIEW = "SYNTHETIC_EXIT_PROBE_NOT_RUN_NO_SCHEDULER_PROOF"
PASS = "FIRST_PARTY_SYNTHETIC_SUBPROCESS_EXIT_OBSERVED_NO_RELEASE"
NO_GO = "SYNTHETIC_SUBPROCESS_EXIT_NOT_PROVEN_NO_GO"
MAX_OUTPUT = 4096
TIMEOUT_SECONDS = 15

# Executed only with an absolute Python executable, -I isolation and -B.
# Every data fixture is created by this child in a disposable TEMP folder.
# No real UCIE operating runtime path is supplied to run_cycle.
_CHILD = r'''
import json
from pathlib import Path
import runpy
import sys
import tempfile
from ucie_miner.worker import run_cycle

entrypoint = Path(sys.argv[1])
module = runpy.run_path(str(entrypoint), run_name="__ucie_exit_probe_only__")
assert callable(module["main"])
with tempfile.TemporaryDirectory(prefix="UCIE_SYNTHETIC_EXIT_") as base:
    root = Path(base) / "UCIE"
    root.mkdir()
    def collect(_root):
        return {"status": "COLLECTED_UNVERIFIED", "new_candidates": 0,
                "sources_checked": 2, "verification_pass": 0,
                "production_approved": False}
    def report(_root):
        target = root / "runtime" / "reports"
        target.mkdir(parents=True, exist_ok=True)
        output = target / "synthetic-only.md"
        output.write_text("FIRST_PARTY_SYNTHETIC_FIXTURE_ONLY\n", encoding="utf-8")
        return output
    result = run_cycle(root, collect=collect, write_report=report,
                       enforce_schedule=False)
    runtime = root / "runtime"
    last = json.loads((runtime / "last_run.json").read_text(encoding="utf-8"))
    history = (runtime / "run_history.jsonl").read_text(encoding="utf-8")
    assert result["status"] == "COLLECTED_UNVERIFIED"
    assert last["status"] == "COLLECTED_UNVERIFIED"
    assert len(history.splitlines()) == 1
    assert result["production_approved"] is False
    assert result["verification_pass"] == 0
    assert result["new_candidates"] == 0
    assert result["sources_checked"] == 2
    marker = {"schema": "UCIE_CHILD_SYNTHETIC_CYCLE_EXIT_MARKER_V01",
              "synthetic_receipt_saved": True,
              "synthetic_worker_returned": True,
              "entrypoint_imported_but_not_executed": True,
              "actual_public_collector_invoked": False,
              "operating_ucie_database_accessed": False,
              "real_owner_directory_scanned": False,
              "synthetic_fixture_created_and_cleaned": True,
              "public_network_requests": 0,
              "approved_rules_added": 0}
print(json.dumps(marker, sort_keys=True), flush=True)
'''


class ExitProbeError(ValueError):
    """Invalid source scope or untrusted synthetic child result."""


def preview_exit_probe() -> dict:
    return {
        "schema": SCHEMA,
        "status": PREVIEW,
        "synthetic_subprocess_started": False,
        "synthetic_receipt_written": False,
        "real_collector_invoked": False,
        "real_owner_directory_scanned": False,
        "real_task_scheduler_events_verified": False,
        "production_termination_root_cause_proven": False,
        "task_scheduler_mutated": False,
        "operating_database_writes": 0,
        "public_network_requests": 0,
        "model_training_performed": False,
    }


def _source_contract() -> tuple[Path, Path]:
    package = Path(__file__)
    root = package.resolve().parents[2]
    entry = root / "scripts" / "public_miner_cycle.py"
    worker = root / "src" / "ucie_miner" / "worker.py"
    if (root.name.casefold() != "ucie" or root.is_symlink()
            or package.is_symlink() or entry.is_symlink()
            or worker.is_symlink() or not entry.is_file()
            or not worker.is_file()
            or not (root / "src" / "ucie_miner").is_dir()):
        raise ExitProbeError("UCIE fixed source contract not available")
    return root, entry


def run_synthetic_exit_probe(*, runner=None) -> dict:
    """Attempt a bounded isolated Python process; never execute the miner.

    Real worker imports + run_cycle body run with injected no-network
    collection, synthetic-only report and OS-held lock. The scheduled worker
    entrypoint is import-loaded without executing its main() function.
    """
    root, entry = _source_contract()
    child = "import sys\nsys.path.insert(0, " + repr(str(root / "src")) + ")\n" + _CHILD
    started = perf_counter_ns()
    invoke = subprocess.run if runner is None else runner
    try:
        process = invoke(
            [sys.executable, "-I", "-B", "-c", child, str(entry)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            cwd=str(root), timeout=TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {
            **preview_exit_probe(),
            "status": NO_GO,
            "synthetic_subprocess_started": True,
            "failure_category": "PROCESS_START_OR_EXIT_TIMEOUT_NO_GO",
            "child_exit_code": None,
            "exit_observed": False,
        }
    if (type(process.returncode) is not int
            or not isinstance(process.stdout, str)
            or len(process.stdout.encode("utf-8")) > MAX_OUTPUT
            or process.returncode != 0):
        return {
            **preview_exit_probe(),
            "status": NO_GO,
            "synthetic_subprocess_started": True,
            "failure_category": "CHILD_NONZERO_OR_INVALID_OUTPUT_NO_GO",
            "child_exit_code": process.returncode,
            "exit_observed": True,
        }
    try:
        marker = json.loads(process.stdout.strip())
    except (json.JSONDecodeError, UnicodeError):
        marker = None
    expected = {
        "schema": "UCIE_CHILD_SYNTHETIC_CYCLE_EXIT_MARKER_V01",
        "synthetic_receipt_saved": True,
        "synthetic_worker_returned": True,
        "entrypoint_imported_but_not_executed": True,
        "actual_public_collector_invoked": False,
        "operating_ucie_database_accessed": False,
        "real_owner_directory_scanned": False,
        "synthetic_fixture_created_and_cleaned": True,
        "public_network_requests": 0,
        "approved_rules_added": 0,
    }
    if marker != expected:
        return {
            **preview_exit_probe(),
            "status": NO_GO,
            "synthetic_subprocess_started": True,
            "failure_category": "UNTRUSTED_SYNTHETIC_MARKER_NO_GO",
            "child_exit_code": process.returncode,
            "exit_observed": True,
        }
    return {
        "schema": SCHEMA,
        "status": PASS,
        "captured_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python_runtime": f"{sys.version_info.major}.{sys.version_info.minor}",
        "child_exit_code": 0,
        "elapsed_ms": min(60000, max(0, (perf_counter_ns() - started) // 1_000_000)),
        "exit_observed": True,
        "synthetic_subprocess_started": True,
        "synthetic_worker_returned": True,
        "synthetic_receipt_written": True,
        "entrypoint_imported_but_not_executed": True,
        "actual_public_collector_invoked": False,
        "real_owner_directory_scanned": False,
        "real_task_scheduler_events_verified": False,
        "production_termination_root_cause_proven": False,
        "production_scheduler_verified": False,
        "owner_authorized_task_repair": False,
        "task_scheduler_mutated": False,
        "temporary_synthetic_fixture_writes": True,
        "operating_database_writes": 0,
        "public_network_requests": 0,
        "model_training_performed": False,
        "other_project_access": False,
    }


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(
        description="UCIE safe synthetic subprocess exit only; never run public miner")
    cli.add_argument("--run-synthetic", action="store_true")
    args = cli.parse_args(argv)
    if not args.run_synthetic:
        print(json.dumps(preview_exit_probe(), sort_keys=True))
        return 0
    try:
        report = run_synthetic_exit_probe()
    except (ExitProbeError, ValueError, TypeError, OSError):
        report = {
            "schema": SCHEMA, "status": NO_GO,
            "failure_category": "SOURCE_CONTRACT_INVALID_NO_GO",
            "operating_database_writes": 0,
            "task_scheduler_mutated": False,
        }
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0 if report["status"] == PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
