# Stage 2 — limited public-source mining preview

This is a **read-only, bounded, unauthenticated data-mining prototype**. It is not yet a production, 24-hour learning service.

## Exact source scope

The collector can read only the independent third-party public GitHub repositories hardcoded in the application:

- python/cpython
- PowerShell/PowerShell

It sends no GitHub tokens. It does NOT access a user's repository list, connected GitHub app credentials, or any other user's project. Source selection is pinned; arbitrary owner/repo arguments are blocked.

Each execution issues at most two pull list requests and ten per-PR file requests (default two per source = six calls total). API rate limits and upstream communication errors fail closed. It keeps a single bounded page of the 20 most recently updated closed PRs for each source. Broader crawling, licenses, opt-outs and timestamp cursoring remain future acceptance items.

## Data interpretation

Only merged PRs with fix-related keywords are considered. File patches are read briefly into memory, tagged by cautious heuristics, and discarded. The local database stores only:

- A public approved source slug, PR number and canonical source URL
- Upstream merge timestamp
- Aggregate SHA-256 digest of patch evidence
- Generic change tags
- Observation timestamp and UNVERIFIED_CANDIDATE_ONLY status

There is **no independent test execution** of upstream patches, no Rulepack promotion, no original code collection archive, no model weight training and no external project access.

## Run once on Windows after pulling this branch

~~~powershell
Set-Location D:\UCIE
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m ucie_miner mine-once
.\.venv\Scripts\python.exe -m ucie_miner report
~~~

Local results remain untracked under D:\UCIE\runtime\public_miner.sqlite3 and D:\UCIE\runtime\reports\. Do not git add these files. No scheduler is installed by this preview; background worker registration awaits independent review, local Windows test and disk quota policy.

The earlier ChatGPT automated technical reports are separate from this data store and cannot truthfully describe it until an explicit read-only reporting connector is established.
