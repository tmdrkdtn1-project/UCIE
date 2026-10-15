# UCIE Stage 14 — External official public releases, advisories and docs

Stage 13 actual Windows host execution examined **100 published/closed PR API
records from exactly 5 allowed independent repositories**, retained 22
unverified digest-only candidates and durably advanced all page cursors to 2.
Stage 14 adds different, independently useful **public official evidence
classes**; no model or rule promotion is implied by their presence.

## Official upstream sources and provenance restrictions

The same five approved repositories remain the ONLY public GitHub repository
targets:
`python/cpython`, `PowerShell/PowerShell`, `git/git`,
`modelcontextprotocol/python-sdk`, `actions/runner-images`.

For **one** chosen allowlisted repository per opted-in cycle (round robin),
the engine requests at most **three** public resources:

- Published GitHub Releases API page:
  `GET https://api.github.com/repos/{approved}/releases?per_page=10&page=N`
  (at most 100 pages/repository, one page per its five-cycle visit).
  Records use numeric release IDs, SHA256 hash of metadata, publication UTC
  and fixed candidate state. Draft/prerelease excluded. Repositories without
  GitHub Releases reach `EXHAUSTED`; ordinary Git tags are NOT inferred to
  be releases.
- Public repository security advisories endpoint:
  `GET https://api.github.com/repos/{approved}/security-advisories?state=published&per_page=10`
  (recent published GHSA only; this IS NOT exhaustive historical security
  advisory pagination). Record only strict GHSA identifier, severity and
  publication-time digest; do not retain/adopt advisory descriptions or
  untrusted instructions. Unsupported/unavailable responses are **PARTIAL**,
  not an invented zero-vulnerability verdict.
- Pinned official public documentation URL for the selected source, reused
  from UCIE's existing `DOC_ENDPOINTS` fixed allowlist (Python docs,
  Microsoft PowerShell docs, Git manual, MCP specification, GitHub Actions
  runners documentation). Retrieve a bounded HTML/text response, hash
  bytes only and retain a digest with observation time; neither store nor
  execute HTML/commands. Repeated hashes are deduplicated. This tracks
  **observed document snapshots**, not versions from past years.

Output is a new, isolated UCIE-only
`runtime/stage14_official_public_sources.sqlite3` SQLite store with
identity/version checks, bounded rows and exact fixed tags. The existing
miner, Knowledge, Stage 10, Stage 12 and Stage 13 DBs are not written by
Stage 14. All third-party content remains untrusted.

### Actual request budget and uncertainty

An eligible Stage 11 hourly run may use at most 8 recent-feed GETs, Stage 13
at most 5 historical PR page GETs, and separately opted-in Stage 14 at most
3 additional official source GETs (total ceiling 16 per due UCIE hour).
GitHub anonymous rate limits are shared by IP, not reserved by UCIE; 403,
network errors and disallowed redirects are surfaced as partial/failed,
not PASS. The optional official step stops remaining GETs when a GitHub
quota header reports fewer than 12 remaining requests. The official
documentation GET may be blocked or redirect, and is not silently
substituted by an unapproved URL.

## Separate host activation (OFF until explicitly opted in)

Stage 14 requires its OWN existing UCIE runtime text marker:

- `D:\UCIE\runtime\stage14_official_opt_in.txt`
- exact ASCII token `UCIE_STAGE14_OFFICIAL_OPT_IN_V1`

Do not create this marker until the PR has passed CI and been merged
and updated on the owner PC. Existing Stage 11 marker does NOT imply
permission to create this extra ledger or read additional external URLs.

Operator read-only inspection:

```powershell
$prior = $env:PYTHONPATH
try {
  $env:PYTHONPATH = 'D:\UCIE\src'
  & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner inspect-official-public-evidence
} finally { $env:PYTHONPATH = $prior }
```

Optional explicit ONE-TIME live retrieval, only after separately enabling:

```powershell
$marker = 'D:\UCIE\runtime\stage14_official_opt_in.txt'
if (Test-Path -LiteralPath $marker) { throw 'Review existing marker before use' }
Set-Content -LiteralPath $marker -Value 'UCIE_STAGE14_OFFICIAL_OPT_IN_V1' -Encoding Ascii -NoNewline
$prior = $env:PYTHONPATH
try {
  $env:PYTHONPATH = 'D:\UCIE\src'
  & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner collect-official-public-evidence-once --live
  & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner inspect-official-public-evidence
} finally { $env:PYTHONPATH = $prior }
```

When active, the engine uses the already registered UCIE hourly task,
no new task, no credential and no unrelated-project access. Deleting
only the Stage14 marker disables future Stage14 observations; already
collected hash-only metadata is not deleted automatically.

## Strict interpretation

Published upstream release/advisory metadata is NOT evidence that a specific
bug was independently reproduced, actually fixed on all runtimes, or safe
to apply in production. A documentation hash change is a research lead,
NOT proof of a specification change. No full original document or release
body is re-published. Security results are limited to published GHSA on
five approved repositories; other official security bulletin sources and
historical full corpus require further explicit route/source approvals.
Neural training, permanent verified Rulepacks, external patch execution
and rule auto-promotion remain disabled.
