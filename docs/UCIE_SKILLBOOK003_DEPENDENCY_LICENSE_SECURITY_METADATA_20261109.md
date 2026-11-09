# UCIE SkillBook 003 — locked installed dependency metadata & rights/security gate

Date: 2026-11-09. UCIE-only roadmap P2. This report and its tests do not change any customer UI, operating source miner, database, scheduled task, auto-promotion, or approved knowledge catalog.

## Why this exists

PR #225 independently executed the *actual*, installed, official MCP Python SDK `Client` ↔ `MCPServer` in memory on Linux, comparing exact Git commits `2118f14f8a19bc158d8a1cf90af58d85d187f849` (v2.3.0) and `754254c08fe1c3eda18b69da3d336106fe8d72d6` (PR #3696). Four scenarios in each of two protocol modes passed at both source points. Real v2.3.0 error codes 0/-32603 became -32602 for unknown prompt / missing required argument in the patched build `2.3.1.dev9+754254c`. This development-build identifier does **not** demonstrate a published 2.3.1 release.

Before publishing any derived SkillBook content, a dependency rights/supply-chain review is necessary. **A successful build and a matching `uv.lock` do not establish licensing permission, vulnerability freedom, provenance of all downloaded files or approval.**

## Exact evidence identities

| Source item | Before `v2.3.0` | Patched PR merge |
|---|---|---|
| Official source owner | `modelcontextprotocol/python-sdk` | Same |
| Exact commit | `2118f14f8a19bc158d8a1cf90af58d85d187f849` | `754254c08fe1c3eda18b69da3d336106fe8d72d6` |
| Upstream original `uv.lock` Git blob | `73fcc3331a93fc9442d8c2b2f85312d7cb389fbd` | `fd2dcb85f9923798334ea6259522ae4ae84185f8` |
| Upstream LICENSE reference | https://github.com/modelcontextprotocol/python-sdk/blob/v2.3.0/LICENSE | https://github.com/modelcontextprotocol/python-sdk/blob/754254c08fe1c3eda18b69da3d336106fe8d72d6/LICENSE |
| Full SDK in-memory execution evidence | https://github.com/tmdrkdtn1-project/UCIE/actions/runs/42585148478 | Same |

Latest observed official GitHub release list on 2026-11-09 remains `v2.3.0` (published 2026-10-02). The fixed PR was merged 2026-10-13; **first officially published fixed release NOT_VERIFIED**. The upstream `SECURITY.md` describes supported release lines and private vulnerability reporting, but does not establish that every locked dependency is vulnerability-free.

## New P2 implementation

- First-party read-only auditor: `scripts/ucie_mcp_installed_dependency_metadata_v01.py`.
- Offline fail-closed tests: `tests/test_ucie_mcp_installed_dependency_metadata_v01.py`.
- Disposable execution occurs **only after** PR #225's source identity / `uv.lock` checks and actual installed SDK integration test, in that same GitHub-hosted Linux workflow.
- The auditor rechecks the whole `uv.lock` original Git blob and parses it using stdlib `tomllib`. It inventories only distributions **actually installed in each pinned SDK virtual environment**. The lock includes development/multi-platform entries not necessarily installed, which must not be counted as deployed dependencies.
- Each installed distribution's normalized name/version is matched to the correct stage's upstream lock; only the two exact workspace packages (`mcp`, `mcp-types`) and exact-version lock packages declared from the official PyPI registry are accepted. Unexpected Git or external-registry dependencies **fail closed**.
- Observe bounded, non-executable installed distribution `METADATA`: `License-Expression` (when present), legacy License/classifier markers, number of license-file claims, and metadata SHA-256. Marker presence is an **observation**, never a legal finding.
- Exact manifest of installed distribution names/versions and SHA-256 hashes is emitted as a temporary CI log receipt; raw third-party sources and original package files are not copied into this repo or uploaded as artifacts.
- No third-party module import, code execution, network or file mutation by this auditor; its mandatory CI runner checks deny Windows/owner-host execution and non-isolated environments.

## Explicit NO_GO checks

| Domain | Status until independent work |
|---|---|
| Original lock Git hash | Check per stage; CI evidence required |
| Installed dependency name/version corresponding to that stage's lock | Check per stage; CI evidence required |
| Installed package license *metadata marker* | Inspect per installed package; a marker is not approval |
| Full dependency LICENSE/NOTICE contents and copyright attribution | **NOT_REVIEWED** |
| Every dependency vulnerability advisory as-of version & platform | **NOT_SCANNED** |
| Build backend artifacts and resolver `uv==0.9.5` wheel SHA-256 | **NOT_INDEPENDENTLY_VERIFIED** |
| SBOM coverage of uninstalled platform/optional/dev dependencies | **NOT_AUDITED** |
| Legal/rights signoff and security review | **NOT_APPROVED** |
| SkillBook 003 catalog publication, signing, export and customer release | **NO_GO** |

**Security-advisory warning:** No vulnerability findings are claimed. A read-only metadata audit is not a negative CVE scan. Private security advisories are inaccessible, so "zero known vulnerabilities" cannot be concluded even after a public scan.

## Required remaining review before P2 complete

1. The per-stage CI receipts must be inspected, and uncertain/missing license metadata must be independently examined against the corresponding public package distributor's declared LICENSE/NOTICE, for the exact resolved version and platform. Do not mine or redistribute unapproved source repositories.
2. Query permitted official security advisories for each installed package/version against applicable environments; record references, publication date, affected/fixed version and unresolved advisories. If an authoritative advisory source cannot be reached or a package is missing, keep the result `NOT_VERIFIED`.
3. Independently pin hashes and check rights for tool/build backend artifacts plus any runtime redistributions; compare an isolated platform-specific SBOM to actual install. Do not make up PASS when this cannot be completed.
4. Confirm first released fixed SDK version only from an official post-PR release publication; never equate a generated `2.3.1.dev9+... ` distribution identifier with a published version.
5. Subject SkillBook 003 to human accuracy/rights/security review. No automatic activation or replacement of existing approved SkillBooks.

## V4 design freeze

Keep `/local` home and `/local/evolution` improvement suggestions visually and semantically unchanged. This PR has no changes in `src/ucie_miner/local_v1_app_v01.py` or `src/ucie_miner/local_v1_design_v04.py`, and does not restart the owner server. Customer release stays NO_GO.
