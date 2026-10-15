# UCIE Stage 11 — Reuse the existing hourly miner (explicit opt-in)

The existing Windows Scheduled Task named `UCIE-PublicMiner-Hourly` stays
registered with its original action, Python executable, trigger, owner and
working directory. No new task or timer is created by this change.

The existing two-source miner still runs FIRST, under the original
`public_miner.lock`, with unchanged miner SQLite and run-receipt semantics.
Only **after it succeeds**, the optional Stage 10 candidate collector may
run, sharing the same OS-held lock. A missing opt-in file means **legacy
behavior only**.

The operator must choose whether and when to create precisely this file:

    D:\UCIE\runtime\stage10_hourly_opt_in.txt

File content (ASCII, optional trailing newline):

    UCIE_STAGE10_HOURLY_OPT_IN_V1

Never register another task. No marker is created automatically by this PR.
Wrong, reparse/symlinked or oversized marker means fail closed with an
explicit Stage 10 error; the successful legacy miner receipt remains intact.

With explicit opt-in the extra one-shot candidate batch:

- Looks only at the five previously approved public repos, including
  commit-only `git/git` leads. All GitHub calls are anonymous and
  bounded by **8 GETs per scheduled hourly run** (5 public PR feed
  metadata GETs, at most 2 PR evidence GETs for one selected PR, and
  one git/git direct-commit metadata GET).
- Runs no third-party code, retains no raw patches, and invokes no
  official docs or advisory GET in this hourly path.
- Appends at most one new PR candidate and one direct Git commit
  candidate **revision per hourly cycle** to the isolated
  `runtime/stage10_unverified_public_candidates.sqlite3` candidate-only
  ledger. (Identical metadata is idempotent.)
- Does not write `runtime/public_miner.sqlite3` or
  `runtime/knowledge.sqlite3` from Stage 10.
- Does not auto-promote, verify, sign, train, distribute or publish
  rules; all candidate status remains `UNVERIFIED_CANDIDATE_ONLY`.

If the optional Stage 10 fetch or stage fails, its exception TYPE only is
reported as `STAGE10_HOURLY_FAILED_NO_GO`, the OS task exit code is nonzero,
and the previous successful legacy receipt is NOT rewritten to falsely
indicate that the legacy collector failed. Inspect the reported Stage 10
status before retrying; GitHub anonymous rate limits can cause failure.

The original hourly scheduling policy remains authoritative:
`SKIPPED_NOT_DUE` and `SKIPPED_ALREADY_RUNNING` never trigger Stage 10
network requests. This is not an additional background scheduler.

## Owner-PC release gate

After CI passes and the reviewed PR is merged into `main`, update the
existing UCIE checkout on the operator's PC. Verify the existing task
action/owner and last-run result independently; `Ready` is not a PASS.

**Operator activation** (only after deciding to enable the bounded extra
public API traffic and after local code update):

    if (Test-Path 'D:\UCIE\runtime\stage10_hourly_opt_in.txt') {
        throw 'Existing Stage 10 opt-in marker requires manual review'
    }
    Set-Content -LiteralPath 'D:\UCIE\runtime\stage10_hourly_opt_in.txt' -Encoding Ascii -Value 'UCIE_STAGE10_HOURLY_OPT_IN_V1'

**Reversible stop without altering the old scheduled task**:

    Remove-Item -LiteralPath 'D:\UCIE\runtime\stage10_hourly_opt_in.txt'

Removing the marker disables *future* Stage 10 ingestion; it does **not**
delete existing candidate rows (right-to-delete/opt-out review requires
a separately authorized process). Stop/retry the action only on operator
choice; changing this file while a running cycle is already processing
it does not cancel that current cycle.

**Do not claim the user's PC is activated or that the scheduler has succeeded
until an actual local task receipt and updated candidate inventory show it.**
