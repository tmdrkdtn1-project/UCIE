"""UCIE W11 first-party synthetic process-shutdown phase laboratory.

Only an isolated -I -B child, UCIE worker imports, disposable synthetic
temporary fixtures and fixed injected failure modes. Never mines public
sources, scans owner projects, alters TaskScheduler or tests production DB.

A synthetic result cannot establish the cause of a real 600s task action.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

SCHEMA = "UCIE_W11_PUBLIC_MINER_SHUTDOWN_PHASE_SYNTHETIC_V01"
PREVIEW = "SYNTHETIC_PHASE_LAB_NOT_RUN_NO_SCHEDULER_PROOF"
PASS = "FIRST_PARTY_SYNTHETIC_PHASES_CLASSIFIED_NO_PRODUCTION_CLAIM"
NO_GO = "SYNTHETIC_PHASE_EVIDENCE_INCOMPLETE_NO_GO"
MODES = ("clean", "fsync_error", "stdout_error", "post_stdout_hold")
PHASES = frozenset((
    "RECEIPT_ENTER", "FSYNC_ENTER", "FSYNC_RETURN",
    "RECEIPT_FAILURE", "RECEIPT_RETURN",
    "WORKER_RETURN", "TEMP_CLEANED",
    "STDOUT_ERROR_INJECTED", "STDOUT_FLUSH_RETURN",
    "MAIN_END", "PYTHON_ATEXIT",
))
MAX_CAPTURE_BYTES = 12000
CHILD_TIMEOUT_SECONDS = 5.0
HOLD_TIMEOUT_SECONDS = 2.0
_CHILD = r'''
import atexit
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from ucie_miner import worker

mode = sys.argv[1]
assert mode in ("clean", "fsync_error", "stdout_error", "post_stdout_hold")
def mark(phase):
    sys.stderr.write("UCIE_W11_PHASE:" + phase + "\n")
    sys.stderr.flush()
atexit.register(lambda: mark("PYTHON_ATEXIT"))
original_fsync = os.fsync
def observed_fsync(fd):
    mark("FSYNC_ENTER")
    if mode == "fsync_error":
        raise OSError("FIRST_PARTY_SYNTHETIC_FSYNCH_FAILURE_ONLY")
    original_fsync(fd)
    mark("FSYNC_RETURN")
worker.os.fsync = observed_fsync
original_receipt = worker._write_receipt
def observed_receipt(runtime, data):
    mark("RECEIPT_ENTER")
    try:
        original_receipt(runtime, data)
    except OSError:
        mark("RECEIPT_FAILURE")
        raise
    mark("RECEIPT_RETURN")
worker._write_receipt = observed_receipt
with tempfile.TemporaryDirectory(prefix="UCIE_W11_DISPOSABLE_") as parent:
    repo_root = Path(parent) / "UCIE"
    repo_root.mkdir()
    def fake_collect(_root):
        return {"status": "COLLECTED_UNVERIFIED",
                "new_candidates": 0, "sources_checked": 2,
                "verification_pass": 0, "production_approved": False}
    def fake_report(_root):
        target = repo_root / "runtime" / "reports"
        target.mkdir(parents=True, exist_ok=True)
        output = target / "synthetic-only.md"
        output.write_text("SYNTHETIC ONLY\n", encoding="utf-8")
        return output
    result = worker.run_cycle(
        repo_root, collect=fake_collect, write_report=fake_report,
        enforce_schedule=False)
    assert result["status"] == "COLLECTED_UNVERIFIED"
    assert result["production_approved"] is False
    history = repo_root / "runtime" / "run_history.jsonl"
    assert len(history.read_text(encoding="utf-8").splitlines()) == 1
    mark("WORKER_RETURN")
mark("TEMP_CLEANED")
if mode == "stdout_error":
    mark("STDOUT_ERROR_INJECTED")
    raise OSError("FIRST_PARTY_SYNTHETIC_OUTPUT_EXCEPTION_ONLY")
sys.stdout.write('{"synthetic_receipt_only":true}\n')
sys.stdout.flush()
mark("STDOUT_FLUSH_RETURN")
if mode == "post_stdout_hold":
    time.sleep(5.0)
mark("MAIN_END")
'''


class ShutdownPhaseError(ValueError):
    """Rejected source identity or synthetic subprocess evidence."""


def _source_contract() -> Path:
    source = Path(__file__)
    root = source.resolve().parents[2]
    pkg = root / "src" / "ucie_miner"
    worker = pkg / "worker.py"
    if (source.is_symlink() or root.name.casefold() != "ucie"
            or root.is_symlink() or pkg.is_symlink()
            or worker.is_symlink() or not worker.is_file()):
        raise ShutdownPhaseError("UCIE-only source root unavailable")
    return root


def _phase_names(stderr: str | bytes | None) -> tuple[str, ...]:
    if stderr is None:
        return ()
    if type(stderr) is bytes:
        stderr = stderr.decode("utf-8", errors="replace")
    if type(stderr) is not str or len(stderr.encode("utf-8")) > MAX_CAPTURE_BYTES:
        return ()
    names = []
    for line in stderr.splitlines():
        if line.startswith("UCIE_W11_PHASE:"):
            name = line[len("UCIE_W11_PHASE:"):]
            if name not in PHASES:
                return ()
            names.append(name)
    return () if len(names) > 36 else tuple(names)


def _ordered(phases: tuple[str, ...], required: tuple[str, ...]) -> bool:
    previous = -1
    for phase in required:
        try:
            previous = phases.index(phase, previous + 1)
        except ValueError:
            return False
    return True


def _expected(mode: str, code: int | None, phases: tuple[str, ...],
              stdout: str | bytes | None, timed_out: bool) -> bool:
    if type(code) is bool or (code is not None and type(code) is not int):
        return False
    ordered = {
        "clean": ("RECEIPT_ENTER", "FSYNC_ENTER", "FSYNC_RETURN",
                  "RECEIPT_RETURN", "WORKER_RETURN", "TEMP_CLEANED",
                  "STDOUT_FLUSH_RETURN", "MAIN_END", "PYTHON_ATEXIT"),
        "fsync_error": ("RECEIPT_ENTER", "FSYNC_ENTER",
                        "RECEIPT_FAILURE", "PYTHON_ATEXIT"),
        "stdout_error": ("RECEIPT_ENTER", "FSYNC_ENTER", "FSYNC_RETURN",
                         "RECEIPT_RETURN", "WORKER_RETURN", "TEMP_CLEANED",
                         "STDOUT_ERROR_INJECTED", "PYTHON_ATEXIT"),
        "post_stdout_hold": ("RECEIPT_ENTER", "FSYNC_ENTER", "FSYNC_RETURN",
                             "RECEIPT_RETURN", "WORKER_RETURN",
                             "TEMP_CLEANED", "STDOUT_FLUSH_RETURN"),
    }
    if mode not in ordered or not _ordered(phases, ordered[mode]):
        return False
    seen = set(phases)
    mandatory = {"RECEIPT_ENTER", "FSYNC_ENTER"}
    if not mandatory <= seen:
        return False
    if mode == "clean":
        return (not timed_out and code == 0
                and isinstance(stdout, str)
                and stdout.strip() == '{"synthetic_receipt_only":true}'
                and {"FSYNC_RETURN", "RECEIPT_RETURN", "WORKER_RETURN",
                     "TEMP_CLEANED", "STDOUT_FLUSH_RETURN",
                     "MAIN_END", "PYTHON_ATEXIT"} <= seen
                and "RECEIPT_FAILURE" not in seen)
    if mode == "fsync_error":
        return (not timed_out and code is not None and code != 0
                and {"RECEIPT_FAILURE", "PYTHON_ATEXIT"} <= seen
                and "RECEIPT_RETURN" not in seen
                and "WORKER_RETURN" not in seen)
    if mode == "stdout_error":
        return (not timed_out and code is not None and code != 0
                and {"FSYNC_RETURN", "RECEIPT_RETURN", "WORKER_RETURN",
                     "TEMP_CLEANED", "STDOUT_ERROR_INJECTED",
                     "PYTHON_ATEXIT"} <= seen
                and "STDOUT_FLUSH_RETURN" not in seen)
    if mode == "post_stdout_hold":
        out = stdout.decode("utf-8", errors="replace") if type(stdout) is bytes else stdout
        return (timed_out and code is None
                and isinstance(out, str)
                and out.strip() == '{"synthetic_receipt_only":true}'
                and {"RECEIPT_RETURN", "WORKER_RETURN", "TEMP_CLEANED",
                     "STDOUT_FLUSH_RETURN"} <= seen
                and "MAIN_END" not in seen)
    return False


def run_one(mode: str, *, runner=None) -> dict:
    if mode not in MODES or type(mode) is not str:
        raise ShutdownPhaseError("unknown synthetic phase mode")
    root = _source_contract()
    source_root = root / "src"
    child = ("import sys\nsys.path.insert(0, " + repr(str(source_root)) +
             ")\n" + _CHILD)
    invoke = subprocess.run if runner is None else runner
    timed_out = False
    code = None
    stdout = None
    stderr = None
    try:
        process = invoke(
            [sys.executable, "-I", "-B", "-c", child, mode],
            cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=(HOLD_TIMEOUT_SECONDS if mode ==
                                "post_stdout_hold" else CHILD_TIMEOUT_SECONDS),
            check=False,
        )
        code = process.returncode
        stdout, stderr = process.stdout, process.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout, stderr = exc.stdout, exc.stderr
    except (OSError, ValueError):
        pass
    phases = _phase_names(stderr)
    accepted = _expected(mode, code, phases, stdout, timed_out)
    return {
        "mode": mode,
        "status": "SYNTHETIC_CASE_OBSERVED" if accepted
                  else "SYNTHETIC_CASE_NOT_PROVEN_NO_GO",
        "child_returncode": code,
        "child_timeout_observed": timed_out,
        "safe_phase_sequence": list(phases),
        "fsync_entered": "FSYNC_ENTER" in phases,
        "fsync_returned": "FSYNC_RETURN" in phases,
        "receipt_write_returned": "RECEIPT_RETURN" in phases,
        "worker_returned": "WORKER_RETURN" in phases,
        "temp_cleanup_returned": "TEMP_CLEANED" in phases,
        "stdout_flush_returned": "STDOUT_FLUSH_RETURN" in phases,
        "python_atexit_observed": "PYTHON_ATEXIT" in phases,
        "synthetic_only": True,
        "real_public_miner_executed": False,
        "real_task_scheduler_verified": False,
        "production_termination_root_cause_proven": False,
        "owner_operating_db_writes": 0,
        "task_scheduler_mutations": 0,
        "network_requests": 0,
        "other_project_access": False,
    }


def preview() -> dict:
    return {
        "schema": SCHEMA, "status": PREVIEW,
        "modes": list(MODES),
        "synthetic_subprocesses_started": 0,
        "real_public_miner_executed": False,
        "task_scheduler_mutations": 0,
        "owner_operating_db_writes": 0,
        "production_termination_root_cause_proven": False,
    }


def run_all(*, runner=None) -> dict:
    results = [run_one(mode, runner=runner) for mode in MODES]
    complete = all(item["status"] == "SYNTHETIC_CASE_OBSERVED"
                   for item in results)
    return {
        "schema": SCHEMA, "status": PASS if complete else NO_GO,
        "results": results,
        "cases": len(results),
        "passed": sum(item["status"] == "SYNTHETIC_CASE_OBSERVED"
                      for item in results),
        "synthetic_only": True,
        "real_public_miner_executed": False,
        "real_task_scheduler_verified": False,
        "production_termination_root_cause_proven": False,
        "task_scheduler_mutations": 0,
        "owner_operating_db_writes": 0,
        "network_requests": 0,
        "other_project_access": False,
        "model_training_performed": False,
        "released": False,
    }


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description="UCIE W11 disposable synthetic shutdown phases")
    cli.add_argument("--run-synthetic", action="store_true")
    args = cli.parse_args(argv)
    if not args.run_synthetic:
        print(json.dumps(preview(), sort_keys=True))
        return 0
    try:
        report = run_all()
    except (ShutdownPhaseError, OSError, ValueError, TypeError):
        report = {"schema": SCHEMA, "status": NO_GO,
                  "synthetic_only": True,
                  "owner_operating_db_writes": 0,
                  "task_scheduler_mutations": 0}
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0 if report["status"] == PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
