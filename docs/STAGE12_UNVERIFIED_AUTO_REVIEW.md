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
