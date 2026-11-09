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

## Observed installed distribution evidence (first CI receipt, 2026-11-09)

Read-only ephemeral source of this observation: https://github.com/tmdrkdtn1-project/UCIE/actions/runs/42587044200 . The CI installed the approved official SDK at both immutable commits, rechecked both Git blob hashes of `uv.lock` and compared *every installed distribution* against its own stage's lock before producing two actual `UCIE_MCP_INSTALLED_DEPENDENCY_METADATA_AUDIT_V01` JSON receipts.

| Measured category | SDK v2.3.0 (`before`) | PR merge build (`after`) |
|---|---:|---:|
| Entries in full multi-platform + dev lock (not deployed counts) | 134 | 138 |
| Installed packages in exact disposable SDK venv | **30** | **30** |
| With bounded `License-Expression` metadata marker | 25 | 25 |
| With only legacy `License` field marker | 4 | 4 |
| With only a license classifier marker | 1 | 1 |
| Packages outside this stage's locked name/version/source | **0 in successful inventory** | **0 in successful inventory** |
| Actual vulnerability advisory scan executed by metadata auditor | NO | NO |
| Redistribution / customer approval | NO | NO |

**Additional legal review priorities**: `annotated-types==0.7.0` (classifier-only), `h11==0.16.0` (legacy field), `pycparser==2.23` (legacy field), and `mcp` / `mcp-types` at the stage-specific installed versions (legacy field). These flags concern **metadata format**, not proof of license noncompliance. The 25 SPDX declarations are also **not** permission or legal attestation. Per-package original license text, notices and actual wheel/SDist/builder artifacts must be examined before any redistribution decision.

### Additional official SDK advisory observation (not a 30-package scan)

The approved official repository's [public security advisory index](https://github.com/modelcontextprotocol/python-sdk/security/advisories) exposed the following ten named published advisories at review time: [GHSA-rwrf-2pqf-9j8j](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-rwrf-2pqf-9j8j), [GHSA-84m7-p3x7-pcfv](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-84m7-p3x7-pcfv), [GHSA-w4fh-qvv9-3v23](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-w4fh-qvv9-3v23), [GHSA-5h93-6whr-6q8j](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-5h93-6whr-6q8j), [GHSA-hvrp-rf83-w775](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-hvrp-rf83-w775), [GHSA-qx49-fqc8-xw99](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-qx49-fqc8-xw99), [GHSA-fmmv-w9g8-j3gc](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-fmmv-w9g8-j3gc), [GHSA-vj7q-gjh5-988w](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-vj7q-gjh5-988w), [GHSA-jpw9-pfvf-9f58](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-jpw9-pfvf-9f58), [GHSA-9h52-p55h-vw2f](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-9h52-p55h-vw2f).

Among reviewed published version ranges, the 2.x affected ranges shown end below 2.2.0 (or below 2.1.0); others apply only to 1.x. That **does not establish zero vulnerabilities in v2.3.0**: the public listing may be incomplete, private advisories are unavailable, later disclosures may arrive, and the 29 other installed distributions were not examined for advisories. For instance the bearer-token advisory `GHSA-w4fh-qvv9-3v23` explicitly notes that upgrading alone does not turn on the added `validate_token_resource` safety setting. No HTTP/OAuth service configuration was tested in our in-memory prompt experiment.

**Therefore final P2 SECURITY = NOT_VERIFIED and LICENSE_REDISTRIBUTION = NOT_APPROVED.** There is no automatic SkillBook promotion or customer release.
