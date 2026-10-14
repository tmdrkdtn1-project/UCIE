"""UCIE-authored, bounded Python runtime behavioral probes.

Runs only first-party Python standard library in ephemeral GitHub CI.
No upstream PR code is imported or executed. No local UCIE DB is accessed.
Positive behavior is *not* a before/after upstream fix verification.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import ast
import gc
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import threading
import warnings
import weakref


def scandir_shared_next():
    for _ in range(4):
        with tempfile.TemporaryDirectory(prefix="ucie-scandir-") as d:
            for i in range(80):
                Path(d, f"n{i:03d}").touch()
            names = []
            lock = threading.Lock()
            with os.scandir(d) as it:
                def read():
                    local = [entry.name for entry in it]
                    with lock:
                        names.extend(local)
                with ThreadPoolExecutor(max_workers=4) as pool:
                    tasks = [pool.submit(read) for _ in range(4)]
                    for task in tasks:
                        task.result(timeout=8)
            if sorted(names) != [f"n{i:03d}" for i in range(80)]:
                return False
    return True


def scandir_close_race():
    for _ in range(4):
        with tempfile.TemporaryDirectory(prefix="ucie-close-") as d:
            for i in range(50):
                Path(d, str(i)).touch()
            it = os.scandir(d)
            def reader():
                try:
                    for _ in it:
                        pass
                except OSError:
                    # Windows may report a graceful directory-handle close race.
                    pass
            try:
                with ThreadPoolExecutor(max_workers=5) as pool:
                    tasks = [pool.submit(reader) for _ in range(3)]
                    tasks += [pool.submit(it.close) for _ in range(2)]
                    for task in tasks:
                        task.result(timeout=8)
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


def weakref_surface_and_race():
    class Target:
        pass
    obj = Target()
    ref = weakref.ref(obj)
    if obj.__weakref__ is not ref:
        return False
    def reader():
        for _ in range(1600):
            current = obj.__weakref__
            if current is not None and (not isinstance(current, weakref.ref)
                                        or current() is not obj):
                return False
        return True
    def writer():
        for _ in range(1600):
            weakref.ref(obj)
        return True
    with ThreadPoolExecutor(max_workers=6) as pool:
        tasks = [pool.submit(reader) for _ in range(3)]
        tasks += [pool.submit(writer) for _ in range(3)]
        return all(x.result(timeout=8) for x in tasks)


def ast_public_repr_surface():
    tree = ast.parse("x = [n for n in (1, 2, 3)]")
    text = repr(tree)
    if not isinstance(text, str) or not text:
        return False
    # This does not exercise internal PyObject_GetAttr failure injection.
    return isinstance(ast.Name(id="x", ctx=ast.Load()), ast.AST)


def compiler_public_error_recovery():
    for bad in ("[x for in range(3)]",
                "{k:v for k, v in }",
                "(x for x in )"):
        try:
            compile(bad, "<ucie-synthetic>", "exec")
            return False
        except SyntaxError:
            pass
        compile("[x for x in (1, 2)]", "<ucie-synthetic>", "exec")
        compile("{x for x in (1, 2)}", "<ucie-synthetic>", "exec")
        compile("{x:x for x in (1, 2)}", "<ucie-synthetic>", "exec")
        compile("(x for x in (1, 2))", "<ucie-synthetic>", "exec")
    # Compiler exception recovery smoke only, not internal failpoint proof.
    return True



# A native interpreter crash in one behavioral test must not prevent all
# other probes from reporting. Run only our own fixed, literal child targets.
CHILD_PROBES = {
    "scandir_shared_next": scandir_shared_next,
    "scandir_close_race": scandir_close_race,
    "scandir_failed_open_no_warning": scandir_failed_open_no_warning,
    "weakref_surface_and_race": weakref_surface_and_race,
    "ast_public_repr_surface": ast_public_repr_surface,
    "compiler_public_error_recovery": compiler_public_error_recovery,
}


def child_main(label):
    if label not in CHILD_PROBES:
        return 2
    try:
        succeeded = bool(CHILD_PROBES[label]())
        print(json.dumps({"label": label, "ok": succeeded}), flush=True)
        return 0 if succeeded else 1
    except Exception as exc:
        print(json.dumps({"label": label, "error_type": type(exc).__name__}),
              flush=True)
        return 2


def observe(label):
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--child", label],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=12, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"label": label, "state": "CHILD_TIMEOUT"}
    if result.returncode < 0 or result.returncode in (134, 139, 3221225477):
        return {"label": label, "state": "CHILD_PROCESS_CRASH",
                "exit_code": result.returncode}
    if result.returncode != 0:
        return {"label": label, "state": "PROBE_FAILURE",
                "exit_code": result.returncode}
    try:
        obj = json.loads(result.stdout.strip())
    except (json.JSONDecodeError, ValueError):
        return {"label": label, "state": "INVALID_PROBE_OUTPUT"}
    return {"label": label,
            "state": ("OBSERVED_EXPECTED_BEHAVIOR"
                      if obj == {"label": label, "ok": True}
                      else "INVALID_PROBE_OUTPUT")}


def main():
    version = ".".join(str(v) for v in sys.version_info[:3])
    gil_fn = getattr(sys, "_is_gil_enabled", None)
    gil_enabled = gil_fn() if gil_fn else None
    observations = []
    for label in CHILD_PROBES:
        # This exact close/next probe crashed an isolated Linux subprocess on
        # 3.13.16 and 3.15.0; do not repeatedly trigger native faults on
        # ordinary PR CI. A separately approved isolated reproduction may
        # opt in after a safety review.
        if (label == "scandir_close_race"
                and os.environ.get("UCIE_ALLOW_NATIVE_CRASH_REPRO") != "1"):
            observation = {"label": label,
                           "state": "NOT_RETESTED_PREVIOUS_CHILD_CRASH"}
        else:
            observation = observe(label)
        observation["coverage"] = (
            "DIRECT_PUBLIC_RUNTIME_SURFACE" if label.startswith("scandir")
            else "PUBLIC_RUNTIME_SMOKE_WITH_THREADING" if label.startswith("weakref")
            else "PUBLIC_RUNTIME_SMOKE_ONLY")
        observations.append(observation)
    observations.append({
        "label": "PY_QSBR_THREADSTATE_SLOT_LEAK",
        "coverage": "INTERNAL_FREE_THREADED_QSBR_INSTRUMENTATION_REQUIRED",
        "state": "NOT_REPRODUCED",
    })
    output = {
        "schema": "UCIE_SAFE_PYTHON_BEHAVIOR_OBSERVATION_V2",
        "runtime": "CPython", "version": version,
        "gil_enabled": gil_enabled,
        "observations": observations,
        "pre_fix_revision_tested": False,
        "pinned_post_fix_commit_tested": False,
        "independent_before_after_verified": False,
        "production_approved": False,
    }
    print("UCIE_PYTHON_BEHAVIOR=" + json.dumps(output, sort_keys=True),
          flush=True)
    # Return nonzero on any observed crash/failure. A green result is only
    # probe execution, not upstream before/after proof.
    return 1 if any(x["state"] not in ("OBSERVED_EXPECTED_BEHAVIOR",
                                     "NOT_REPRODUCED",
                                     "NOT_RETESTED_PREVIOUS_CHILD_CRASH")
                    for x in observations) else 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--child":
        raise SystemExit(child_main(sys.argv[2]))
    if len(sys.argv) != 1:
        raise SystemExit(2)
    raise SystemExit(main())
