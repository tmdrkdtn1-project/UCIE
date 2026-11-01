# UCIE V1.2 — Hourly execution proof and opt-in library quality loop

Date: 2026-11-01. Scope: UCIE only. No private user projects or sources.

## What is, and is not, automatic learning

1. The existing Windows task UCIE-PublicMiner-Hourly collects bounded
   anonymous public candidate metadata each hour when actually running.
   It is not model weight training.
2. Stage10 additional approved-five-source public candidate collection
   requires the preexisting owner Stage10 marker.
3. Stage12 unverified-only deterministic review classification requires
   its separate owner Stage12 marker; it never auto-approves a rule.
4. Stage16 limited safe public evidence QA requires its own pinned input.
   A current run may explicitly report DISABLED or quota PAUSED.
5. New Stage17 is a separate opt-in **source-linked quality drift monitor**
   inside the SAME existing hourly worker lock. It inspects current
   source-linked candidate count, negative changes, V0.5 claim conflicts,
   orphan receipts, source SHA drift, and prior snapshot integrity.
   It does not fetch the internet, train an LLM, self-modify code or
   automatically approve/execute fixes.

## Verify current Windows scheduler and library stages

After precise SHA-pinned owner installation, run on actual owner Windows PC:

    & 'D:\UCIE\scripts\ucie_library_hourly_proof_v12.ps1'

This combines two **independent** checks:
- Existing task_status.ps1 -Evidence: Windows scheduled task identity,
  next cadence, limited user, task instance GUID events 100/200/201/102,
  and binding of two real scheduler instances to two collector receipts.
- New V1.2 read-only receipt analyzer: last_run.json vs the last two
  run_history.jsonl receipts, status and timestamps, 50–90 minute gap,
  last completed within 90 minutes, stage10/12/13/15/16/17 statuses,
  and separate stage marker presence.

Combined positive status HOURLY_COLLECTOR_CURRENTLY_EVIDENCED_NO_AUTO_APPROVAL
requires both checks; the Python receipt alone is NOT scheduler event proof.
Stage12 unverified review and Stage17 quality are reported as separate
booleans, not inferred from task registration or previous UI screenshots.

Run even before V1.2 installation, as a prior evidence check:

    & 'D:\UCIE\scripts\task_status.ps1' -Evidence

If current tunnel is offline, ChatGPT cannot inspect the Windows PC, so
an owner-shared result remains necessary for real current-state PASS.

## Explicit owner-gated quality monitoring

Stage17 is NOT enabled by installation. To inspect current owner markers:

    & 'D:\UCIE\scripts\ucie_quality_control_v12.ps1'

When both existing Stage10 and Stage12 opt-in tokens are present and the
owner chooses automatic quality observation for future cycles:

    & 'D:\UCIE\scripts\ucie_quality_control_v12.ps1' -Enable

This creates only UCIE runtime/stage17_quality_opt_in.txt through
CreateNew; never schedules, starts a worker, alters a user identity or
enables Stage10/12 on behalf of the owner. Future existing hourly runs
call Stage17 after Stage16 under the existing single-instance lock.
Inspect the resulting rolling snapshot later with:

    & 'D:\UCIE\scripts\ucie_quality_status_v12.ps1'
    & 'D:\UCIE\scripts\ucie_library_hourly_proof_v12.ps1'

To opt out, without touching other stages or local ledgers:

    & 'D:\UCIE\scripts\ucie_quality_control_v12.ps1' -Disable

Safe statuses: STAGE17_QUALITY_DISABLED,
STAGE17_QUALITY_OBSERVED_UNVERIFIED_NO_GO,
STAGE17_QUALITY_REVIEW_REQUIRED_NO_GO.
Review-required or stale/corrupt source is never converted to PASS.
A missing marker never creates a quality file.

## Changed paths (three narrow replacements)

- src/ucie_miner/public_discovery.py: recognized Stage17 error phase
- src/ucie_miner/public_hourly_staging.py: optional Stage17 check invoked
  only after the pre-existing Stage10 opt-in, Stage12 and Stage16.
- src/ucie_miner/worker.py: validated Stage17 status/count/delta in the
  original bounded receipt; preserves safety and old collector counts.

## Seven new paths

- src/ucie_miner/library_hourly_proof_v12.py
- src/ucie_miner/library_quality_loop_v12.py
- scripts/ucie_library_hourly_proof_v12.ps1
- scripts/ucie_quality_control_v12.ps1
- scripts/ucie_quality_status_v12.ps1
- tests/test_ucie_library_v12.py
- docs/UCIE_V12_HOURLY_PROOF_AND_QUALITY_LOOP_20261101.md

Total: 10 paths. No blanket Git pull, reset, clean or broad checkout.
Check exact previous file blob hashes and restore ONLY these paths from
a pinned CI-tested merge commit, with backups of the three replacements.

## Synthetic regression

    $env:PYTHONPATH='D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_library_v12.py' -v

Covers freshness/cadence, forged approval and run receipt divergence,
Stage17 disabled zero-work behavior, owner marker validity, source-linked
candidate growth/shrink/conflict detection, snapshot hash chain integrity,
and fail-closed existing worker receipt validation.

CI Windows/Linux Python 3.13/3.15 tests program behavior, not actual
owner task instance success. Actual scheduled evidence must come from
the owner Windows PowerShell report.

## Security and scientific boundaries

- No approved public source expansion, private data, other projects,
  imported upstream code or prompt-injection instruction execution.
- A public candidate is always UNVERIFIED_CANDIDATE_ONLY until separate
  independent evidence and explicit human signoff.
- No new scheduled task, worker privilege, rule release, auto promotion,
  database write or LLM weights update from V1.2.
- Stage17 performs only a tiny local SHA self-integrity rolling snapshot,
  which is neither a cryptographic signature nor a model improvement.
- The existing hourly scheduler can fail or pause; no status is reported
  as current without actual timely local receipts and scheduler events.
