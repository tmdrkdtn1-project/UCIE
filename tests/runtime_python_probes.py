"""UCIE-only guarded Python behavioral tests; no third-party code execution.

Raw scandir iterator races previously failed/crashed in hosted CI. Those
unsafe scenarios are NEVER rerun by this file. CI checks the first-party
safe-call mitigation; native upstream and before/after gates remain NO-GO.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import ast
import gc
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import warnings
import weakref

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.guarded_scandir import GuardedScandir


def guarded_shared_next():
    for _ in range(5):
        with tempfile.TemporaryDirectory(prefix="ucie-guarded-") as d:
            names = [f"n{i:03d}" for i in range(80)]
            for name in names:
                Path(d, name).touch()
            barrier = threading.Barrier(4)
            def reader(it):
                barrier.wait(timeout=5)
                return [entry.name for entry in it]
            with GuardedScandir(d) as it:
                with ThreadPoolExecutor(max_workers=4) as pool:
                    tasks = [pool.submit(reader, it) for _ in range(4)]
                    observed = [n for f in tasks for n in f.result(timeout=8)]
            if sorted(observed) != names:
                return False
    return True


def guarded_next_close():
    for _ in range(5):
        with tempfile.TemporaryDirectory(prefix="ucie-guarded-close-") as d:
            for i in range(80):
                Path(d, str(i)).touch()
            it = GuardedScandir(d)
            barrier = threading.Barrier(5)
            def reader():
                barrier.wait(timeout=5)
                return [entry.name for entry in it]
            def closer():
                barrier.wait(timeout=5)
                it.close()
            try:
                with ThreadPoolExecutor(max_workers=5) as pool:
                    tasks = [pool.submit(reader) for _ in range(3)]
                    tasks += [pool.submit(closer) for _ in range(2)]
                    for f in tasks:
                        f.result(timeout=8)
            finally:
                it.close()
    return True


def scandir_failed_open_no_warning():
    with tempfile.TemporaryDirectory(prefix="ucie-missing-") as d:
        Path(d, "file").touch()
        with warnings.catch_warnings(record=True) as found:
            warnings.simplefilter("always", ResourceWarning)
            for p in (Path(d, "missing"), Path(d, "file")):
                try:
                    os.scandir(p)
                    return False
                except OSError:
                    pass
            gc.collect()
        return not any(issubclass(w.category, ResourceWarning) for w in found)


def weakref_surface_smoke():
    class Target:
        pass
    obj = Target()
    ref = weakref.ref(obj)
    if obj.__weakref__ is not ref:
        return False
    def reader():
        for _ in range(1200):
            current = obj.__weakref__
            if current is not None and (not isinstance(current, weakref.ref)
                                        or current() is not obj):
                return False
        return True
    with ThreadPoolExecutor(max_workers=4) as pool:
        return all(f.result(timeout=8) for f in
                   [pool.submit(reader) for _ in range(4)])


def ast_public_repr_smoke():
    node = ast.parse("x = [n for n in (1, 2, 3)]")
    return bool(repr(node)) and isinstance(node, ast.AST)


def compiler_public_smoke():
    for bad in ("[x for in range(3)]",
                "{k:v for k, v in }",
                "(x for x in )"):
        try:
            compile(bad, "<ucie-synthetic>", "exec")
            return False
        except SyntaxError:
            pass
        for good in ("[x for x in (1, 2)]", "{x for x in (1, 2)}",
                     "{x:x for x in (1, 2)}", "(x for x in (1, 2))"):
            compile(good, "<ucie-synthetic>", "exec")
    return True


# Literal first-party call targets only: raw native racing is not reachable.
SAFE_PROBES = {
    "guarded_shared_next": guarded_shared_next,
    "guarded_next_close": guarded_next_close,
    "scandir_failed_open_no_warning": scandir_failed_open_no_warning,
    "weakref_surface_smoke": weakref_surface_smoke,
    "ast_public_repr_smoke": ast_public_repr_smoke,
    "compiler_public_smoke": compiler_public_smoke,
}


def child_main(label):
    if label not in SAFE_PROBES:
        return 2
    try:
        ok = bool(SAFE_PROBES[label]())
        print(json.dumps({"label": label, "ok": ok}), flush=True)
        return 0 if ok else 1
    except Exception as exc:
        print(json.dumps({"label": label, "error_type": type(exc).__name__}),
              flush=True)
        return 2


def observe(label):
    try:
        run = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--child", label],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=15, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"label": label, "state": "CHILD_TIMEOUT"}
    if run.returncode < 0 or run.returncode in (134, 139, 3221225477):
        return {"label": label, "state": "CHILD_PROCESS_CRASH",
                "exit_code": run.returncode}
    if run.returncode != 0:
        try:
            parsed = json.loads(run.stdout.strip())
        except (ValueError, TypeError):
            parsed = {}
        return {"label": label, "state": "GUARD_PROBE_FAILURE",
                "exit_code": run.returncode,
                "error_type": parsed.get("error_type", "UNKNOWN")}
    try:
        data = json.loads(run.stdout.strip())
    except (ValueError, TypeError):
        return {"label": label, "state": "INVALID_PROBE_OUTPUT"}
    return {"label": label, "state": (
        "GUARDED_BEHAVIOR_OBSERVED" if data == {"label": label, "ok": True}
        else "INVALID_PROBE_OUTPUT")}


def main():
    observations = [observe(label) for label in SAFE_PROBES]
    safe_guards_passed = all(
        r["state"] == "GUARDED_BEHAVIOR_OBSERVED" for r in observations)
    print("UCIE_PYTHON_BEHAVIOR=" + json.dumps({
        "schema": "UCIE_SAFE_PYTHON_BEHAVIOR_OBSERVATION_V3",
        "runtime": "CPython",
        "version": ".".join(str(x) for x in sys.version_info[:3]),
        "gil_enabled": (sys._is_gil_enabled()
                        if hasattr(sys, "_is_gil_enabled") else None),
        "observations": observations,
        "historical_unprotected_shared_next": "OBSERVED_FAILURE_NOT_RETESTED",
        "historical_unprotected_next_close": "OBSERVED_NATIVE_CRASH_NOT_RETESTED",
        "candidate_mitigation_checks_passed": safe_guards_passed,
        "native_upstream_regression_gate": "NO_GO",
        "pinned_pre_fix_build_tested": False,
        "pinned_post_fix_build_tested": False,
        "independent_before_after_verified": False,
        "production_approved": False,
    }, sort_keys=True), flush=True)
    # Green CI only means *guarded UCIE-owned prevention* checks passed.
    return 0 if safe_guards_passed else 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--child":
        raise SystemExit(child_main(sys.argv[2]))
    if len(sys.argv) != 1:
        raise SystemExit(2)
    raise SystemExit(main())
