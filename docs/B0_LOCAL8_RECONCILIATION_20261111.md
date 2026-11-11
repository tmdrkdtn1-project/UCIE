# UCIE B0: safe reconciliation of eight genuinely divergent owner files

Status: **SELECTED_CHANGES_STAGED_FOR_REVIEW / NO AUTOMATIC MERGE / NO LOCAL REPLACEMENT** (2026-11-11).

Scope is exclusively UCIE source inside `D:/UCIE` and this approved public GitHub repository. The owner-local working tree contains eight substantive divergences from the current `main` branch, beyond other tracked files whose normalized Git blobs already match. No local `reset`, `clean`, `checkout`, `pull`, scheduled-task changes, operating SQLite edits, or other-project access occurred.

The files were compared by UTF-8 source from connected `ucie_admin_read_text` and exact GitHub `main` blobs. CRLF/LF alone is not treated as a functional change. Local edits are owner-authored, not implicitly approved for public merge; only the two bounded improvements below were reimplemented on `main` in this review branch.

| Owner-local divergent file | Reconciliation outcome |
|---|---|
| `docs/ROADMAP.md` | **Keep current `main`**: canonical four-pillar product charter, private designated-customer full-release NO-GO gates and master roadmap supersede the older Stage 1–4 local note. Never overwrite current main charter with an obsolete owner-local document. |
| `scripts/public_miner_cycle.py` | **Integrate three Stage17 fields only**: `stage17_quality_status`, `stage17_quality_candidate_count`, `stage17_quality_candidate_delta`, and only through existing Stage10 staged/partial outcome. Existing opt-in, single-instance lock, schedule cadence, source list and approval guards unchanged. |
| `src/ucie_miner/__main__.py` | **Keep current `main`**: local deltas are CLI wording, error wording and equivalent unique-key JSON handling; not a basis to replace newer main behavior. |
| `src/ucie_miner/core.py` | **Keep current `main`**: local renames, comments, redundant `per_source` bookkeeping and collection-status naming do not justify overwriting current main. Preserve its approved public GET budgets and row rotation. |
| `src/ucie_miner/public_fix_evidence.py` | **Keep current `main`**: difference is only a public candidate rejection comment. |
| `src/ucie_miner/schedule_policy.py` | **Keep current `main`**: failure and jitter policy code identical; comments differ. |
| `src/ucie_miner/worker.py` | **Integrate sanitized failure provenance only**: static failure phase, allowlisted public source/operation and bounded HTTP status; no raw exception text. **Do NOT import local stricter partial count <= 2/source**: current `main` intentionally supports up to five PR attempts per approved source (the hourly normal path still uses two). Preserve current main collector validation and Stage17 count bounds. |
| `tests/test_ucie_stage15_fix_evidence.py` | **Keep current `main`**: main uses fixed UTC subclass for reproducible rotated public PR fixture tests, while local uses a mock/wraps clock; existing 12/12 Stage15 baseline and 11/11 audited-snapshot tests do not warrant replacing main. |

## Source-pinned local snapshot (2026-11-11)

Local SHA-256 values are evidence for later owner reconciliation, **not** automatic write leases or proof that the sources may be distributed.

| File | Owner-local SHA-256 | GitHub main Git blob SHA-1 |
|---|---|---|
| `docs/ROADMAP.md` | `30d43222e295e21189b69788f7390eb23fbaefc1e57aa313c58aaab04f22b3b4` | `0e7453ee914cfded621fe37770a4d7a95750afdb` |
| `scripts/public_miner_cycle.py` | `a8e547119388795ea15e8316d587ad8c9e19aabecb97a444377361f482da4e98` | `9d53538dd97f29497020424d562f97dd917305ab` |
| `src/ucie_miner/__main__.py` | `d64d46359972908ddbfb651d683c5bdd7718c3a62efb19cb7f9f6ce4b66bf915` | `1adbcdb64241442f018637ec453a2c6f835da0f2` |
| `src/ucie_miner/core.py` | `5bba1cbd7a8ff43392089ab39a07ac8089f574acd1cbec3b3fc070cd02e65c04` | `9d825276411ebd7d3ebd7f090fabec262b2b79b9` |
| `src/ucie_miner/public_fix_evidence.py` | `8dde59664c892122a9eb2fae05bc900d1178cf8d686508b8fbeebb1be2bfc30c` | `2694bdb63086a054dd7faa9a9d05490e38cb78dd` |
| `src/ucie_miner/schedule_policy.py` | `e5ccfa7ef6d875877883c6e9e753f1bb3508e501e29fc517464d208ede46d04b` | `00fb172c6928d012d1ac9f7f00de5e6a8c34bcb0` |
| `src/ucie_miner/worker.py` | `4caf985afe3c0d1abbce02ea2fd60b118b4e50cad0e53dc9c9b27015712083fe` | `7728e35ab1ca185849c444d5652160b67555815f` |
| `tests/test_ucie_stage15_fix_evidence.py` | `27e2a637a54d384fa702a0933e39586933017964549fa8a0558cd62745f7dbbf` | `61f52b1789405d0951729564fddda9f473e4532c` |

## Required verification / release boundaries

- New `tests/test_ucie_b0_local8_selected_integration_v01.py` covers six first-party synthetic checks: Stage17 field round-trip; counter/status rejection; bounded collector HTTP error receipt; untrusted source/operation suppression; report-writer phase; actual hourly `main()` AST-isolated Stage17 forwarding.
- Before proposing merge, verify this branch on clean Windows/Linux CI and Python versions supported by the workflow, plus existing worker and schedule tests. Host `D:/UCIE` running code remains the owner-local version and is not automatically changed by an approved PR.
- This change does not activate auto-promote, alter a live Windows Scheduled Task, re-run collection, change the Virtual Library or UI, or authorize a full customer release.
- B0 `read_text` connected return was recovered in both approved scopes (101-byte repo example and 3,227-byte MCP code example), but the one-time C40 supervisor attribution incident remains separately open in issue #235. Customer full-product gate remains NO-GO (issue #199).
