# UCIE public fix candidate review — 2026-10-17 (evidence-only, NO-GO)

**Scope:** Approved public `python/cpython` and `PowerShell/PowerShell` PRs
referenced by the operator's *read-only* UCIE Stage12/15 inspection (19
unverified proposals, 10 Stage15-linked records). This is a human-review
evidence note, **not** a rule, patch, verification certificate, learning-weight
change or promotion. No original third-party patches or raw source are copied
into UCIE. No private projects or user data were accessed. No network or
execution is added to the scheduled miner.

**Evidence status:** Official merged PR metadata, exact merge hashes,
release-date metadata and pinned upstream source were **read and compared**.
No independently executed before/after CPython binaries, executable upstream
regression, versioned release-inclusion test or license approval. Accordingly
`approved_rules=0`, `independent_regression_verified=false`,
`production_approved=false` for every candidate below.

## Candidate A — incorrect remote-debugging disable option (priority 1)

- Original [python/cpython PR #159014](https://github.com/python/cpython/pull/159014),
  main merge `91248026c8a41910098032dd23f9a05ad2d9b513`,
  merged 2026-10-14. Documentation corrections were backported to
  [3.14 PR #159413](https://github.com/python/cpython/pull/159413)
  (`0d214f87921ab9b858cda64c290d89081335772f`) and
  [3.15 PR #159414](https://github.com/python/cpython/pull/159414)
  (`cf0c41f716871a8d19d56916e0be59d3beb887d5`).
- **Observed fault:** The 2026-10-09 Python **3.15.0 release tag**
  `v3.15.0`, `Doc/using/cmdline.rst`, spells the flag
  `-X disable_remote_debug`; `Python/initconfig.c` at the same
  tag checks only `L"disable-remote-debug"`. CPython's upstream
  [issue #159010](https://github.com/python/cpython/issues/159010)
  reports that the underscore spelling is silently ignored, leaving
  remote debugging active on supported/default builds. This is a
  **security configuration error**, despite the upstream fix being
  documentation-only.
- **Safe operator instruction (candidate):** For Python 3.14+ where the
  feature is available, use `python -X disable-remote-debug ...`
  (hyphens), never `-X disable_remote_debug`; verify on the *actual
  target interpreter* with `sys.is_remote_debug_enabled()`. The
  environment variable `PYTHON_DISABLE_REMOTE_DEBUG=1` is an
  alternate documented control. A `False` observation alone does not
  prove the flag worked if remote debug support is compiled out.
- **Owner-reported runtime observation (2026-10-17):** On the owner-host
  Windows Python 3.15 installation, a PowerShell STDIN probe invoked three
  **separate** interpreter processes with `-I`: no extra `-X` option
  printed `True`; `-X disable_remote_debug` printed `True`;
  `-X disable-remote-debug` printed `False` for
  `sys.is_remote_debug_enabled()`. This confirms the safe flag's effect
  and the misleading underscore option on **that tested runtime**.
  The operator supplied the printed outputs; no executable was acquired
  or run by the reviewer, and that invocation did **not** print the
  exact `sys.version`, binary digest, or subprocess exit codes.
  Do not misrepresent the host output as an independent runner test.
- **Remaining regression:** Independently repeat the three child-process
  observations on a version-identified, disposable feature-enabled
  Python runner. Confirm interpreter identity and observed exit codes.
  A 3.15 development-branch documentation fix does **not** retrofit
  the released 3.15.0 documentation.
- **Gate:** `SOURCE_RELEASE_TAG_AND_OWNER_RUNTIME_BEHAVIOR_MATCH`;
  independent runtime replication, distribution-specific rule acceptance,
  and production approval remain `NO_GO`.

## Candidate B — concurrent `os.scandir` iterator use and close (priority 2)

- [Original PR #153462](https://github.com/python/cpython/pull/153462),
  main merge `999a046b24cff4ba0e72b574196721f66bd08237`
  (2026-08-21); [3.15 backport #159365](https://github.com/python/cpython/pull/159365),
  `b3fae57cc5e04e2808aaa34b5297e96281673244`
  (2026-10-13); [3.14 backport #159381](https://github.com/python/cpython/pull/159381),
  `dacf472604ca7ccb806ed0737dec79847f71ac1d`
  (2026-10-14).
- **Observed fault:** [Issue #152754](https://github.com/python/cpython/issues/152754)
  explains a native directory-handle use-after-free when `next()`
  and `close()` race, especially in free-threaded builds. The 3.15.0
  release-tag `Modules/posixmodule.c` lacks the patch's
  `read_mutex`; the current `3.15` branch contains it. The
  `3.14` backport is later than the published 3.14.8 release.
- **Safe operator instruction (candidate):** Do not concurrently
  iterate/close **the same** `os.scandir()` iterator. Assign each
  thread its own iterator or serialize its `next()` / `close()`
  ownership. Avoid relying on unspecified cross-thread entry
  allocation. Existing UCIE first-party guarded-iterator tests cover
  its wrapper only, **not** a verified upstream before/after fix.
- **Unperformed regression:** Compare fixed pre/post interpreter builds
  only in a disposable isolated runner; native race reproducers may
  crash and must **not** be run on the owner's operational host.
  Upstream adds `Lib/test/test_os.py` close/next and shared-next
  tests. No verified fix is inferred from their presence alone.
- **Gate:** `PINNED_PATCH_AND_TEST_SOURCE_MATCH`; independently executed
  upstream regression and release inclusion `NO_GO`.

## Candidate C — deep lazy-import alias recursion (one bug family, priority 3)

- [Original PR #159289](https://github.com/python/cpython/pull/159289),
  main merge `25883627946b7cbcf7286acfe2a2019382375325`
  (2026-10-14); [3.15 backport #159416](https://github.com/python/cpython/pull/159416),
  `72ab89038441d7cd34c0d6e75873dcd7d3831dd4`
  (2026-10-14). **These are one issue family, not two independent fixes.**
- **Observed fault:** [Issue #159288](https://github.com/python/cpython/issues/159288)
  describes C-stack overflow from very deep `lazy import a.b... as x`
  placeholder chains. `Objects/lazyimportobject.c` at the released
  `v3.15.0` tag lacks the two targeted recursive-entry guards in
  `lazy_import_path()` and `lazy_import_replay_from()` added by the
  backport. The fix intends to raise `RecursionError` instead of
  crashing.
- **Safe operator instruction (candidate):** On an unpatched
  Python 3.15.0, avoid generating unbounded, deeply dotted *lazy*
  import aliases, especially from external input. Input-bound import
  depth; do not automatically execute the upstream reproduction.
- **Unperformed regression:** The upstream test uses 10,000 name parts
  and a limited C stack; verify only on a patched disposable build.
  **Never** execute a potential segfault reproducer in the owner's
  hourly collector or production interpreter.
- **Gate:** `PINNED_PATCH_AND_TEST_SOURCE_MATCH`; independent
  before/after and distribution-specific fix status `NO_GO`.

## Lower-priority screened candidate

[PowerShell/PowerShell PR #28209](https://github.com/PowerShell/PowerShell/pull/28209)
(merge `0d0bc7cdc5246e7837ec826ef816d4332f40df61`)
changes only `test/tools/TestService/TestService.csproj` to update
`Microsoft.Windows.Compatibility` from
`11.0.0-preview.4.26230.115` to `11.0.0-rc.1.26425.128`.
This is a **CI/test dependency pin**, not evidence of a generic
PowerShell command-safety call or runtime fix. Keep unverified, do not
promote to a PowerShell safety rule.

## Attribution, deduplication and license

Only approved public `python/cpython` and `PowerShell/PowerShell`
sources and official python.org 3.15.0 release information were consulted.
CPython's repository provides its `LICENSE` text; license review for
reuse/distribution is **not approved** here. PR commit hashes and PR
cross-references distinguish mainline fixes from backports; Stage12's
19 review *evidence revisions* must not be counted as 19 independent
bug families. These findings are a **manual static evidence review**,
not a mutation of the Stage12 queue, a permanent trained memory,
an approved Rulepack, or a deployed product rule.

Next gate: independently replicate Candidate A's owner-reported
three-process flag observation on a pinned disposable interpreter,
then carry out noncrashing provenance, regression and release-inclusion
checks for Candidates B and C where feasible. Do not run native crash
reproducers on the owner host or automatically approve candidates from
receipt counts, screenshots or green UCIE CI.
