# UCIE Stage 12 — automatic unverified review preparation

Stage 11 already automatically collects up to 8 approved public API GETs
during an authorized existing hourly UCIE cycle and stores candidate metadata
in `runtime/stage10_unverified_public_candidates.sqlite3`.

Stage 12 adds a **non-model, non-executing, repeatable public evidence
candidate review** operation, not model weight training. It reads only the
existing Stage 10 ledger using `mode=ro`, validates source/revision/tag
identity, classifies broad error patterns using fixed allowlisted categories,
and selects safe review guidance plus an offline regression plan from the
existing first-party skill profiles. Results are candidate-only entries in
the *separate* `runtime/stage12_unverified_review.sqlite3` database. Repeating
the same evidence digest does not insert duplicates. New revisions append
new unsigned review tasks. No patches, titles, prompts, executable source,
credentials, external paths or model weights are learned/retained.

**Stage 12 is OFF by default, regardless of Stage 11 activation.**
The owner must separately approve its disk review-queue writes by creating
exactly one optional file containing a pinned ASCII token:

- Path: `D:\UCIE\runtime\stage12_review_opt_in.txt`
- Contents: `UCIE_STAGE12_REVIEW_OPT_IN_V1`

After code review, CI and `main` merge, update only the existing UCIE
checkout. The existing `UCIE-PublicMiner-Hourly` Windows Scheduled Task
continues unchanged. Stage 11 must also remain enabled for the hourly
new-input → Stage 12 output pipeline to execute.

Read-only preview **before enabling**:

```powershell
$previous = $env:PYTHONPATH
try {
    $env:PYTHONPATH = 'D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner preview-stage12-review
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner inspect-stage12-review
}
finally { $env:PYTHONPATH = $previous }
```

Explicit owner activation **after inspection**:

```powershell
$marker = 'D:\UCIE\runtime\stage12_review_opt_in.txt'
if (Test-Path -LiteralPath $marker) { throw 'Existing opt-in marker: review first' }
Set-Content -LiteralPath $marker -Value 'UCIE_STAGE12_REVIEW_OPT_IN_V1' -Encoding Ascii -NoNewline
```

An optional **one-shot no-network** review pass can run immediately rather
than waiting for the next regular hourly legacy mining cycle:

```powershell
$previous = $env:PYTHONPATH
try {
    $env:PYTHONPATH = 'D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner run-stage12-review-once
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner inspect-stage12-review
}
finally { $env:PYTHONPATH = $previous }
```

No task registration, CI runner hosting, third-party code execution,
automatic production rule approval, human approval forgery, learning weight
updates, code patches, or Rulepack signatures are performed.

To stop **future** Stage 12 candidate review writes, remove only
`runtime/stage12_review_opt_in.txt`. This will not interrupt the existing
hourly legacy miner or Stage 11 collection, and will not delete already
stored candidate review history. Deletion/opt-out is a separate human
reviewed action.

Success criteria are separate: Stage 11 public collection receipt,
Stage 12 candidate review count and explicit owner-PC task timestamps.
`STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO` means review suggestions were
prepared, **not** that fixes were independently verified or the model
learned weights. No production GO is implied.


## Existing hourly pipeline: automatic public-evidence study (no new Stage or task)

