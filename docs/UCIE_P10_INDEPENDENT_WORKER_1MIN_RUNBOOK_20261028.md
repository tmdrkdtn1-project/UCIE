# UCIE P10 — blocked A → PENDING, independent B/C progress (2026-10-28)

## Owner-defined acceptance goal

"자동 스케줄이 막히면 그 작업은 펜딩으로 두고 다음 작업 진행에 지장 없게", 1-minute internal dispatch, protected separate hourly existing public miner, no universal runtime stall. **Minute tick is a check, NOT a hard deadline for a job.**

## Implementation bundle

- Existing `src/ucie_miner/pending_queue.py` stays intact. The new `runtime_pipeline.py` provides a short process-level locked tick (never waits for jobs), five **fixed-type** recurring jobs, at most 3 concurrent worker supervisors, and fixed 1/5/5/15/60-minute processing intervals. Each event is bounded/read-only and does **not** invoke an external GitHub GET.
- Per-job worker supervisors spawn exactly one allowlisted child Python `-B -m ucie_miner.runtime_pipeline --execute --kind ...` in its **own process**. A supervisor waits at most 180 seconds, sends a heartbeat every 15 seconds to renew the lease while legitimate work proceeds, kills its own child on overrun, and writes `BLOCKED` → `PENDING` with retry delay. Failed spawn/blocked dependency affects **only that job**; another 2 slots continue. Other jobs never wait for A.
- Actual callable handlers only use **already existing UCIE code**: W04 public metadata library read; W06 official document metadata read; first-party synthetic incremental computation; first-party standalone metadata lookup QA; P9 product **read-only** report preview. These are not automatic external technology training or model/policy rule approval. The existing **UCIE-PublicMiner-Hourly** still collects approved public PRs hourly and is independent. This P10 does not change its operating database.
- Recurrence uses only five **stable dedupe keys**, not one new row per minute. After a successful job's interval elapses, mark the same row PENDING and store **per-kind last successful time + total successful completion count** in a constant-size `p10_completed` table. Permanent failure remains REVIEW_REQUIRED. Claims and state transitions use SQLite short transactions. No unbounded queue/history growth from scheduling.
- Existing queue token fencing rejects stale workers. A missing callback or HTTP failure in a handler leads to a sanitized retry reason; no raw untrusted exception text is persisted.
- The `scripts/install_internal_minute_task.ps1` defaults to **PREVIEW ONLY**, refuses non-UCIE root and existing same-name task, uses the existing local Python 3.15 virtualenv/current user Interactive/Limited, sets once+repetition PT1M, ignores overlapping dispatcher invocations, and registers only `UCIE-Internal-Minute` with **explicit `-Install`**. Existing `UCIE-PublicMiner-Hourly` trigger/worker unchanged. Since bridge does not support OS scheduler actions, code existence or test PASS is **NOT** proof of an installed 1-minute task.

## Cadence (independent of old hourly miner)

| Kind | Proposed interval | Scope |
|---|---:|---|
| UCIE_LIBRARY_INDEX_CHECK | 1 minute | existing official evidence index read |
| PUBLIC_METADATA_REVIEW | 5 minutes | existing reviewed public evidence read |
| UCIE_QA_REVIEW | 5 minutes | UCIE-authored portable lookup exact parity |
| UCIE_FIRST_PARTY_EXPERIMENT | 15 minutes | small synthetic algorithm only, never persist experience |
| UCIE_REPORT_PREPARATION | 60 minutes | P9 product read-only preview, not a delivered scheduled email |
| Existing UCIE-PublicMiner-Hourly | 60 minutes | separate current production public source miner, untouched |

**5-minute external public collection is not enabled by this bundle.** A shorter authorized live GET cadence requires API quota/backoff testing plus explicit operating schedule approval. Existing signed Rulepack, W05 unverified cues, model weights, real production adoption and automatic learning/promotion untouched.

## Independent functional safety tests

- `tests/test_ucie_runtime_pipeline.py`: offline initialization, A blocked→PENDING while B/C succeed, A heartbeat/timeout fencing via existing queue test, failure to spawn A but launch B/C, <=3 active caps, stable 5-row recurrence plus constant-size per-kind counters, direct first-party handler checks, **actual Python child worker subprocesses** in copied UCIE-only synthetic tree, true short dispatcher returning before child results, operating miner/P8 source preservation, CLI initialization opt-in.
- Existing `tests/test_ucie_pending_queue.py`: A blocked/B complete, duplicate claim prevention, concurrency, stale lease fencing, retry budget and OS-specific SQLite release checks.
- Require exact-head Windows+Ubuntu/Python 3.13+3.15 CI 4/4 and actual owner host 1-file test before any real scheduled task switch. CI PASS ≠ owner operating 1-minute task PASS.

## UCIE Windows commands (scope-limited)

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
$py = 'D:\UCIE\.venv\Scripts\python.exe'

# No operating queue changes; safe test uses synthetic UCIE-only temp paths
& $py -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_runtime_pipeline.py' -v

# Read-only preview of a future 1-min task (no install, no task changes)
& 'D:\UCIE\scripts\install_internal_minute_task.ps1'

# Only after separately authorizing live activation: explicit queue init and
# one-minute task creation, leaving old hourly miner intact:
# & 'D:\UCIE\scripts\install_internal_minute_task.ps1' -Install

# If initialized: single short tick, only 3 independent read-only workers
# & $py -B -m ucie_miner.runtime_pipeline --ucie-root 'D:\UCIE' --tick

# Existing queue status (does not create the queue)
& $py -B -m ucie_miner.pending_queue --ucie-root 'D:\UCIE'
```

## Remaining V1 boundaries

An installed Windows task must be accepted through consecutive real owner-host ticks and worker receipts. Actual external API schedule acceleration, automated user-approved experience promotion, package license/legal/independent QA/owner release are separate incomplete product gates. No claim of V1 release, no silent task installation, no unauthorized project access or cross-project learning.
