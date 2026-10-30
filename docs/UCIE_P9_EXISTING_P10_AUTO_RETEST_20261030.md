# UCIE P9 - Existing P10 automatic retest integration (2026-10-30)

## Actual behavior
The existing P10 **UCIE_FIRST_PARTY_EXPERIMENT** 15-minute leased worker still executes the original first-party parity trial. On its success it invokes UCIE P9 retest automatically. No new worker kind, Windows task, schedule, public source, approval or external project access.

- When P11 is disabled or no new improvement_review exists, it performs no retest and creates no P9 table.
- With a newly recorded P8 review, P9 reads P11 source/experience/improvement data using SQLite read-only mode and validates the existing first-party SHA256 receipt and results over workloads 128, 256 and 512.
- Exactly one new item per existing experiment worker invocation; it stores a bounded, immutable receipt in the existing **P10-only queue** database under table p9_retest_receipts. Duplicate executions leave prior receipts unchanged. If an original P11 receipt changes or disappears, fail closed.
- The P11 experience ledger, original public miner, scheduler, code, keys, rules and models are never modified by the P9 worker.
- All passing retests remain FIRST_PARTY_RETEST_PASS_MANUAL_REVIEW_ONLY. A regression is FIRST_PARTY_RETEST_REGRESSION_HOLD_NO_GO. No automatic code adoption, promotion, release or signature.
- The 65 historical experiences never become new P8 reviews or automatic P9 receipts.

## Test coverage
tests/test_ucie_p9_p10_auto_retest_integration.py covers first-party idle, new evidence, immutable SHA receipts, multiple P8 reviews queued one per experiment run, source tampering, side-effect forgery, cross-workload regression hold and unrelated worker isolation.

## Host truth and future gate
This PR changes only first-party GitHub sources/CI. **It does not update or activate anything on operating Windows D:/UCIE** and does not override the pinned P8 three-file synchronization that protects owner local changes. Do not claim that P9 is live on host from a merged PR or CI alone.

The natural next boundary is safe host delivery of the reviewed files without overwriting owner-local modifications, followed by a read-only live observation of new P8 evidence and one P9 receipt. No PowerShell user prompt is necessary during this GitHub development work. Real upstream fix verification and owner production adoption remain separate unpassed gates.
