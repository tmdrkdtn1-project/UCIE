# UCIE P3-A — W04 real owner public-evidence search performance baseline

Date 2026-11-09. **First measurement gate only. No claimed optimization or V4 UI changes.**

## Why this follows P2

SkillBook 003's actual MCP SDK in-memory behavior has been independently reproduced. Its installed package dependency metadata was audited against the exact upstream lock, with legal rights, dependency advisories and customer release still fail-closed. The next roadmap stage begins with **real W04 read-only backend search latency**, not changes to the accepted V4 customer UI.

## Existing search contract (no changes)

- Original public-only source-linked search: `src/ucie_miner/library_search.py`, `search_existing_public_library()` and `search_linked_public_candidates()`.
- Original Stage12 lineage verification: `src/ucie_miner/verification_handoff.py`, `prepare_verification_handoff()` which reads only existing UCIE SQLite `mode=ro` and `PRAGMA query_only=ON` after rederiving Stage10/15 source records.
- Search emits `READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO`, `export_allowed=false`, `human_approved=false`, `network_requests=0`, `operating_database_writes=0`.
- Query patterns fixed at `python`, `git`, `api`. Limit 10. No user input or other project files. A count is the number of public **candidate revisions**, NOT approved/verified rules or SkillBooks.

## Exactly what is measured

The source-only first-party script `scripts/ucie_w04_owner_public_readonly_perf_v01.py` and host-guarded test `tests/test_ucie_w04_owner_readonly_perf_baseline_v01.py` run only on real `D:/UCIE` Windows owner host. No CI test attempts to read a fake operating DB. Local runner tests the pure shape/approval safety contracts with synthetic fixtures everywhere else.

For each of three fixed queries:
1. Warm one in-memory search against the validated handoff.
2. Measure **12 in-memory search/filter** calls against the *already prepared*, source-linked handoff.
3. Measure **4 complete read-only calls** that also rederive Stage10/15 and verify Stage12 SQLite linkage.
4. Report median/min/max in milliseconds, query matching revision count, returned count, and total input revisions, plus timestamp. Compare case paths **only on equal linked source counts and output totals**; otherwise fail closed.

These are single owner-host workload observations, NOT frontend latency, throughput capacity, speedup, p95, request concurrency, browser visual acceptance, external release approval or production SLA. Do not claim a high speed ratio from only 4 complete calls. The quality of the backend must be investigated before any index/cache changes, especially preserving the runtime cost of immutable provenance checks.

## Safe execution and interpretation

Only the existing UCIE admin `ucie_admin_test_one_file(filename='test_ucie_w04_owner_readonly_perf_baseline_v01.py', approved=true)` may exercise it. The test reports `UCIE_W04_READONLY_OWNER_LATENCY={...}` on stdout when eligible, and is skipped in ordinary Windows CI without `D:/UCIE` and on Linux. The proof is an actual owner-host test receipt, not an offline CI assertion. If Stage12 source linkage is incomplete, do **not** bypass validation for speed; report `HANDOFF_NOT_FULLY_LINKED` and measure no successful baseline.

No writes: script does not execute SQL, copy databases, write logs, create indexes, register tasks or access source code outside UCIE. All existing reader operations use the original read-only SQL code. No Cloudflare changes or network.

## Next P3 decisions (do not implement without measurement)

- If full end-to-end median dominates in-memory filtering, identify which source verification step costs time before considering short-lived per-request in-memory reuse with output-equivalence and freshness gates.
- If in-memory filtering dominates, consider changes to candidate materialization or bounded index use, **only after an A/B comparison** with exact outputs and explicit source/version/approval invariants.
- If data changes during timing, no improvement conclusion is valid; repeat after source linkage is stable.
- Any candidate optimization must pass exact-head Windows/Ubuntu Py3.13/3.15 CI and owner baseline comparison; accept no performance gain claim on synthetic-only data.

**V04 freeze:** `src/ucie_miner/local_v1_app_v01.py`, `src/ucie_miner/local_v1_design_v04.py`, and particularly `/local` and `/local/evolution` must remain untouched. No customer/online release, TaskScheduler, DB, public miner, cloud or automatic approval changes.

## Actual owner-host measured observation (2026-11-09)

The UCIE-only owner bridge ran `tests/test_ucie_w04_owner_readonly_perf_baseline_v01.py` on the actual Windows `D:/UCIE`, exit 0, **7/7 tests PASS in 3.262s**, captured UTC `2026-11-09T08:52:20.813315+00:00`. Test run duration is **not** the backend latency metric. All three query patterns used the existing source-linked read-only W04 candidate API.

- Total source-linked **public candidate revisions**: 1,016. This is **not** an approved rules count and may change when the public miner records new evidence.
- Query-specific matching revisions: Python 628, Git 124, API 92. Top 10 returned for each.
- Source report asserted `operating_database_writes_by_measurer=0`, `external_network_requests_by_measurer=0`, `source_approval_changed=false`, `customer_release_authorized=false`, `ui_modified=false`. This does not prove another concurrent UCIE collector made no changes.

| Search query | Revisions matching | Preloaded handoff filter, 12 samples median (ms) | Complete source/ledger read to search, 4 samples median (ms) |
|---|---:|---:|---:|
| `python` | 628 | **21.227** (20.603–30.877) | **121.832** (121.213–125.526) |
| `git` | 124 | **20.136** (19.727–22.131) | **127.127** (125.012–133.486) |
| `api` | 92 | **22.210** (20.012–40.523) | **160.358** (146.840–181.327) |

**Meaning:** Across these three real queries, the complete request path is slower than the in-memory search/filter segment. The **difference of median values must not be presented as an isolated measured lineage-verification cost**: full execution also creates/reconstructs its public handoff, repeats normalization and can read evolving ledgers, and the samples are not statistically paired. What is justified is to **profile the full Stage10/12/15 handoff/normalization path next before changing search indexing**, while refusing to skip immutable source linkage, case-folded matching, revision grouping, and nonapproval checks.

**Limits:** single owner-host, one timestamp, small sample counts, no p95, no concurrency, no browser-render timing, no RSS/tracemalloc peak. No performance gain has been implemented or claimed. Existing W04 P8 cost policy and V04 customer interface remain unchanged.

Proof lives in owner `ucie_admin_test_one_file` execution receipt and GitHub exact-head CI for the first-party harness. GitHub cannot reproduce the owner's public ledger without access to D:/UCIE, and its synthetic tests must not be misreported as real owner latency.
