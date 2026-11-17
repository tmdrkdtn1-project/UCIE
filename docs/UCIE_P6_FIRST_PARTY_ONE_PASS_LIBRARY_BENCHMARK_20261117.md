# UCIE P6 actual first-party search algorithm change and before/after QA

Date: 2026-11-17 KST. PROJECT_ID=UCIE ONLY. No owner local source changes, external public miner GET, operating SQLite writes, task rearm, rule promotion or customer export.

## Source identities, not reused static gates

- Immutable before-source: GitHub UCIE repository `638665d7ff7f7c4d14ac689af85018ad30923b63:src/ucie_miner/library_exact_index.py`; canonical Git blob `73baf4dac3bc07484a70e6c6854d5ac6937afbb7`.
- Optimization applied only to `src/ucie_miner/library_exact_index.py`. Existing P3 pagination, W04 default substring route and Stage10-12/15 provenance/approval gates are unchanged.
- Baseline is **actual UCIE first-party code** from immutable Git object, never public upstream code, customer or other project files. The code is hash checked and run only inside independent GitHub CI Python process alongside candidate; source not written to owner's Windows machine.

## Real algorithm delta

BEFORE: Normalize each validated record into an intermediate `(key, item)` catalog. For indexed multiqueries make a second full pass to build the index. For linear sparse queries retain all item dictionaries, then scan and sort matches after normalization.

AFTER: Calculate the original bounded strategy selection before normalizing, run the SAME strict `_checked_handoff` and `build_library_entry` on **every** source-linked record including nonmatches. For multiqueries, append validated items straight into the in-memory index during the one normalization pass; for linear sparse queries only materialize items with exact requested keys while still validating all other entries. Sort each stored bucket once; generate the SAME original JSON fields, pagination, ordering, negative status and approval restrictions. Add only four additive diagnostics: `one_pass_source_normalization`, `separate_intermediate_record_catalog_created`, `validated_source_rows`, `materialized_result_records`.

Original published cost fields (`linear_scan_comparisons_for_same_queries`, `index_build_plus_lookup_operations` etc.) remain a **legacy selection score**, not newly measured elapsed time or actual physical operations. Do not reinterpret them as a measured speedup. New P6 independent median time and peak memory are reported separately.

## Acceptance and benchmark method

1. Verify the actual old UCIE Git tree/path/blob SHA before importing only the first-party historical module into independent CI. Never fetch or execute upstream public PR code.
2. Compare complete before/after JSON (except four additional diagnostic fields) on 27/128/2048 record scenarios, one/multiple/repeated exact keys, missing keys and pagination offsets; verify no change in catalog permissions or indexes.
3. Negative checks: corrupt a **nonmatching** metadata record and assert both original and candidate reject; forge approval and assert both reject; incomplete review ledger remains NO-GO. No shortcut can bypass source validation.
4. Measure 3000 synthetic linked UCIE candidates, both sparse one-key linear and repeated multiquery indexed workloads. Warm up both variants, alternate execution order, take five median wall-clock `perf_counter_ns` samples per variant; separately use `tracemalloc` per-call peak bytes. Print explicit per-run JSON receipt `UCIE_P6_FIRST_PARTY_MEASURED=`. Assert exact output equivalence. Report observed time/memory for each OS/Python, not universal speed or memory guarantees. Do not use timing noise alone for PASS or approval.
5. Require exact HEAD Windows/Ubuntu Python 3.13/3.15 4/4 CI success and all new test cases OK. Historical W09 Git SHA remains unchanged. Owner-host source SHA differences must block automatic overwrite.

## GO/NO-GO boundary

Successful first-party synthetic equivalence/measurement means only **P6 self-owned algorithm candidate tested in CI**. It does not certify actual upstream code benefit, all real-life source-ledger perf, capacity at untested sizes, independent human QA, customer signed original Rulepack, actual prior deployment/restore artifact, legal license clearance, private full-product release, P11 HTTP403 recovery, or an approved change in the owner's 230-entry dirty Windows worktree.

NEXT after measured evidence: compare real existing UCIE source-linked read-only catalog **only when owner host sync/read access is explicitly safe and source-hash leased**, then UX + private-customer full product gates. P11 job6 REVIEW_REQUIRED5/5 and PublicMiner 403 remain HOLD.

STATUS=P6_FIRST_PARTY_GIT_BASELINE_COMPARISON_PENDING_EXACT_HEAD_CI__OWNER_HOST_NO_CHANGE__CUSTOMER_V1_NO_GO

## Independent standalone Python diagnostic

After the approved UCIE checkout is separately synchronized, the same baseline/candidate measurement can also run in an **independent isolated Python process** using:

```shell
python -I -B scripts/p6_library_one_pass_benchmark.py --rows 3000 --repeats 5
```

Only first-party UCIE `src` and `tests` paths are added by the bounded script; it uses the exact historical Git object, synthetic in-memory linked evidence and standard-library median/tracemalloc. It does not inspect any owner operating SQLite or project file. The CLI prints JSON to stdout and never publishes/saves measurement receipts automatically. Separate CI tests invoke this command with rows=256/repeats=3, plus invalid rows=6001 fail-close. This test is only available after test/scripts source synchronization, which has NOT happened on owner's D:/UCIE.
