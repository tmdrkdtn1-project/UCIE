# UCIE MCP Python SDK — real installed Client ↔ MCPServer integration gate (2026-11-09)

## Scope and decision

Roadmap P1-A evidence maturity, following UCIE PR #223 (synthetic wire checks) and #224 (four SHA-pinned upstream method paths). This next gate **installs the actual SDK** from the approved `modelcontextprotocol/python-sdk` repository at two immutable commits in disposable GitHub-hosted Ubuntu, using each revision's **own original `uv.lock`**. It tests two in-memory protocol modes across one normal request and three error/control requests, with the actual SDK `Client`, `MCPServer` and `MCPError` classes.

This is a **one-shot research CI experiment**, not a release. Neither UCIE customer UI nor any owner-host runtime is affected.

## Exact pinned upstream inputs

| Item | Baseline | Patched commit |
|---|---|---|
| Official upstream Git URL | `https://github.com/modelcontextprotocol/python-sdk.git` | Same |
| Git commit | `2118f14f8a19bc158d8a1cf90af58d85d187f849` (tag `v2.3.0`) | `754254c08fe1c3eda18b69da3d336106fe8d72d6` (merged PR #3696) |
| `uv.lock` Git blob | `73fcc3331a93fc9442d8c2b2f85312d7cb389fbd` | `fd2dcb85f9923798334ea6259522ae4ae84185f8` |
| `pyproject.toml` Git blob | `8148505417b4ff5ed543dfdff39c9bf4ff7d4f2b` | `6d7626d79b4a78c66e5dd1837b28530e677a0d34` |
| `mcp-types` project manifest blob | `4f3500c2913b8e183b3cd9a6ae15776bd79ea049` | `b5a980802196d70dfa373a5b646b353b2a243aa0` |
| `PromptManager` original source | `01a0823bf74c72c2197b846bf94a5f0ff00dfcea` | `6ad5dfb8c654c2f965c5e25424a588a771e3c858` |
| `Prompt.render` original source | `a13b72f1aa0eb4f15dddc42b4442a4246479cf6b` | `32372a527a6e9b7d352b5371d524288342fd99b2` |
| `Client` source | `8c7d372431219c1e60b6e14fd94e80b58efc10f2` | `099dcbb874fe1b49137bc2fe5667b0c81338d33b` |

All Git object hashes are checked before dependencies are installed, each checkout is detached from its own commit, and the trial uses sparse checkout for `src/mcp`, `src/mcp-types`, root manifests, and example workspace `pyproject.toml` manifests only. Not a bulk crawl or source republication.

The disposable CI uses GitHub `actions/checkout@v7` and `actions/setup-python@v7`, Python 3.13, pinned `uv==0.9.5` tool from package index, and `uv sync --locked --no-default-groups --no-editable`. Third-party dependency artifacts are obtained according to the **upstream, commit-specific lock**; those are runtime dependencies **not UCIE mining evidence sources**. Some dependency wheels and build backends are from a public package registry, not an approved evidence repository; treat this as an **isolated, untrusted software supply-chain experiment**. Locking version/hashes does not equal independent license, vulnerability, package integrity or threat-model clearance. The pinned `uv` resolver itself currently has an exact version pin, not a separately verified SHA-256 wheel receipt. Do not promote this step to full supply-chain approval.

## Executed scenarios / expected gate

One in-memory actual `Client(MCPServer)` session per stage × protocol mode:
- Legacy handshake (`legacy`, associated with 2025-11-25) and DirectDispatcher (`2026-07-28`) mode. These are SDK modes, not two complete public-network transports.
- Registered `greet(name="Ada")` returns one text message matching `Hello, Ada`.
- Unregistered `unknown_prompt`: before fix **not** `-32602`, after fix **exactly** `MCPError.code=-32602`.
- Registered `greet` without required name: before fix **not** `-32602`, after fix **exactly** `-32602`.
- Registered `explode` raises a first-party `RuntimeError`, which must not be misreported as input parameter error `-32602`.

Script `scripts/ucie_mcp_installed_sdk_client_server_gate_v01.py` is a hard-gated one-shot runner. It imports the full pinned installed SDK from each private disposable virtual environment. It rejects Windows and non-isolated/non-GitHub CI use, checks the exact Git commit asserted by the workflow and the Python executable/import roots, bounds each API call with a timeout, records per-stage observations and emits a receipt with no original prompt payload, user files or sensitive logs. A failure prevents PASS for that stage.

Workflow `.github/workflows/ucie-mcp-installed-sdk-integration-qa.yml` has read-only repository permissions, no checkout credentials, no production secrets or services, 14-minute timeout, temporary source/dependency folders removed on all exits, and no persistent artifacts. No external sockets used by the in-memory test after installation; dependency and official source setup require public network access. It does not invoke code from unrelated projects or their sources.

**Successful CI evidence must include two stage receipts, each 8 real API calls (4 scenarios × 2 SDK modes), plus the exact source and lock SHA preflight. The results are not to be guessed from successful generic CI.**

## Qualification / remaining gates

- **Still not tested:** actual streamable HTTP and stdio transport, complete upstream tests, other Python versions, real user workload, prompt injection, complete vulnerability and dependency license review, first fixed tagged distributed version, customer/online deployment.
- **Still required:** obtain any third-party package/builder hashes and license attestations needed for distribution rights; confirm whether a released version exists after PR #3696; independent security review, owner approval, signing, no cross-repository data leakage.
- Existing `v2.3.0` tag predates the fix. Official releases list at last verification (2026-11-09) shows no published post-PR release; `first_fixed_release=NOT_VERIFIED`.
- SkillBook 003 remains `DRAFT / NOT_APPROVED`. Provenance may link the executed integration receipt only if this exact-head CI completes successfully; until then no “real SDK integration PASS” claim.
- **V4 UI design freeze:** no code modifications under `src/ucie_miner/local_v1_app_v01.py`, `src/ucie_miner/local_v1_design_v04.py` or anything rendering `/local` and `/local/evolution`. No operating database, Windows scheduler, public miner, Cloudflare, connectivity, dashboard, auto rule promotion, or customer release changes.

If the upstream lock install fails or a protocol mode has a different API surface, record the exact failure as **NO_GO**, keep the previous method-path proof, and make only a scoped follow-up patch. Do not substitute synthetic fixtures or disable a failing case to obtain a green badge.