The existing authorized \`UCIE-PublicMiner-Hourly\` sequence is now:

\`legacy miner → Stage11/Stage10 public candidate intake → Stage13 historical
metadata → Stage14 official-source observation → Stage15 fix evidence →
Stage12 existing unsigned review queue\`.

The *ordering matters*: Stage12 runs **after** Stage15 has committed its
current-cycle evidence. It derives a review task from each properly linked
Stage15 revision, validates the Stage13↔15 chain using Stage16 checks, and
selects a fixed UCIE-authored safe-call question/regression review plan.
This gives a durable, incremental 'study' result in the **existing**
\`runtime/stage12_unverified_review.sqlite3\` without any new SQLite
schema or scheduled task. New evidence revisions append separate review
tasks; revisiting the same revision produces zero new rows. The optional
Stage14 official document/release/security observation is NOT automatically
claimed to apply to a PR or prove its released version.

Important authorization boundaries:

- The legacy miner keeps its original schedule and lock.
- Existing Stage11 activation is still required to enter the hourly
  public candidate pipeline: \`stage10_hourly_opt_in.txt\`.
- Stage12 review writes still require exactly its **own** original opt-in
  \`stage12_review_opt_in.txt\` token documented above.
- Enriching and incorporating Stage15 fix evidence requires **both**
  the Stage12 review marker and the original independent
  \`stage15_fix_evidence_opt_in.txt\` token
  \`UCIE_STAGE15_FIX_EVIDENCE_OPT_IN_V1\`. Merely having an old Stage15
  database does not silently expand Stage12's authorization.
- Stage13 and Stage14 public requests still require their existing
  independent owner opt-ins. The Stage13 index itself is only *read*
  for Stage15 linkage, even if historical backfill is disabled.
- Marker absent: disabled stage does not perform its new network or review
  writes. Invalid markers or broken Stage13↔15 provenance fail closed.
- The Stage12 review queue contains **unverified** suggestions, never
  verified fixes, release-coverage promises, automatically learned model
  weights or production Rulepacks.

### Operator read-only status and one-shot review (no additional API)

After a successful reviewed \`main\` update, check the public-study pipeline
without activating any markers:

~~~powershell
$prior = $env:PYTHONPATH
try {
  $env:PYTHONPATH = 'D:\UCIE\src'
  $py = 'D:\UCIE\.venv\Scripts\python.exe'
  & $py -B -m ucie_miner inspect-external-history
  & $py -B -m ucie_miner inspect-fix-evidence
  & $py -B -m ucie_miner audit-external-evidence-chain
  & $py -B -m ucie_miner preview-stage12-review
  & $py -B -m ucie_miner inspect-stage12-review
} finally { $env:PYTHONPATH = $prior }
~~~

If the owner wants recurring review writes, inspect and separately enable
the Stage12 marker as documented above. If also enabling recurring Stage15
deep-evidence reads, inspect/enable its existing marker as documented in
\`docs/STAGE15_EXTERNAL_FIX_EVIDENCE.md\`. **Do not create opt-in files
on behalf of the owner.** Limit simultaneous manual \`--live\` calls:
the authorized hourly cycle already consumes up to 20 public GETs in the
fully opted-in configuration, shared against GitHub's anonymous API quota.

\`run-stage12-review-once\` runs existing review logic without network and
can process already recorded Stage15 evidence **only while both Stage12 and
Stage15 markers remain authorized**. \`inspect-stage12-review\` now separates
\`by_evidence_origin\`: \`stage10_pr_metadata\`,
\`stage10_git_metadata\`, and \`stage15_fix_evidence\`. These are counts
of *review records*, not deduplicated real-world bug families.

The existing Windows host's actual task state, active owner markers and
hourly receipts must be checked separately; CI synthetic tests are not an
attestation of local activation or a claim of model training.


## Existing Windows hourly timing and persistent diagnostics

The recurring Windows task is start-time based. A successful worker cycle
normally finishes several seconds after the hourly trigger; the previous
finish+60min guard could therefore skip the *next* regular trigger, turning
intended hourly collection into effective two-hour collection.

The worker now respects the **prior recorded start timestamp + 60min** for
successful cycles, with the prior finish as a minimum boundary and the
original operating-system single-instance lock still in place. Failed
cycles retain the original completion-anchored retry backoff. Historic
receipts lacking a start timestamp retain the old fallback. No task
registration, trigger update or new scheduler is required.

Existing \`runtime/last_run.json\` and \`run_history.jsonl\` now retain only
the sanitized optional public stage \`stage10_status\` and, on failure,
\`stage10_error_type\` (Python exception class name, no exception text).
\`COLLECTED_UNVERIFIED\` still describes **legacy miner collection only**:
check \`stage10_status\` before claiming that the additional opt-in
external study pipeline succeeded. Exit code 2 with an otherwise successful
legacy receipt may indicate \`STAGE10_HOURLY_FAILED_NO_GO\` in the new receipt.

Owner-host command after an actual newly scheduled execution (read-only):

~~~powershell
& 'D:\UCIE\scripts\task_status.ps1'
Get-Content 'D:\UCIE\runtime\run_history.jsonl' -Tail 3
~~~

Never rewrite existing receipts to pretend that historical optional-stage
diagnostics were known. Offline CI verifies only behavior on disposable
test hosts, not the owner's actual hourly task.


## Stage13 optional public backfill failure isolation (owner case: 2026-10-17)

An actual owner-PC hourly run returned \`stage10_error_type=ValueError\`.
A constrained local traceback located the deliberate Stage13 failure escalation
in \`public_hourly_staging.py\` (the prior 82nd line), not a failure in the
legacy two-source miner. Stage13 had reported
\`EXTERNAL_HISTORY_UPSTREAM_OR_METADATA_FAILED_NO_GO\`. The underlying cause
was not distinguishable from previous receipts.

Stage13 now reports bounded, non-text diagnostic fields on this failure:
\`failure_source\` (exactly one of the five approved public repos) and
\`failure_category\` (either \`FETCH_OR_RESPONSE_REJECTED\` or
\`PUBLIC_METADATA_REJECTED\`). No HTTP body, URL parameter, exception
message, upstream title or code is retained. The failed public source
cursor stays on the rejected page: **no bypass of evidence validation**.

This recoverable **optional upstream** failure no longer prevents already
independent Stage14 observation, Stage15 fix-evidence collection and Stage12
unverified review of properly linked, previously collected Stage13 revisions.
The overall Stage10 receipt is \`STAGE10_HOURLY_PARTIAL_NO_GO\`, **not**
\`STAGE10_UNVERIFIED_STAGED_NO_GO\`. The Windows task still exits with code
**2** to signal degradation; it must not be reported as full success.
\`runtime/last_run.json\` now records:
\`stage10_status\`, \`stage13_history_status\`,
\`stage13_failure_source\`, \`stage13_failure_category\`,
\`stage12_review_status\` and \`stage12_review_proposals_added\`.
Some may be absent when the corresponding optional stage is disabled or
fails before the receipt exists.

When diagnosing a recurring public metadata error, use the bounded receipt
to identify the approved public source, then separately review its pinned
public upstream evidence. Do **not** skip malformed PRs, move cursors past
unknown data, disable allowlists, reinstall the scheduler, auto-promote
rules or treat unverified reviews as confirmed fixes. Retain opt-out
and independent human activation exactly as before.


## 2026-10-17: approved git/git closed PR page 22 rejected for irrelevant unmerged title

Owner-host Stage13 read-only inspection fixed its \`git/git\` cursor on
page 22. A public read of that *allowlisted* GitHub closed-PR page found
\`git/git#1774\` with \`merged_at=null\` and a 419-character title.
Previously Stage13 checked the 400-character title bound for **every**
closed PR before excluding unmerged PRs, so one out-of-scope entry
rejected the whole historical page as \`PUBLIC_METADATA_REJECTED\`.

Stage13 now validates bounded PR numbers and duplicate page identities,
skips **unmerged** PRs without accepting/storing them, then applies the
unchanged strict title length, URL, repository identity and SHA checks
to **merged** PRs only. A synthetic 20-unmerged-row page-22 regression
proves the cursor advances, while an oversized *merged* title is still
rejected without advancing the cursor. Do not weaken merged evidence
verification, manually move owner-host cursors, or claim that previously
rejected PRs are verified fixes. The actual owner Windows run after
this patch is a separate operational verification.
