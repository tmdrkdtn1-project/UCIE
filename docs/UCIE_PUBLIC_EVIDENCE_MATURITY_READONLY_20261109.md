# UCIE read-only public evidence maturity review V01 (2026-11-09)

Scope: UCIE-only, existing source-linked Stage10/opted-in Stage15/Stage12 metadata. No external fetch, writes, scheduler changes, trust promotion, rule signing, customer distribution or cross-project access.

## Why this follows PR #215

PR #215 restored 1,008 source-linked UNVERIFIED review revisions by aligning three consumers with the canonical 10,000-row boundary. A restored source-linked ledger is not evidence of a real reproduced fix, safe recipe, accurate version range or license clearance. The next release blocker is **evidence maturity**, not candidate volume.

## First bounded implementation

`src/ucie_miner/public_evidence_maturity_v01.py` reuses `prepare_verification_handoff` and `_checked_handoff` before deriving any data. Thus source SQLite remains opened only through existing `mode=ro` / `query_only=ON` readers with schema, source-identity and fingerprint checks. No new raw SQLite or network consumer is introduced.

Output is a closed, deterministic, JSON-serializable summary:
- source-linked **evidence revision** count, and distinct *public identity* count;
- counts per previously approved public repo, PR/fix-PR/git commit identity;
- multiple evidence revisions under the same public identity, **not** automatically labelled duplicate, false-positive or verified fix;
- number of existing non-executable Stage6 template *candidates*;
- explicit report-only gaps: per-revision license not attested **here**, affected version not validated **here**, independent regression not performed **here**;
- bounded manual review targets without raw source code, logs or untrusted text.

An absent, pending or source-mismatched handoff cannot turn into a maturity score or display source targets. All approval, signature, external reproduction, customer release and automatic promotion flags remain false. The output is NOT a confidence score or clearance verdict; unrelated evidence systems may carry separately approved facts and are not overwritten by this read-only report.

## Usage: explicit owner-only audit, never scheduled

From the existing UCIE-only Python environment:

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.public_evidence_maturity_v01 --root 'D:\UCIE' --limit 8
```

Synthetic regression on branch:

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_public_evidence_maturity_v01.py' -v
```

## Acceptance and non-acceptance

- Code + synthetic CI can establish bounded field calculation and fail-closed behavior, but cannot validate actual owner 1,008-row figures.
- Real owner report must remain pending until the exact new files are safely deployed with SHA-aware backup, without overwriting 15 pre-existing dirty tracked files.
- This report does not fix source license gaps or independently reproduce any upstream behavior.
- `ONLINE_RELEASE_AUTHORIZED=false`, `CUSTOMER_DISTRIBUTION_AUTHORIZED=false`, candidate automatic promotion disabled.

Next meaningful bundle: record actual owner report; investigate top review identities with approved source/version/rights documents and UCIE-authored isolated positive/negative reproduction. Distinguish **metadata completeness**, **independent correctness**, and **release permission**, and only then propose a human review gate.

Product owner: https://github.com/tmdrkdtn1-project/UCIE/issues/199


## Owner 1,008-revision receipt and upstream public-source review (2026-11-09)

Evidence types must remain separate:
- **OWNER_HOST_READONLY_REPORT**: owner submitted output from the UCIE-only CLI after local deployment. This is not an independently executed third-party audit.
- **UPSTREAM_PR_METADATA_OBSERVED**: this author checked public PR records and changed-file metadata in only the already approved GitHub repositories; no upstream source code was executed.
- **RELEASE_NOTE_OBSERVED**: release-note reference is not independent regression or universal version applicability.
- **INDEPENDENT_BEHAVIOR_REPRODUCTION / PER_REVISION_RIGHTS / OWNER_RELEASE_SIGNOFF**: NOT PERFORMED by this review.

### Exact local read-only inventory

