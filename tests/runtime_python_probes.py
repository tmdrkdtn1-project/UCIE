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
                for _ in it:
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


PROBES = (
    ("PY_SCANDIR_SHARED_ITERATOR_RACE", "DIRECT_PUBLIC_RUNTIME_SURFACE",
     lambda: all((scandir_shared_next(), scandir_close_race(),
                  scandir_failed_open_no_warning()))),
    ("PY_WEAKREF_FREE_THREADED_RACE", "PUBLIC_RUNTIME_WITH_THREADING",
     weakref_surface_and_race),
    ("PY_COMPREHENSION_COMPILER_ERROR_CLEANUP", "PUBLIC_COMPILER_SMOKE_ONLY",
     compiler_public_error_recovery),
    ("PY_AST_REPR_FIELDS_LOOKUP", "PUBLIC_AST_REPR_SMOKE_ONLY",
     ast_public_repr_surface),
)


def main():
    version = ".".join(str(v) for v in sys.version_info[:3])
    gil_fn = getattr(sys, "_is_gil_enabled", None)
    gil_enabled = gil_fn() if gil_fn else None
    observations = []
    for code, coverage, test in PROBES:
        try:
            success = bool(test())
            state = "OBSERVED_EXPECTED_BEHAVIOR" if success else "OBSERVED_MISMATCH"
        except (Exception, AssertionError) as exc:
            state = "PROBE_ERROR_" + type(exc).__name__
        observations.append({"pattern": code, "coverage": coverage,
                             "state": state})
    observations.append({
        "pattern": "PY_QSBR_THREADSTATE_SLOT_LEAK",
        "coverage": "INTERNAL_FREE_THREADED_QSBR_INSTRUMENTATION_REQUIRED",
        "state": "NOT_REPRODUCED",
    })
    output = {
        "schema": "UCIE_SAFE_PYTHON_BEHAVIOR_OBSERVATION_V1",
        "runtime": "CPython", "version": version,
        "gil_enabled": gil_enabled,
        "observations": observations, "pre_fix_revision_tested": False,
        "pinned_post_fix_commit_tested": False,
        "upstream_code_checked_out": False,
        "independent_before_after_verified": False,
        "production_approved": False,
    }
    print("UCIE_PYTHON_BEHAVIOR=" + json.dumps(output, sort_keys=True))
    return 1 if any(item["state"].startswith(("PROBE_ERROR", "OBSERVED_MISMATCH"))
                    for item in observations) else 0


if __name__ == "__main__":
    raise SystemExit(main())
