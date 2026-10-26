# Sixth UCIE candidate — MCP empty metadata legacy peer compatibility

**Status: independently developed candidate only; not part of signed Serial 4 or Serial 5.**

## Approved upstream and exact pinned source

- Official approved repository: [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)
- Merged fix: [PR #3628](https://github.com/modelcontextprotocol/python-sdk/pull/3628), 2026-10-02 UTC
- Before fix: commit `cdf7d332d7f417ed7199fea303a17426d4dc4d07`, file `src/mcp/shared/jsonrpc_dispatcher.py`, Git blob `5c09126a17d9a45e02b5662964a04b5cd63b1ba8`
- After fix: commit `0b2fd3ea60efb16b349e8c887cf91bf2f9f773fc`, same file Git blob `ab333912d2857c12eb42dd5adfa59df4dceefa24`
- The fix removes unconditional `out_params["_meta"] = out_meta`; it emits non-empty metadata only and omits an empty `params` member. The upstream PR says some legacy servers reject the empty metadata envelope. It does **not** prove that all MCP servers reject it.
- Upstream Python SDK version containing this fix was **not independently pinned or verified**.

## New detector

`src/ucie_miner/static_mcp_empty_meta.py`: `MCP_EMPTY_META_LEGACY_COMPAT`

Pure Python AST inspection of **explicitly provided, approved public code or first-party synthetic snippets**. It searches for outbound `JSONRPCRequest(jsonrpc="2.0", ..., params=<paramsvar>)` where a possibly empty metadata dictionary is assigned unconditionally to `<paramsvar>["_meta"]`. An explicit `if <metavar>:` guard suppresses the pattern. Local function boundaries avoid mistaking an unrelated nested constructor for the send path.

**Limits:** Only a bounded syntactic heuristic, not dataflow proof; source can shadow `JSONRPCRequest`, reassign variables, or sanitize metadata elsewhere. Findings always require manual review. A zero finding result is not a safety PASS.

### One-pass bounded offline test

`tests/test_ucie_static_mcp_empty_meta.py` covers the approved upstream before/after shape, explicit truthiness guard, unrelated/nested nonmatches, controlled standard-library JSON examples, inert stdin execution and fail-closed bounds. No upstream code execution, external endpoints, real MCP server or user data.

### Manual candidate inspection

From a clean UCIE checkout with local `src` on Python path:

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
Get-Content -Raw -Encoding utf8 '<approved-public-python-source-file>' |
  D:\UCIE\.venv\Scripts\python.exe -B -m ucie_miner.static_mcp_empty_meta
```

The file must be a previously approved public source; do not feed private work or other project material.

### Hard hold — no implied release permission

Serial 4's four rules and the newly signed Serial 5 fifth-rule addendum remain immutable and unchanged. This PR **does not** auto-promote, approve, sign, reissue, deploy or add the sixth candidate to an existing Rulepack. A future owner decision must be tied to the sixth rule, its uncertainty and a separate release gate. No extra CI runs or mock signing rounds are required for this candidate work beyond the one applicable exact-head CI matrix.
