# UCIE W03 + W04 — 기존 수집기의 어댑터 연결 및 첫 도서관 실제 검색 (2026-10-27)

**PRODUCT:** UCIE four-pillar development intelligence and virtual library.
**WORK BATCH:** W03+W04. This is the initial functional slice, not the full P2/P3 or V1.

## W03 — existing approved public-source acquisition adapter

- Module: `src/ucie_miner/public_source_adapter.py`.
- `adapter_plan("repo:python/cpython")` returns the already existing
  `public_feed_url` route with source ID, page cursor, bounded request budget
  and explicit *not authorized by registry* marker.
- `adapt_existing_public_discovery(source_ids=(...), fetch=existing_callback)`
  reuses `public_discovery.discover_all_feeds` to convert reviewed public
  metadata to the shared source-adapter envelope.
- **Important:** caller must supply a fetch callback; there is no implicit
  transport, new source, new rate budget, new credentials, scheduler install,
  or operating data write. Existing opt-in gates and URL restrictions remain.
- Only the currently approved repository sources are supported. Official
  documents continue using existing `public_evidence_routes.py` until W06.
  Survey-only services remain blocked.

## W04 — searchable existing Stage12 candidate review shelf

- Module: `src/ucie_miner/library_search.py`.
- Reuses `verification_handoff.prepare_verification_handoff`: it checks
  Stage10 source metadata, opted-in Stage15 revisions, Stage12 queue linkage,
  trusted source and schema/row fingerprint using read-only SQLite.
- Converts each validated unverified row to W02 `LibraryEntry` in memory.
- `query` text filters **source/skill/domain/pattern/reference** only; `kind`
  and exact `source_id` filters also supported. Maximum 20 returned rows.
- Reports public URL, source evidence SHA, revision, pattern and
  `UNVERIFIED_CANDIDATE_ONLY` lifecycle with explicit no approval/export.
- Does not read raw upstream code or external project files; no network,
  index writes, migrations, signatures or auto promotion.
- A lagging/incomplete Stage12 queue returns an empty `NO_GO` result, not a
  fictional valid library catalog. This is only the **candidate-review shelf**;
  independent approved Rulepacks, engine/skill extraction and full search are
  still separate W07/W05/P3 work.

After owner-host code synchronization (do not use git reset/clean on the dirty
UCIE checkout):

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
$py = 'D:\UCIE\.venv\Scripts\python.exe'
& $py -B -m ucie_miner.library_search --query python --limit 5
& $py -B -m ucie_miner.library_search --source-id repo:git/git --limit 5
```

W03 can be imported without executing transport:

```powershell
& $py -B -c "from ucie_miner.public_source_adapter import adapter_plan; print(adapter_plan('repo:python/cpython'))"
```

## Next active implementation

**W05 engine/skill/learning logic discovery** from permitted public evidence
is next, alongside **W04's expanded shelves**: approved, version-pinned
Rulepacks and generic technical methods, plus search quality measurement.
Avoid interpreting Stage12 candidates as proven successful skills or executable
source code. Integrate existing official document/release/advisory routes in
W06 without expanding the approved source list.

## Test / evidence status

- `tests/test_ucie_public_adapter_library_search.py` exercises an existing
  UCIE synthetic discovery callback (W03) and a real synthetic Stage10→12
  SQLite ledger (W04), including preservation of source bytes before/after
  search and denial of unapproved source input.
- A test run validates only the exact tested SHA, not local owner-host
  runtime, external interoperability, licensing, or product V1 acceptance.
