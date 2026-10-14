# UCIE Stage 6 — Runtime failure containment and first-party safe-call regression

**Status: mitigation candidate; upstream before/after verification is still NO-GO.**

## Observed defects before this mitigation

The disposable hosted runners produced reproducible adverse observations:

- The raw shared `os.scandir` iterator produced missing/duplicate entries or errors on
  Windows/Ubuntu Python 3.13 and Python 3.15.
- The raw concurrent `next()/close()` case crashed an isolated Linux
  CPython 3.13.16 process (SIGSEGV, exit -11) and a Linux 3.15.0 process
  (SIGABRT, exit -6). The pre/post upstream commit lineage was **not**
  attested. Do not automatically retry this native crash in ordinary CI.
- PowerShell 7.6.6 on hosted Windows returned two candidates for the fuzzy
  duplicate command fixture (expected one) and did not satisfy the
  dot-prefixed path contract tested by the UCIE fixture. A runner's
  installed 7.6.6 is not the pinned PowerShell merged revision.

Original CI observations are preserved in PR #15:
- https://github.com/tmdrkdtn1-project/UCIE/actions/runs/38518730702
- https://github.com/tmdrkdtn1-project/UCIE/actions/runs/38518904264
- https://github.com/tmdrkdtn1-project/UCIE/actions/runs/38519080160

## First-party containment — Python

`ucie_miner.guarded_scandir.GuardedScandir` serializes **all** calls to
`next()` and `close()` on one owned `os.scandir` iterator with a single
lock. Consumers share only this wrapper and use `with` or explicit
`close()`. This prevents **UCIE-controlled callers** from directly racing
the raw native iterator. The guard is only a candidate implementation and
has not been promoted into the running public miner.

`tests/test_ucie_guarded_scandir.py` exercises concurrent readers and
closers using disposable temporary trees. The hosted runtime probe executes
guarded tests in separate short-lived child processes and reports failures
with error types. It **never automatically invokes the known crashing
unprotected close/next test**. Historic unguarded failures remain explicit
in the JSON observation as `OBSERVED_*_NOT_RETESTED`.

## First-party containment — PowerShell

`scripts/ucie_safe_powershell_results.ps1` offers *data-only* helper
functions to deduplicate fuzzy `CommandInfo` candidates using logical
identity, and to derive `./`-prefixed relative paths from explicitly
selected directory search results. The helpers do not execute returned
commands, install software, connect to an SSH server, or mutate system
configuration. PowerShell runtime observations report both raw results and
the separately checked guarded result. A guarded FAIL is a CI failure;
a raw FAIL is **preserved**, not disguised as an upstream fix PASS.

## CI meaning

The standard Windows/Ubuntu × Python 3.13/3.15 matrix checks:
- existing unit/security tests
- UCIE guard concurrency and cleanup tests
- bounded first-party guarded CPython runtime probes
- on Windows, PowerShell guarded command/path contract checks alongside raw
  runtime observations

**A green guard test establishes only that the guarded UCIE first-party
workaround behaved as expected in the sampled hosted environment.**
It does not demonstrate a fix to `python/cpython` or PowerShell,
independent affected-version coverage, exact SHA-matched before/after
regression, human authorization, Rulepack signing or operating-host PASS.

The Stage 7/8 release gate remains `NO_GO`. Known raw native crashes are
quarantined from automatic replay; a separate explicitly approved and
crash-isolated review is required for any further native reproduction.
No operating UCIE database, OS scheduler, release package or `main`
branch is modified by this draft.
