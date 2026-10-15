# Stage 4 — PUBLIC_ONLY PR review (candidate-only)

This change extends **the existing `ucie_miner`**. It deliberately does **not**
install a second collector, migrate the existing 9 source records, publish
Rulepacks, read other projects, or claim independent testing of upstream fixes.

## Pipeline

1. Read `runtime/public_miner.sqlite3` in SQLite **read-only** mode. The
   original PRs and `UNVERIFIED_CANDIDATE_ONLY` flags are retained unchanged.
2. Match each `(allowlisted source, PR number, merged_at)` against the narrowly
   curated PUBLIC_ONLY manifest `curated_public/pr_review_evidence_v1.json`.
   Unknown or mismatching candidates need manual review; nothing is inferred
   from raw PR title/body/patch content.
3. Group known backports with their original upstream fix. In the nine-PR
   snapshot, PR #153462 and #159365 form one `os.scandir()` family, producing
   **eight distinct review patterns**. This is *not* eight approved rules.
4. Optional `--verify-live` reads exactly two allowlisted third-party GitHub
   repositories' PR metadata, then a pinned **release tag source file** for
   each matched PR. Network access is **anonymous, GET-only, bounded** and
   blocks redirects. A marker present at a release tag is **only a source-code
   clue**, not full patch inclusion, CI evidence, security certification, or a
   guarantee that the installed binary includes the fix. Absent/failed markers
   remain unresolved, never auto-promoted.
5. Write a local, separate `runtime/review_candidates.sqlite3` and the
   generated `runtime/reviews/candidate_review_v1.json`. These contain only
   candidate IDs, source URLs, rule-family IDs, release-check statuses and
   timestamps — no PR bodies/patches or user-project data.
6. Every row has `approval=0`. The stage does **not** call the existing
   `ucie_public.rulepack.publish_demo`, create a production signing key, modify
   the source DB, apply fixes, or run arbitrary upstream source code.

## Commands (PowerShell / verified Python 3.15 environment)

```powershell
Set-Location D:\UCIE
$env:PYTHONPATH = (Resolve-Path .\src).Path
$Python = Join-Path $env:LOCALAPPDATA 'UCIE\venv315\Scripts\python.exe'
& $Python -m unittest discover -s tests -v
# Read-only review preview, no network or local DB changes
& $Python -m ucie_miner review --preview
# Stage candidate review in a SEPARATE UCIE-local SQLite DB
& $Python -m ucie_miner review
# Optional: recheck upstream PR metadata and release-tag source snippets
& $Python -m ucie_miner review --verify-live
```

There are no background tasks or new scheduled-task registrations here.
`--verify-live` can be rate-limited or fail on DNS; failures **stay unverified**
without bypassing the allowlist. Do not interpret a successful offline unit test
as independent proof that upstream runtime vulnerabilities are fixed. Verify
release notes, signed binary version/build, and relevant regression behavior
separately before any automatic recommendation or Rulepack promotion.

## Nine-source evidence mapping (2026-10-14 public-only review)

| Upstream source | PR | Candidate theme | Pinned source tag / marker interpretation |
|---|---:|---|---|
| PowerShell/PowerShell | 25780 | SSH command lookup without a Runspace | v7.5.12; marker was observed; verify exact installed version |
| PowerShell/PowerShell | 28042 | Fuzzy `Get-Command` result de-duplication | v7.6.7; marker absent in inspected source |
| PowerShell/PowerShell | 28087 | Leading-dot names in `Resolve-Path -Relative` | v7.6.7; marker absent in inspected source |
| python/cpython | 153462 | Shared `os.scandir()` iterator race | v3.15.0; fix marker absent |
| python/cpython | 155365 | Free-threading thread-state slot cleanup | v3.15.0; marker observed |
| python/cpython | 156962 | Compiler comprehension failure cleanup | v3.15.0; marker absent |
| python/cpython | 159232 | AST `__repr__` / `_fields` lookup | v3.14.8; marker absent |
| python/cpython | 159364 | Free-threading weak-reference race | v3.15.0; marker absent |
| python/cpython | 159365 | `os.scandir()` 3.15 backport | **same family as #153462**; v3.15.0 marker absent |

These observations were obtained by examining the named public upstream PRs,
changed files, and pinned release-tag files; this stage stores curated metadata,
not upstream source. Details can change with newer upstream releases. Preserve
all original source records and do not treat branch merges as released fixes.

Repository source terms: [`python/cpython` PSF license](https://github.com/python/cpython/blob/main/LICENSE)
(including PSF License Version 2); [`PowerShell/PowerShell` MIT license](https://github.com/PowerShell/PowerShell/blob/master/LICENSE.txt).
Data review must continue to respect deletion/opt-out requirements, privacy,
secrets and copyright/licensing obligations. No private project code, logs,
conversation, account, token, connector or local project path is an upstream
training source.

## Independent regression gates *still required*

- **Windows PowerShell:** check SDK-hosted remoting with no Runspace; fuzzy
  duplicate modules, command identity and scoring; relative resolution for
  `.directory`, `..directory`, `directory` across OS and versions.
- **Python:** check `os.scandir()` iterator sharing and `close()`/`next()`
  races; free-threaded weak-ref race and reference stability; fault-injected
  compiler and thread-state allocation cleanup; AST subclass `_fields`
  behavior. Determine release and free-threading build status independently.
- Run dedicated, isolated regression tests on *actual affected binaries*,
  ensuring the version's source/commit and test result are bound together.
- Require human-approved licensing and release traceability, independent
  patch regression test, a signed versioned Rulepack and a receiving project's
  isolated CI before deployment. None of these are granted by this feature.

**Acceptance:** nine mapped PRs / eight distinct families is a deterministic
**offline review result** only. `rules_promoted=0`, `patches_independently_tested=0`
and `production_approved=false` remain mandatory.
