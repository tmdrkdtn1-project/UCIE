# UCIE Stage 5–7 Flow and Review Docket Hardening

**Scope:** UCIE-only Draft development branch based on PR #20. The allowed
public provenance remains the pinned `python/cpython` and
`PowerShell/PowerShell` Stage 4 records. No new upstream source is
authorized, executed or imported.

## A. Python lexical dataflow (inert AST)

`static_concurrency.py` now tracks binding changes in lexical source
order. It distinguishes known local `os.scandir` function aliases, imported
module aliases, raw iterator copies, and later reassignments:

- `import os as fs; it = fs.scandir(path); pool.submit(fn, it)`
- `it = os.scandir(path); copy = it; pool.submit(fn, copy)`
- `from os import scandir as scan` before a nested function
- `alias = list` or `copy = list(copy)` after initial raw binding
- `os` shadowed by a local function parameter or assignment
- alias created only *after* a call (no backward-in-time effect)

A limited snapshot of direct, statically recognized module/function
imports is inherited into nested functions; function parameters override
imported names. This is **not general interprocedural flow analysis**.
A conditional branch can still produce imprecise lexical results; dynamic
imports, reflection, arbitrary user-defined module objects, flow merges,
and native lifetime proof remain unimplemented. No text is evaluated.

## B. PowerShell fixed aliases and source-defined shadows

The inert PowerShell AST scanner additionally recognizes the documented
`rvpa` alias for `Resolve-Path` and avoids treating calls to an explicit,
preceding source-defined `function gcm`, `function Get-Command` or
`function Resolve-Path` as built-in commands. A function declaration
inside a literal dead branch does not suppress subsequent built-in
candidate analysis.

PowerShell aliases can be dynamically changed; **no external Get-Alias,
command resolution, execution or user-environment inspection occurs**.
Statements may run under different scopes/conditions; findings are still
`STATIC_HEURISTIC_REVIEW_REQUIRED`, not a proven bug or fix.

## C. Stage 7 and 8 external-evidence scope

`prepare_independent_review_docket` separately surfaces external
regression-claim case IDs with no matching static candidate. An unrelated
claim must not silently count as a reviewed finding. Stage 8's optional
read-only acceptance bundle exposes the unlinked count. Independent
reviewer authentication and real before/after regression remain
`NOT_VERIFIED`; **NO_GO** is unconditional.

## Evaluation contract

The existing 14-case Python and 6-case PowerShell UCIE-authored synthetic
calibrations remain as regression baselines. New deliberately synthetic,
bounded fixtures cover cross-scope module aliases, raw iterator copies,
alias ordering/clearance, parameter shadows, PowerShell `rvpa`,
source-defined function shadows and literal unreachable definitions.
The new fixtures are not a randomly sampled independent dataset. Any
observed perfect synthetic score says nothing about real-world
precision/recall, scanner completeness or signed Rulepack eligibility.

A fingerprint or case ID match does not authenticate a submitted external
claim. No upstream code checkout/execution, third-party repository access,
private files, native raw-crash replay, production DB writes, auto-rule
promotion, scheduler installation, signer or production deploy occurs.

**Release gate: DEVELOPMENT_CI_ONLY / INDEPENDENT_FIX=NOT_VERIFIED /
PRODUCTION_APPROVED=FALSE / NO_GO.**
