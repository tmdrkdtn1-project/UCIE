# UCIE SPEED V1.2 L1 minimal safe-read patch — 2026-10-25

Project: UCIE exclusively. Branch: `feat/ucie-speed-v12-safe-read-lanes-20261025` from `main`.
State: CODE IMPLEMENTED (Draft review branch), not active host rollout.

## Input and ownership

Owner supplied a neutral ZIP/MASTER SPEED V1.2. It is a review reference, not executable code or authority. The official current UCIE operating policy wins over performance goals. Project separation is absolute.

## Actual source bottleneck

`scripts/public_miner_cycle.py` enters `ucie_miner.worker.run_cycle`. The worker has an existing OS byte-range single-instance lock, schedule policy, SQLite ledger, and atomic `last_run.json` plus append-only `run_history.jsonl` receipt. `ucie_miner.core.mine_once` serially fetches list metadata from exactly `python/cpython` and `PowerShell/PowerShell`, then for eligible *unseen* PRs fetches dependent PR files and optionally verifies provenance before writing into one SQLite transaction. No real per-stage latency or shared GitHub quota observations have been supplied. The two independent list-GETs provide a bounded candidate for overlapping I/O, **not** permission to increase external throughput.

## Patch scope

1. `src/ucie_miner/core.py`: add the strictly typed optional `read_workers` parameter default **1**. A value of 2 is accepted only for the exact existing two public sources tuple. With 2, `ThreadPoolExecutor(max_workers=2)` fetches **list URLs only**, within the same outer SQLite transaction and with source order preserved for all dependent PR file requests, deduplication, provenance, classification and DB inserts. No new upstream route, no retry, no credential. On any failure, no run receipt is committed. Default production call site is unchanged and therefore remains **serial**. No command-line flag, env variable or scheduler option enables 2.
2. `src/ucie_miner/worker.py`: add bounded monotonic `collection_elapsed_ms`, `report_elapsed_ms`, `cycle_elapsed_ms` to the pre-existing per-run ACK only. No new log/DB/worker/scheduler. Existing failure status, crash-safe OS lock, time scheduling, source allowlist and sanitized error types remain authoritative.
3. `tests/test_ucie_speed_v12_safe_reads.py`: isolated synthetic two-source GET behavior, actual barrier-enforced cross-thread temporal overlap, identical database rows and result compared to serial, no replay/retry on failed unknown/429, no duplicate existing candidates, invalid worker/source rejection, receipt bounded metrics.

## Security and activation

- Existing `UCIE-PublicMiner-Hourly` reservation and logon identity unchanged. Existing C40 Admin Bridge and `UCIE_UnattendedHost` protected root unchanged. No automatic Rulepack promotion.
- No unrelated project or private repository access; all test inputs are synthetic. No project-wide shared rate limiter, scheduler, account, WAL, credentials, cross-project controller.
- **No real API concurrency increase:** owner has not supplied a verified shared GitHub API rate limit and allocated budget. The default `read_workers=1` must remain in all scheduled and normal operators. The optional two-thread mode is for network-free acceptance tests only until a separately approved nonoperational host pilot.
- No `Retry-After` auto retry introduced. Future 429 retry classification must honor source idempotency, effective SDK attempts, billing/authorization/UNKNOWN state and quota evidence; quota failures are never retried automatically.
- CI must run the existing full offline suite plus the added tests. Reusing previous test evidence is allowed only with matching source SHA + Python/OS/environment and unchanged test dependencies.
- A code PR is NOT a host rollout, live 2x throughput test, budget approval, or a signed release.

## Baseline and measurement

Previously executed source-neutral simulation (not this PR) with 8 sample batches each: synthetic ~0.5829 seconds serial vs ~0.3084 seconds with two threads, about 1.89x (below 2x target). This is **not** UCIE live API/Windows throughput. The new test asserts overlap and quality, not an arbitrary 2x performance threshold. Real baseline p50/p95, external 429, CPU/RAM, cost and SDK retries: SOURCE_MISSING. Small synthetic-N p95 does not establish service SLA.

## Next gates

1. Draft PR offline CI Windows/Ubuntu Python3.13/3.15 PASS and independent code review.
2. No need to change or rerun completed old miner cycles. Do not deploy directly on owner's PC without reviewing the patch; existing local branch checkout is not this feature branch.
3. On an independently approved **new reversible non-production** UCIE task, record elapsed timings, GET count, 429, total SDK attempts, quota, CPU/RAM, quality, and ACK in serial and test with explicit 2-worker allowance only after account-level external rate budget is verified.
4. Real `PERF_2X_PASS` requires comparable throughput >=2x with stable p95/quality/errors/cost/security and verifiable run receipts, not synthetic arithmetic.

Gate: `L1_SOURCE_PATCH_PENDING_CI / OPERATING_READ_WORKERS_1 / LIVE_HOST_PILOT_NOT_RUN / PERF_2X_NOT_VERIFIED`.
