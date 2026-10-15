# UCIE Stage 7–8 independent evidence preparation and acceptance v2

**Scope:** This is a candidate-only development change on an isolated UCIE
Git branch. It extends Draft PR #11 / #10; `main` and the operating collector
are unchanged.

## A. Official upstream license markers (not legal approvals)

The approved public sources presently handled by Stage 4 are
`python/cpython` and `PowerShell/PowerShell`. The following **official**
published license statements were reviewed:

- Python 3.15 official history/license: https://docs.python.org/3/license.html
- CPython public license source: https://github.com/python/cpython/blob/main/Doc/license.rst
- PowerShell public license: https://github.com/PowerShell/PowerShell/blob/master/LICENSE.txt

The optional `audit-license --verify-live` function retrieves **only
bounded, pinned-tag public license-document files** allowed by Stage 4
(e.g., `Doc/license.rst` and `LICENSE.txt`) using anonymous HTTPS GET.
It records only a SHA-256 digest and a **marker-present/absent** status;
it does not copy or redistribute the full source. A marker at a release
tag is not proof that an individual PR's changed files, the exact merge
commit, dependencies, or a binary are independently license-reviewed.
A synthetic injected downloader is never an authoritative upstream
verification.

All other research-allowed upstream repositories remain within the
project's published policy but are **not** silently enabled in this
pinned Stage 4 review adapter.

## B. Stage 6 independent regression case preparation

`preview-regressions` emits eight deterministic non-executable case
plans for the eight pinned Stage 4 error families. Each case describes
a synthetic fixture, expected invariant, negative case, platform and
the required independent evidence. The generator rejects forged
Rulepack hashes, pre-approved evidence flags, injected execution
commands and source/PR inconsistencies. Actual upstream behavioral
reproduction is **NOT_EXECUTED**. No external fixes are imported, tested
or run by this change.

## C. Windows read-only preflight and operational bundling

`src/ucie_miner/host_preflight.py` inspects only a supplied UCIE
checkout's `runtime/public_miner.sqlite3` and `runtime/knowledge.sqlite3`
through SQLite `mode=ro` with `PRAGMA query_only=ON`. It does not
migrate data or create a missing Knowledge DB. Absence, bad schema,
bad integrity, wrong host/Python version and unsafe symlink paths are
reported as incomplete or unavailable rather than PASS.

The strictly pinned Windows manual entrypoint is
`scripts/ucie_readonly_host_preflight.py`, with fixed `D:/UCIE`
checkout and Python 3.15 identity. **Do not run on the owner PC without
separate operational approval.** The GitHub CI performs only synthetic
fixtures.

The `preview-acceptance` command composes existing *read-only*
Knowledge-to-pattern audit, offline PR provenance receipt, offline
license marker receipt, candidate regression plans and DB preflight.
Output status is unconditionally **NO_GO** because independent
validation, human authorization and signing are not present. Its
Windows check is read-only and cannot attest the machine's ownership
or scheduler state.

## Safe isolated development checks

Run offline unit tests only in an isolated UCIE development checkout:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m ucie_miner audit-license
.\.venv\Scripts\python.exe -m ucie_miner preview-regressions
.\.venv\Scripts\python.exe -m ucie_miner preview-acceptance
```

The last two preview commands correctly fail closed if the separate
Knowledge database has **not** been provisioned under independent
authorization. Neither command should be interpreted as permission
to run the one-shot Knowledge import.

Real source authenticity and per-commit licensing, external issue
reproduction, security signoff, authorized Rulepack signing and actual
Windows host acceptance remain explicit independent gates.

**Prohibited:** automatic rule promotion, nonapproved upstream code
execution, permanent operating DB import, package deployment, task
registration, unapproved repository reads, or claims that synthetic
CI tests reproduced upstream fixes.

**Status:** `DEVELOPMENT_ONLY / NO_GO / NO_PROMOTION`.
