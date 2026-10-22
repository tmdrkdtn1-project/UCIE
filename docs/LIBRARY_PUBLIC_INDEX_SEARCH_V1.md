# UCIE Library: unified public metadata search

**Implemented:** read-only taxonomy search over the two existing UCIE public-only indexes:
- Stage 13 `runtime/stage13_external_public_history.sqlite3` (historical, hash-only, up to 80k stored evidence revisions).
- Stage 10 `runtime/stage10_unverified_public_candidates.sqlite3` (recent PR and direct Git commit candidate evidence).

**Not implemented:** web-scale full-text/semantic search, verified skill installation, export of approved learning packages, new service endpoints, private-project feedback, scheduler changes or release authorization.

## Operator read-only query

```powershell
Set-Location D:\UCIE
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner search-library --source python/cpython --limit 10
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner search-library --skill-id mcp-api-compatibility
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner search-library --tag REGRESSION
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner search-library --index history --limit 20
```

The query creates no DB or network request and does not touch operating miner or knowledge data. A new UCIE checkout without an index returns `PUBLIC_LIBRARY_INDEXES_ABSENT_NO_GO` and an empty result set, not fictional knowledge. Results are a bounded first-page selection only (maximum 50); high-volume corpus pagination and contextual relevance are future work.

Results contain canonical approved public PR / git commit references, exact pinned revision and evidence hashes, fixed first-party technology domain, source-matched technical labels, safe review question, and a non-executing review suggestion. Only exact duplicate public URL + pinned upstream SHA + evidence fingerprint records are deduplicated; distinct evidence revisions remain visible. Recent Stage 10 records appear first by default. Use `--index history` or `--index recent` to inspect either index independently.

Every returned record remains `UNVERIFIED_PUBLIC_RESEARCH_ONLY_NO_GO`. No signed skill payload is installed or injected. Public evidence metadata is not proof of a fixed product release or licensing/QA acceptance.

This index query is the minimal **UCIE Library retrieval foundation**. Its purpose is for future **read-only recipient-facing search**, but that connection is not deployed or authorized in this change. Any recipient must independently choose and apply verified public guidance; no project telemetry or private code is sent to UCIE.

## Acceptance boundary

Focused UCIE-authored synthetic test: `tests/test_ucie_public_library_search.py`, plus the existing GitHub offline matrix. No actual user-host corpus search or MCP search-endpoint upgrade is claimed until those are separately performed and observed.
