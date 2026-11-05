# UCIE W12 owner incident differential — stop synthetic-test churn
Date: 2026-11-05 KST. PROJECT=UCIE ONLY. Production root cause UNKNOWN.

## W11 classification is not production repair
The user supplied a preview NOT_RUN receipt and then an explicitly executed
four-mode first-party synthetic PASS: clean exit0, injected fsync failure exit1,
injected stdout failure exit1, artificial post-stdout hold timed out.
These are correct laboratory results; they do not verify the operating task.

## NEW exact owner-host observations (read only)
- Original public unverified PR candidates 361:
  python/cpython=351 and PowerShell/PowerShell=10.
- Original recorded collector runs 492, latest finished 2026-11-05T06:37:21Z
  (15:37:21 KST), latest new public unverified PR candidates=2.
- Stage10 PR revisions 126; separate Stage12 review proposals 813.
  Ledger grains overlap and are NOT additive.
- TaskScheduler most recent 15:37 action ended with code 0, duration
  11.606 seconds and receipt-to-action closure 0.769 seconds.
- Previous 14:37 action had nonzero code 0x8007050B, duration
  600.017 seconds, receipt-to-action closure 591.169 seconds.
- Task ExecutionTimeLimit PT10M. Timeout is a strong correlation,
  not a proven causal attribution. The latest two task actions contain one
  bad instance; the two-new-clean scheduled-instance gate remains NO_GO.
- A separately attempted owner scheduler test was blocked by tool safety.
  No bypass was attempted; no PASS asserted from that blocked call.

## Three real public miner receipts compared
KST start | collect_elapsed_ms | report_elapsed_ms | cycle_elapsed_ms | new PR
13:37:10 | 9177 | 18 | 9196 | 0
14:37:10 | 8760 | 18 | 8779 | 0
15:37:10 | 11005 | 18 | 11024 | 2

All three statuses were COLLECTED_UNVERIFIED, verification_pass=0,
production_approved=false. Stage10, Stage12, Stage13, Stage16 and Stage17
receipt status codes were the same on all three runs. The problematic 14:37
public collection cycle finished in 8.779 seconds, so nearly the full 591s
delay occurred AFTER receipt completion, not in collection or review logic.

## Exact UCIE-only owner source pins, no source text disclosure
scripts/public_miner_cycle.py:
  owner Git blob 7a936f3208e4d8760066989e9a3992ec297d7a04
  GitHub main Git blob 9d53538dd97f29497020424d562f97dd917305ab
src/ucie_miner/worker.py:
  owner Git blob 3d2b6c5c54cf832155179f9fc8f4db536ae7505d
  GitHub main Git blob 7728e35ab1ca185849c444d5652160b67555815f

Both local files differ from the repository main; never overwrite them
or claim main source is identical to the running owner host.

Bounded local AST inspection (only those two UCIE files; no source emitted):
- Worker has _write_receipt, the single-instance lock context and a receipt
  return; it directly creates no Thread/ThreadPoolExecutor and directly
  registers no atexit callback in that file.
- Entrypoint invokes run_cycle, prints result and uses SystemExit;
  it directly registers no atexit callback in that file.
- Imported modules, interpreter shutdown, Windows task policy, OS state or
  external monitoring agents are NOT excluded by this narrow AST analysis.

## Prioritized next gate — no more generic synthetic phase labs
1. Keep the 14:37 failed and 15:37 successful instances as separate events.
2. Before any operating edit, source-pin both owner code files and review
   a narrowly scoped ONE-SHOT only trace for UCIE-PublicMiner-Hourly:
   receipt return -> OS lock release -> stdout flush -> atexit entry ->
   exact task Event201; timestamp safe scalar fields only.
3. A trace requires distinct owner authorization and must not query public
   GitHub, write operating SQLite, read unrelated paths or run the miner as
   a diagnostic shortcut. No new permanent telemetry, scheduled monitors,
   registry/service change or raw source dump.
4. Do NOT simply lengthen PT10M, reinstall/restart the task, modify operating
   code or promote any unverified rule while the real causal path is unknown.
5. Require TWO NEW fully event-bound successful scheduled actions before
   declaring scheduler GO. Later success does not delete failure evidence.

Official background:
https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-error-and-success-constants
https://docs.python.org/3/library/concurrent.futures.html

NO operating database writes. NO TaskScheduler mutations. NO actual miner
execution from this investigation. NO other projects accessed. NO training,
automated approval or package/release. This is evidence, not production PASS.
