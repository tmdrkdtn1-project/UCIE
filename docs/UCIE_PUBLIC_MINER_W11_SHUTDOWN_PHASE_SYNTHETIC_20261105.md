# UCIE W11 | Post-receipt Python shutdown phases | 2026-11-05

PROJECT=UCIE ONLY. STATUS=FIRST_PARTY_SYNTHETIC_QA_ONLY_NO_RELEASE.
No private source / unrelated project access. No TaskScheduler change or real
collector launch, no operating DB writes, public HTTP or model training.

## Evidence inherited from owner reports and W10

The owner's 2026-11-05T06:15:25Z public-only report:
- legacy PR candidates=359 (python/cpython=349, PowerShell/PowerShell=10)
- legacy run receipts=491, Stage10 PR revisions=126, Stage12 review=811
- TaskScheduler last result=267014 / 0x00041306 (terminated), 1/2 valid
  event-to-receipt scheduled instances. Scheduler health is NO_GO.

Independent read-only W10 exact-task instance-to-receipt correlation:

| Action | Runtime | Receipt-to-action-finish | 201 result |
| --- | ---: | ---: | --- |
| Prior action | 9.754s | 0.893s | 0x00000000 |
| Failed action | 600.017s | 591.169s | 0x8007050B |

Task ExecutionTimeLimit=PT10M. This correlation suggests timeout, but
does not establish why a real Python action remained alive after its receipt.

Pinned public UCIE GitHub main blobs at W11 source review:
- scripts/public_miner_cycle.py 9d53538dd97f29497020424d562f97dd917305ab
- src/ucie_miner/worker.py 7728e35ab1ca185849c444d5652160b67555815f

Public main worker.run_cycle invokes a receipt writer with fsync, returns
inside a single-instance lock context, and the entrypoint prints JSON and
returns a status to SystemExit. A durable receipt does not certify clean
TaskScheduler action completion.

IMPORTANT: The owner checkout had pre-existing tracked local modifications
to both files above; W11 does not read their full contents, overwrite them,
or pretend they match public main. Production root-cause remains UNKNOWN.

## New W11 functionality (five first-party-only files)

- src/ucie_miner/public_miner_shutdown_phase_w11.py
- tests/test_ucie_public_miner_shutdown_phase_w11.py
- scripts/ucie_public_miner_shutdown_phase_w11.ps1
- tests/test_ucie_public_miner_shutdown_phase_owner_w11.py
- docs/UCIE_PUBLIC_MINER_W11_SHUTDOWN_PHASE_SYNTHETIC_20261105.md

The W11 Python module creates a child with sys.executable -I -B. It imports
only the UCIE worker and uses run_cycle with a fixed first-party fake collector,
fake report, enforce_schedule=False and disposable temp UCIE directory. Its
phase labels are emitted to captured stderr and never stored permanently.
No actual public miner main(), external API, C40, Stage10 or scheduler runs.

| Synthetic mode | Expected source-linked observations |
| --- | --- |
| clean | fsync return, receipt return, worker return, temp clean, stdout flush, main end, atexit, exit 0 |
| fsync_error | synthetic fsync OSError, no receipt/worker return, nonzero exit |
| stdout_error | synthetic OSError after worker return, no stdout flush, nonzero exit |
| post_stdout_hold | synthetic temp already cleaned and stdout flushed, artificial late hold bounded by parent timeout; no atexit |

All modes use only first-party synthetic inputs. The timeout is a TEST
injection (2 seconds parent limit), not a measured production timeout.
Phase names/sequence, stdout marker, child code and provenance are validated.
Invalid modes, forged/duplicated input, unknown stdout, bool exit codes,
nonzero/missing cases and unbounded evidence fail closed.

Local owner test receipts:
- first-party isolated phase regression: 19/19 PASS
- exact D:\UCIE Windows PowerShell preview + explicit synthetic acceptance:
  2/2 PASS
- synthetic clean code0, fsync error code1, stdout stage error code1,
  artificial after-stdout hold timed out, 4/4 expected classes observed
- temporary fixture writes only; operating DB writes=0; scheduled tasks
  changed=0; public network requests=0; other project access=false

## Manual owner commands

Preview without spawning synthetic child:

    & 'D:\UCIE\scripts\ucie_public_miner_shutdown_phase_w11.ps1'

Explicit synthetic child opt-in only:

    & 'D:\UCIE\scripts\ucie_public_miner_shutdown_phase_w11.ps1' -RunSynthetic

The second command is not a production collector execution.
Never treat synthetic exit SUCCESS as real hourly TaskScheduler recovery.

## Release and next owner approval gate

PR stays DRAFT/UNMERGED. Next step after owner approval is a source-pinned,
bounded one-shot **real UCIE-only** process-exit checkpoint plan that can
independently distinguish receipt return, lock release, stdout flush, atexit
and TaskScheduler action 201. Source identity must be reconciled first.
Do not add always-on telemetry, reconfigure or start the hourly task,
extend PT10M, kill an unrelated process, or hide the failed instance.
Require two NEW exact task-bound successful instances with exit code zero
before changing scheduler GO status.