| Field | Owner-observed value |
| --- | ---: |
| Stage10 / optional Stage15 → Stage12 source-linked evidence revisions | 1,008 |
| Distinct public PR/commit identities | 1,000 |
| Public identities with multiple revisions | 6 |
| Additional revisions over distinct identities | 8 |
| Existing Stage6 non-executable template candidate revisions | 4 |
| FIX_PR_METADATA / PR_METADATA | 873 / 135 |
| per-revision rights, affected-version and independent regression evidence attested **by this CLI** | 0 / 0 / 0 |
| approved rules / network requests / persistent writes / customer release | 0 / 0 / 0 / false |

Exact source revision counts: python/cpython=571, PowerShell/PowerShell=256, actions/runner-images=123, modelcontextprotocol/python-sdk=57, git/git=1. Counts are evidence revisions, not distinct bugs, approved fixes, unique skills or actual version compatibility. A second revision against the same public PR may be a valid independent source observation; **do not label it duplicated or delete it based only on the grouping**.

### Bounded review: six multiply observed approved-repository PRs

| Original public PR | Owner-linked revisions | Observed merged SHA | Source-observed change category | Next gate |
| --- | ---: | --- | --- | --- |
| [PowerShell #28243](https://github.com/PowerShell/PowerShell/pull/28243) | 4 | `6ca9a44dc945c802fc2f59897fafe0c598a9c894` | dependency pin Microsoft.PowerShell.PSResourceGet 1.3.0-preview2 → 1.3.0-rc1 | review why 4 separate evidence hashes were observed; retain as versioned maintenance technique, not claimed bug fix |
| [PowerShell #28211](https://github.com/PowerShell/PowerShell/pull/28211) | 2 | `0aaf78b30bd7c8ab947643a9152ac28ad7020e79` | Store en-US product description + MSIX publishing stage metadata handling | release-pipeline correctness review, no prevention-rule promotion |
| [PowerShell #28287](https://github.com/PowerShell/PowerShell/pull/28287) | 2 | `ba85e625ac6bb662817785b090c3b69cdfa198cc` | dependency pin PSResourceGet 1.3.0-rc1 → 1.3.0-rc2 | version pin/supersession metadata; do not infer previous revision was faulty |
| [MCP Python SDK #3696](https://github.com/modelcontextprotocol/python-sdk/pull/3696) | 2 | `754254c08fe1c3eda18b69da3d336106fe8d72d6` | unknown prompt / missing required prompt argument errors use JSON-RPC INVALID_PARAMS -32602 | first independent version-pinned protocol behavior validation candidate |
| [CPython #158910](https://github.com/python/cpython/pull/158910) | 2 | `05d80ccfe77a781667d1b9e25247c193559cd7cc` | free-threaded bytes/bytearray join and concurrent list mutation crash avoidance | disposable, resource-bounded free-threaded build/reproduction only; never stress owner production Python |
| [CPython #159289](https://github.com/python/cpython/pull/159289) | 2 | `25883627946b7cbcf7286acfe2a2019382375325` | recursion-limit checks in deeply nested lazy-import chain to avoid native stack overflow | isolated subprocess C-stack regression after version/build confirmation |

These six PRs explain exactly 4+2+2+2+2+2=14 source evidence revisions attached to 6 public identities, hence the observed 8 extra revisions. The public PR merge identities match the owner-submitted revision examples. No independent test result or per-revision license decision was inferred from the merged state.

**Technical classification matters for all four pillars:** a dependency pin or Store publishing improvement can be a reusable **development/maintenance** principle even when it is not an error-prevention rule. Keep it in a maintenance/release-engine review queue rather than a generic discard bucket or a falsely verified bug-fix catalog.

### Version and release scope — narrowly attested facts

- [PowerShell v7.7.0-rc.1 release](https://github.com/PowerShell/PowerShell/releases/tag/v7.7.0-rc.1) was published 2026-10-29 and explicitly mentions existing-template fixes [#28042](https://github.com/PowerShell/PowerShell/pull/28042) (fuzzy Get-Command duplicate results) and [#28087](https://github.com/PowerShell/PowerShell/pull/28087) (dot-prefixed Resolve-Path -Relative output). This is **release-note evidence**, not proof of working behavior on all operating systems or stable versions. Its build/packaging notes also mention #28243 and #28211. Do not infer #28287 availability from a separate package dependency bump.
- [MCP Python SDK v2.3.0 release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.3.0) was published 2026-10-02; #3696 merged 2026-10-13. Therefore SDK v2.3.0's publication is **not** evidence that the later PR fix shipped in that tag. Exact first compatible release remains unverified.
- **CPython v3.15.0 source check (not behavioral reproduction):** upstream annotated tag `v3.15.0` was stamped 2026-10-09T11:16:41Z and resolves to commit `d220409a13b77de7a6c30abe16ea90db01528edc`. GitHub compare reports both exact PR merge commits #158910 and #159289 *diverged* relative to that tag (neither exact merge commit is its ancestor). More concretely, [tagged join.h](https://github.com/python/cpython/blob/v3.15.0/Objects/stringlib/join.h) blob `deebfeadc0f4fd87e4ddefc68418b6cd32063eae` lacks the PR's `bytes_join_lock_held` and `Py_BEGIN_CRITICAL_SECTION_SEQUENCE_FAST` protection visible in current main, while [tagged lazyimportobject.c](https://github.com/python/cpython/blob/v3.15.0/Objects/lazyimportobject.c) blob `bb35ddcdae1755ee7c7327256b31008a62f7f00d` lacks the PR's additional `_Py_EnterRecursiveCall` protection in `lazy_import_path` and `lazy_import_replay_from` visible in main. **The specific PR changes are not present in that tagged code.** This is versioned code evidence only; it does **not** demonstrate a live crash or rule out all alternative mitigations/backports, and is not an instruction to stress-test an owner machine.
- The presence of a repository license is not a per-PR rights clearance. License, attribution, redistribution limits, source ownership and any necessary third-party permissions remain an explicit independent gate.

### Prioritized next **development** bundle, not duplicate collection

1. **P1-A / MCP #3696:** design UCIE-authored positive and negative `prompts/get` cases for valid prompt, unknown prompt, missing required argument, and actual prompt-execution exception. Distinguish `-32602` input errors from internal failures. Pin a specific, legally reviewed SDK artifact and protocol revision; execute only with separate approval in a disposable sandbox. Do not silently install from an unapproved package index or declare upstream tests independent.
2. **P1-B / CPython #158910:** review the free-threaded runtime/build and reproduction method without running a crash/race stress test on the owner PC. Independent before/after native tests require isolated builds, timeouts, memory limits and crash-safe evidence receipts.
3. **P1-C / CPython #159289:** inspect supported lazy-import versions; design a depth-bounded subprocess negative/positive test proving a `RecursionError` rather than a segfault under a pinned supported build, again isolated from owner production processes.
4. **P2 / reuse existing Stage6 candidates:** #28042, #28087, #153462 and #159014 are already four recognized non-executable templates; do not create duplicate rule IDs or imply approval. Version/rights/independent regression receipts still need separate decisions.
5. **P3 / positive maintenance knowledge:** #28243, #28287 and #28211 are version-pinning and release-pipeline cases. Keep them for useful development-engine/SkillBook comparison only after independently assessing applicability and benefits.

**Acceptance for the next bundle:** one selected behavior has a pinned source and exact supported/rejected version(s), authorized/independently run positive+negative first-party cases, baseline-vs-fixed results, checked license/attribution, and a reviewer decision with limitations. Until then: `SOURCE_LINKED_UNVERIFIED`, `AUTO_PROMOTION=false`, `SIGNED_RELEASE=false`, `CUSTOMER_RELEASE=false`.

No changes to public miner's task/database, localhost server process, Cloudflare, source allowlist, signing, approved Rulepacks, private projects or existing modified owner files are authorized by this review. The 09:00 daily-report hold remains in effect.
