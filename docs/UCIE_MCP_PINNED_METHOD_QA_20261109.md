# UCIE MCP SDK pinned-source method QA — bounded disposable execution (2026-11-09)

This is the **next roadmap QA gate**, extending PR #223 without modifying the V4 customer-facing home/improvement pages or the UCIE owner-host service.

## Exact source identities

Source owner: `modelcontextprotocol/python-sdk` (approved independent public upstream). No source from any other project or repository.

| Snapshot | Immutable upstream commit | Expected original Git blob SHA-1 |
|---|---|---|
| `PromptManager`, before | `2118f14f8a19bc158d8a1cf90af58d85d187f849` (SDK v2.3.0) | `01a0823bf74c72c2197b846bf94a5f0ff00dfcea` |
| `Prompt.render`, before | same | `a13b72f1aa0eb4f15dddc42b4442a4246479cf6b` |
| `PromptManager`, after | `754254c08fe1c3eda18b69da3d336106fe8d72d6` (PR #3696 merged) | `6ad5dfb8c654c2f965c5e25424a588a771e3c858` |
| `Prompt.render`, after | same | `32372a527a6e9b7d352b5371d524288342fd99b2` |

**Source URLs:** https://github.com/modelcontextprotocol/python-sdk/pull/3696 and https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.3.0 . Official public specification: https://modelcontextprotocol.io/specification/2025-11-25/server/prompts#error-handling, specifying `-32602` for unknown names and missing required arguments. Last observed published SDK release `v2.3.0` precedes merged PR, so **first released fixed version is NOT_VERIFIED**.

## What is *actually* executed

On a disposable GitHub-hosted Linux runner, `.github/workflows/ucie-mcp-pinned-source-method-qa.yml` fetches **exactly four short files** at the immutable commits from `raw.githubusercontent.com/modelcontextprotocol/python-sdk`. There are no new repositories, PyPI installs, network tools inside the probe, packages, Git credential persistence or source-code publishing artifacts. The files are deleted at the end.

`scripts/ucie_mcp_pinned_method_probe_v01.py` verifies the full original files' **Git blob SHA-1**, checks size and AST shape, extracts only:
- the unchanged full **`PromptManager.render_prompt` method path**, running it with a UCIE-authored fake prompt registry;
- the unchanged **required-arguments validation guard** at the beginning of `Prompt.render`, returning a first-party sentinel before any third-party rendering/import logic.

Runs 4 cases per branch: missing prompt, missing required argument, valid argument *guard*, and first-party simulated prompt-execution exception. The expected pre-fix unknown/missing exception is `ValueError` and the expected merged-source exception is `MCPError(INVALID_PARAMS=-32602)`. Exception class `MCPError` itself is a minimal first-party stub because no upstream SDK dependencies are loaded. This procedure executes **the selected actual pinned upstream method AST**, but does NOT execute the original SDK package, JSON-RPC client/server transport, all message rendering or real prompt-function code.

Test fails closed for hash mismatch, unexpected class/function AST, malformed source, symlinks, missing snapshots, abnormal result, and unauthorized invocation. CLI requires `python -I -S`, `UCIE_DISPOSABLE_PINNED_QA=1` and Linux POSIX; it cannot silently run on the Windows owner host. The GitHub workflow has an 8-minute timeout, read-only permissions and no third-party code installation.

## Gate distinctions and what remains

| Evidence class | Decision |
|---|---|
| GitHub exact upstream source and immutable blobs | PINNED |
| First-party JSON-RPC synthetic scanner (PR #223) | TESTED_FIRST_PARTY, not an upstream claim |
| Selected upstream Python method AST before/after isolated on disposable CI | **8/8 method paths observed in one disposable CI**; full SDK integration not performed |
| Full installed, pinned SDK `Client` / `MCPServer` `prompts/get` integration for both protocol versions | **NOT_EXECUTED** |
| First fixed distributed SDK release and supported version ranges | **NOT_VERIFIED** |
| SDK license source | Repo `LICENSE` for v2.3.0 is MIT with attribution, but per-contribution/dependency/legal review remains pending |
| Independent security/rights/consumer verification, approver, signed rules, customer export | **NO_GO** |

Do not treat the targeted method probe as full SDK independent QA or apply a fix to any external project. Only after independently authorized, supply-chain-pinned installed SDK before/after integration runs may the full SDK behavior gate be considered. Until then SkillBook 003 remains an unpublished draft.

## Operating and V4 stability

No changes to `/local`, `/local/evolution`, home colors, typography, customer copy, V4 app source, public miner scheduler, database, Windows tasks, cloud tunnel, active server, private materials, other projects, source allowlist, auto-promotion, export or release. The prior owner local dirty UCIE working tree is preserved. The held 09:00 report remains held.

## Observed pinned-method runtime receipt — recorded after first CI run

The GitHub-hosted disposable source-method workflow completed successfully: https://github.com/tmdrkdtn1-project/UCIE/actions/runs/42582727640 . The recorded JSON receipt had `status=PINNED_UPSTREAM_METHOD_PATHS_OBSERVED`, `method_paths_executed=8`, both official exact commits and four Git blob identities matched, before unknown/missing → `ValueError` and after unknown/missing → `MCPError(code=-32602)`. The selected valid argument guards passed and first-party execution-error controls propagated `RuntimeError` on both sources. The receipt explicitly records `sdk_imported=false`, `entire_prompt_renderer_tested=false`, `sdk_transports_tested=false`, `independent_sdk_integration_verified=false`, `rights_and_release_approved=false`. All fetched source snapshots were discarded from the temporary runner. Exact final-head CI status must be checked separately if this document changes.
