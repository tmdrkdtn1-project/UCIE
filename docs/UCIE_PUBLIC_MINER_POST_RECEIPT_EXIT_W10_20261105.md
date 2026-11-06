# UCIE W10 — verify Python process exit AFTER public miner receipt (2026-11-05)

PROJECT=UCIE ONLY. First-party forensic/diagnostic workflow. NO production repair.
Applies only to fixed public collector task \UCIE-PublicMiner-Hourly.
No other project access, new collector job, database writes, external APIs,
task modifications, rule promotions or model training.

## Owner-reported and independently reverified evidence

The owner's original report at 2026-11-05T06:15:25Z had:
- Original public PR candidates: 359 (python/cpython=349, PowerShell/PowerShell=10)
- Collector run records: 491
- Stage10 unverified PR revisions: 126
- Stage12 unverified review proposals: 811
- Local hourly receipts recent and apparently successful, while
  Windows task status LAST_TASK_RESULT_NO_GO.
- Exact task state Ready; LastTaskResult decimal 267014 (0x00041306),
  Windows SCHED_S_TASK_TERMINATED; exact valid task-event matches 1/2.

TaskScheduler/Operational exact-instance evidence confirms two lifecycles:

| KST start | Worker receipt completion | action 201 completion | Exit result | Action duration | After-receipt lag |
| --- | --- | --- | --- | --- | --- |
| 13:37:10 | 13:37:19 | 13:37:19.893 | 0x00000000 | 9.754s | 0.893s |
| 14:37:10 | 14:37:19 | 14:47:10.169 | 0x8007050B | 600.017s | 591.169s |

Owner's exact task settings: ExecutionTimeLimit=PT10M, StopIfGoingOnBatteries
and DisallowStartIfOnBatteries both true. The 600s action lifetime matches
that time limit, so time-limit termination is a strong *hypothesis*.
A matching duration and nonzero action result do not independently prove
cause. Do not give the failure 201 code a guessed error name.

Important distinction: receipt means the worker recorded a cycle result,
NOT that Python ended, STDOUT flushed or Windows marked task success.

## Implemented isolated first-party process exit test

- src/ucie_miner/public_miner_exit_probe_v01.py
  - Default no-execution static preview.
  - Only --run-synthetic spawns fixed sys.executable with -I -B and a
    first-party static child script; no network or collector call.
  - Loads UCIE's actual worker import graph. The main entrypoint is
    imported only on D:/UCIE owner Windows or non-Windows synthetic CI;
    the GitHub temporary Windows checkout deliberately does NOT load the
    owner-only script or bypass its D:/UCIE guard.
  - Calls run_cycle() with a fixed SYNTHETIC collector and report inside a
    disposable system temp UCIE fixture. Writes a synthetic last_run.json,
    synthetic run_history.jsonl, and synthetic report ONLY in temp.
  - Parent checks explicit child return 0, JSON marker, synthetic receipt
    existence and worker return, bounded 15s timeout.
  - Prints FIRST_PARTY_SYNTHETIC_SUBPROCESS_EXIT_OBSERVED_NO_RELEASE.
  - Does not prove any real scheduled instance's Python shutdown.
- tests/test_ucie_public_miner_exit_probe_v01.py
  - Covers true subprocess exit, default non-execution, bad marker, timeout,
    nonzero exit, injected forged booleans and fixed -I command.
- scripts/ucie_public_miner_exit_probe_v01.ps1
  - Exact D:\UCIE root and explicit -RunSynthetic switch.

## Implemented real-hardware read-only TaskScheduler timeline

- src/ucie_miner/public_miner_exit_timeline_v01.py
  - Pure, bounded validation of TWO first-party public receipts and up to 16
    full TaskScheduler instance records (100, 200, 201, 102).
  - Exact task action must match fixed Python executable. Event GUID used
    internally for grouping but never included in output.
  - Reject missing, duplicated, shifted, malformed, non-UTC, foreign, or
    extra approval data. No inferred TaskScheduler GO.
  - Outputs two event-to-receipt matches, action result code, duration,
    seconds between receipt completion and action close.
- scripts/ucie_public_miner_exit_timeline_v01.ps1
  - Reads only exact UCIE task events, last two UCIE public run receipts,
    sends allowlisted fields to the pure analyzer, no writes or other tasks.
- tests/test_ucie_public_miner_exit_timeline_v01.py
  - 16 offline synthetic/static tests including nonzero, mismatched/duplicate
    events, untrusted status, missing receipts and task mutators.
- tests/test_ucie_public_miner_exit_timeline_owner_live_v01.py
  - Owner-only exact D:\UCIE single-file acceptance; CI outside owner root
    skips. Actual 2/2 receipt-to-instance matches; one action nonzero.

## Owner commands (read-only or explicit synthetic only)

Default synthetic preview (no child is executed):

    & 'D:\UCIE\scripts\ucie_public_miner_exit_probe_v01.ps1'

Explicit self-contained synthetic process exit test:

    & 'D:\UCIE\scripts\ucie_public_miner_exit_probe_v01.ps1' -RunSynthetic

Read-only exact task history and after-receipt action lag:

    & 'D:\UCIE\scripts\ucie_public_miner_exit_timeline_v01.ps1'

## Decision gates

1. First-party synthetic Python worker process exit: observed (exit 0).
2. Real failed scheduled task event 201 nonzero after receipt: observed.
3. Exact event instance-to-worker-receipt association: 2/2 observed.
4. Root cause (Python shutdown vs output flush vs delayed fsync vs OS):
   NOT PROVEN. Do not guess.
5. Schedule change, service restart, Task ExecutionTimeLimit increase:
   NOT AUTHORIZED and NOT PERFORMED.
6. The original failure incident must remain traceable after later success.
   Two new successful exact scheduled instances with zero 201 results are
   required before an owner can reconsider scheduler GO.

Note: The owner host contains preexisting locally modified tracked worker.py
and public_miner_cycle.py files. They are not overwritten by this work.
Do not infer unmodified GitHub main code exactly matches the local scheduled
worker until a separate source-pinned diff/review is completed.
