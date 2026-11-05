# UCIE SkillBook / W04 opt-in federated read-only catalog V0.1

PROJECT=UCIE ONLY
STATUS=FIRST_PARTY_DRAFT_NOT_APPROVED

UCIE SkillBook 001 and existing W04 public evidence are two distinct shelves.
An official-doc SHA for SkillBook does NOT attest a W04 public PR candidate.
No SQLite schema migration, index replacement, background scheduler, C40 restart,
auto-promotion, auto-learning, export, package signing, or production approval.

## Owner-local launch
From an owner PowerShell on the existing UCIE Windows PC:

    & 'D:\UCIE\scripts\ucie_skillbook_union_library_v01.ps1'

Open the printed http://127.0.0.1:PORT/catalog address locally.
The default shelf is SkillBook-only: no W04 database read.
Select "all" or "public" to opt into the existing
search_existing_public_library() read-only source-linked W04 search.
Ctrl+C stops the local browser; it is not a service or scheduled task.

Routes: /catalog, /catalog.json, inherited /skillbooks, /, /audit, /health.
Queries are bounded and sources are still restricted to the UCIE allowlist.
W04 supports only ASCII queries; Korean queries keep SkillBook results
and explicitly report W04_NONASCII_QUERY_NOT_SUPPORTED_NO_SEARCH.
An incomplete W04 ledger is SOURCE_LINKAGE_INCOMPLETE_NO_GO, not "0 results".
No approved exports are provided.

## QA and release gates
- Exact-code CI Windows/Ubuntu Python 3.13/3.15: independently inspect run.
- UCIE Windows synthetic HTTP and opt-in W04 fake reader tests.
- Owner opt-in actual W04 read-only query and observed UI screenshots: pending.
- Independent behavior/security QA, source rights, signoff, package export: pending.
- Existing runtime DB, C40 supervisor, scheduler and other projects: no changes.
