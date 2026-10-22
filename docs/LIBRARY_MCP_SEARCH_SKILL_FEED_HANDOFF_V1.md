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

There is deliberately no new local service. An operator maintaining the
existing UCIE-owned MCP runtime can, after reviewing and deploying this code
into the **same trusted UCIE environment**, route that service's existing
`search_ucie_evidence` handler to:

```python
from pathlib import Path
from ucie_miner.public_library_mcp_adapter import (
    search_ucie_public_library_for_mcp,
    preview_public_skill_feed,
)

UCIE_ROOT = Path(r"D:\UCIE")

def existing_ucie_public_search_handler(
        query: str, category: str | None = None,
        tag: str | None = None, top: int = 5):
    return search_ucie_public_library_for_mcp(
        UCIE_ROOT, query=query, category=category, tag=tag, top=top)

# For a separately operator-approved read-only catalog tool endpoint:
def ucie_public_skill_catalog_handler():
    return preview_public_skill_feed(UCIE_ROOT)
```

This code sample is a **handoff for the existing runtime**, not evidence of
runtime installation. The currently installed MCP server is maintained
outside this public GitHub repository. This PR cannot change its tool
registry or its running tunnel. **Do not** replace that server, restart
the tunnel, or expose any new recipient-facing tool without a separate
operator-approved deployment. The existing MCP service's public-only
metadata and authorization boundaries must remain in effect.

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
