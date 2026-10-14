# UCIE Stage 5/6 — inert Python concurrency candidate detection V1

## Why this stage exists

Earlier UCIE-hosted tests directly observed errors and a native child-process
crash when raw `os.scandir` iteration was shared across threads. Draft PR #16
implemented a UCIE-owned `GuardedScandir` wrapper that serializes all
`next()` and `close()` operations, with 182/182 tests per platform matrix
and no observed crash in the **guarded** tests.

That mitigation is useful only if UCIE can identify *potentially unsafe
call sites* before the user executes them. This stage connects the public PR
evidence for `python/cpython#153462` to a first-party, **pure AST** detector.

## Detection contract

`inspect_python_scandir_source(text)` parses only caller-provided inert
Python text using `ast.parse`; it does **not** run it, import dependencies,
read files or connect to anything. Bounded limits:

- UTF-8 input <=128 KiB (131,072 bytes)
- AST node count <=10,000
- finding count <=100; excess or malformed input fails closed

It detects unguarded iterator bindings of the literal `os.scandir(...)`
form whose names are passed into a likely executor/thread boundary:

- `executor.submit(worker, iterator)`
- `executor.map(worker, iterator)`
- `threading.Thread(target=worker, args=(iterator,))`
- an executor/thread invoking an explicitly declared inner function
  that captures the raw iterator

Output reports source SHA-256, line/column, boundary type, a safe-call
guidance string and the approved public PR URL. **Every finding is
`STATIC_HEURISTIC_REVIEW_REQUIRED`**. The detector cannot infer all aliases,
imports, data flow, iterator lifetime, executor identity, lock state,
or third-party native behavior. A missing finding is **not** a safety PASS,
and detection is **not** proof that the runtime bug is reproduced.

## Read-only CLI

For explicitly approved public code snippets or synthetic test text in
an isolated UCIE development checkout:

```powershell
@'
import os
def run(directory, executor, consumer):
    raw = os.scandir(directory)
    executor.submit(consumer, raw)
'@ | .\.venv\Scripts\python.exe -m ucie_miner scan-python-stdin
```

This command reads **standard input only**. It does not traverse
`D:\UCIE`, user repositories, other project folders or arbitrary
filesystem paths. It does not show the source text in output or save it.
Do **not** pipe private code, user files or unapproved repos to this
command; approved public and purpose-built synthetic examples only.

## Regression and review boundaries

- Synthetic tests check explicit executor arguments, captured closures,
  `threading.Thread` arguments, negative single-thread cases, guarded
  iterators, syntax errors, limits and non-execution of suspicious AST text.
- CLI tests use only UCIE-authored snippets and confirm no code was run,
  no source file was opened and no candidate was approved/promoted.
- Existing guarded runtime and Stage 4–8 CI tests continue.
- The exact `python/cpython` pre-fix vs pinned post-fix runtime
  reproduction, independent approval, release inclusion, signing, scheduled
  production deployment and operating-host acceptance remain `NO_GO`.

**Status:** `STATIC_CANDIDATE_ONLY / SOURCE_EXECUTION=NONE / RULEPACK_NO_GO`.
