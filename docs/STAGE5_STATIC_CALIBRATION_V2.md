# UCIE Stage 5 — Literal branch and local scanner alias calibration V2

Draft-only improvement on top of the verified Stage 5–7 candidate pipeline
(PR #19). This update does **not** authorize collection of additional
repositories, execute input code, alter operational databases, or promote rules.

## Changes

Python's inert `ast.parse` scanner now detects a locally assigned
`alias = os.scandir` followed by `it = alias(path)`, or a function-local
`from os import scandir as scanned`. It also clears the alias when rebound
to a different value. It ignores AST subtrees under **literal** `if False`
or `if 0`, including nested functions, and retains the true branch for
`if True` or `if 1`. Unknown/nonliteral conditions remain review candidates.
No expression is evaluated and imports are never executed.

PowerShell's inert `Parser.ParseInput` scanner recognizes the fixed,
built-in `gcm` spelling of `Get-Command` and ignores command ASTs
contained in a literal `if ($false)` or `if (0)` body. Nonliteral
conditions remain candidates. It does **not** invoke `Get-Alias` or
evaluate scripts or dynamic alias assignments.

## Same-fixture synthetic calibration, not production accuracy

The same small UCIE-authored fixture sets from PR #19 are reused **only
to measure the impact of these particular changes**:

| Language | Before | Intended V2 result on identical fixtures |
| --- | --- | --- |
| Python | 6 TP / 1 FN / 1 FP / 6 TN (14 cases) | 7 TP / 0 FN / 0 FP / 7 TN |
| PowerShell | 2 TP / 1 FN / 1 FP / 2 TN (6 cases) | 3 TP / 0 FN / 0 FP / 3 TN |

The tests also add independent synthetic cases for reassigned aliases,
imported local aliases, true/false literals, unknown conditions and
nested unreachable scopes. Passing every deliberately curated fixture
**is not** a real-world accuracy result, representative dataset claim,
or proof of all dangerous shared-iterator patterns.

Known remaining limitations: module-level imports used inside nested
functions, re-exported/dynamic aliases, arbitrary control-flow and
interprocedural analysis, custom shadowing of `os`, runtime behavior,
PowerShell dynamic aliases, nested conditional inference and exact
upstream before/after binary fixes. Unrecognized risky code may still
produce zero findings. No-finding status is NOT a safety PASS.

All diagnostics remain `STATIC_HEURISTIC_REVIEW_REQUIRED`, bind only to
previously pinned approved public PR identities, and retain independent
regression, reviewer, license, signature and operating-host gates as
`NOT_VERIFIED` or `NO_GO`.

## Isolation

Only first-party UCIE-authored synthetic inputs are analyzed in this
branch's CI. No untrusted upstream code is executed, no raw native
scandir crash is replayed, no permanent UCIE DB or scheduler is changed,
no other projects are accessed, and no code/Rulepack is deployed or
merged into `main`.
