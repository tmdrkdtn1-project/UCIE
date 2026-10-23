# UCIE Library — read-only MCP search handoff and public skill feed

## What this adds

UCIE now has first-party, PUBLIC_ONLY Python handlers ready for an **existing**
UCIE MCP server to import. No additional MCP server, ChatGPT plugin,
Cloudflare tunnel, scheduler, remote project reader or signing stack is created.

- `ucie_miner.public_library_mcp_adapter.search_ucie_public_library_for_mcp`
  accepts the currently exposed `search_ucie_evidence(query, category, tag,
  top)` argument names and searches only the preexisting UCIE Stage 10 and
  Stage 13 public metadata indexes.
- `ucie_miner.public_library_mcp_adapter.preview_public_skill_feed`
  exposes five first-party UCIE *technical review profiles*, along with
  bounded PUBLIC_ONLY source references. This is a read-only *research feed*,
  not an installable ChatGPT Skill, Rulepack, or model update.
- `python -m ucie_miner preview-library-skill-feed` displays the same
  deterministic five-domain research catalog offline.

Both functions return **UNVERIFIED / NO_GO** metadata. A content SHA-256 is
only a comparison fingerprint, not an attested or signed version release.

## Integration into the **existing** UCIE Private Readonly MCP runtime

There is deliberately no new local service. The existing UCIE tool currently
returns `status=UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY` and a `results`
list. **Preserve that live tool response and its authentication and legacy
library search.** Add a separate, explicitly unverified key rather than
replacing the existing handler's response.

The trusted UCIE runtime is maintained outside this GitHub repo. Only after
the runtime owner reviews the exact installed handler body, an additive
integration is appropriate:

```python
from pathlib import Path
from ucie_miner.public_library_mcp_adapter import (
    extend_existing_ucie_mcp_wire_response,
)

UCIE_ROOT = Path(r"D:\UCIE")

# In the *existing* search_ucie_evidence handler, after its current
# authorization/legacy search logic (not as a new top-level MCP handler):
#
# existing_response = <the current handler's normal response dict>
# return extend_existing_ucie_mcp_wire_response(
#     UCIE_ROOT, existing_response, query=query,
#     category=category, tag=tag, top=top)
```

The function returns a **new** dictionary containing every old field
unchanged plus `ucie_public_research_index`. A malformed/foreign legacy
response is rejected rather than being treated as UCIE evidence. A fixed
taxonomy query may produce an empty public research result; this does not
remove or alter the old Library results.

**Do not blind-edit the runtime MCP server**: inspect its current handler
first to identify its output shape, authorization logic and import path. The
runtime executable at `D:\UCIE_DATA\.venv_mcp\Scripts\python.exe` needs
access to the reviewed UCIE source under `D:\UCIE\src` for the import, but
only through the runtime's approved UCIE-only package/path setup. A GitHub
commit by itself does not change this environment.

### Single-use local integration guard (never automatic)

The repository includes an opt-in UCIE-only source patcher:
`scripts/prepare_ucie_mcp_library_link.py`. It uses AST inspection to
identify the existing `search_ucie_evidence` function in the exact file
`D:\UCIE_DATA\library_app\private_lib\mcp_stdio_server.py`. It verifies
the existing public-only response marker and rejects multiple return
paths, unknown signatures, or repeat attempts. It never inspects another
project, reads credentials, modifies plugin registration or restarts a tunnel.

Run only on the authorized UCIE Windows host after the reviewed PR source
is present at `D:\UCIE\src`. Missing adapter code fails closed.

One non-mutating preflight:

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B 'D:\UCIE\scripts\prepare_ucie_mcp_library_link.py'
```

A result of `READY_FOR_ONE_TIME_UCIE_MCP_HANDLER_LINK` confirms
structure and import/syntax preflight only, not live deployment.

After independent owner approval to change the running UCIE MCP file,
an opt-in atomic patch is available:

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B 'D:\UCIE\scripts\prepare_ucie_mcp_library_link.py' --apply --approval APPROVE_UCIE_EXISTING_MCP_LIBRARY_HANDLER_ONCE
```

The script inserts a local import for the UCIE-only module and wraps
the original handler return value via `extend_existing_ucie_mcp_wire_response`,
which accepts existing JSON text or dict outputs while preserving legacy
`status` and `results`. It writes a SHA-named backup of the old MCP server
and atomically replaces only that one file after syntax checking. The
host owner must inspect and approve any separate service restart; this
script does not perform one.

If the installed handler structure differs, the preflight reports a
FAIL_CLOSED without modifying the server. Do not blindly retry, remove
checks or scan unrelated source files; inspect only this UCIE handler.

Do not restart the tunnel or change the MCP tool registry as part of this
source-only PR. Once the authorized local handler modification is actually
deployed, one fresh live `search_ucie_evidence` call must preserve
`status` and `results` and additionally return
`ucie_public_research_index.schema=UCIE_LIBRARY_MCP_PUBLIC_SEARCH_CONTRACT_V1`.
Until that is observed, live integration remains **NOT DEPLOYED**.

### Query contract

- Scope only: Python, PowerShell, Git, MCP/API, GitHub Actions Runner,
  and the bounded approved public technical tag taxonomy. Query words are
  used for fixed taxonomy matching only. No semantic/raw text corpus search.
- Conflicting categories, ambiguous domains, malformed inputs, suspicious
  free-text prompts and unsupported domains produce an empty NO_GO result
  or explicit validation error. Caller-supplied raw query text is never
  persisted, transmitted, echoed in a response, or inserted into SQL.
- No live HTTP requests, subprocesses, dynamic imports, code execution,
  project access or private data reads.
- Reference results contain only allowlisted public URLs, pinned upstream
  SHA, evidence fingerprints, first-party safe-call guidance, and explicit
  unverified status. No upstream patches or unsafe commands.
- The feed has deterministic `content_sha256`. It must **not** be
  interpreted as a cryptographic signature or as a signed, approved Skill.

## One-shot safe operator preview

```powershell
Set-Location D:\UCIE
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner preview-library-skill-feed --references-per-domain 3
```

No schedule is registered, no recipient package is sent, and no existing
UCIE database is modified by the preview.

## What still blocks actual periodic skill distribution

1. Genuine, independently checked skill-level version, license, security
   and regression evidence is needed. Today all fresh mined leads are
   candidate-only and the exportable skill count is zero.
2. The separately managed existing MCP runtime must deliberately call the
   new adapter, and an authorized test must verify the new live tool response.
3. A later explicit owner-approved, signed PUBLIC_ONLY package and a
   recipient-side opt-in pull mechanism are required before any deployment.
   Cross-project telemetry, private context transfer and automatic
   installation remain forbidden.

**Development state: adapter and public research feed only; existing live
MCP plugin NOT modified and production distribution NO_GO.**
