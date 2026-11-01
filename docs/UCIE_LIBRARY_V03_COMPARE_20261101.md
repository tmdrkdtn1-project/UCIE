# UCIE Public Evidence Library V0.3 — Candidate comparison (2026-11-01)

## Owner V0.2 acceptance

The owner manually verified all four Windows V0.2 functions on 2026-11-01:
unfiltered candidate search, second page, SHA-linked detail view, and Python
domain filtering. This is **V0.2 functional acceptance only** and is not a
verified software fix, licensing opinion, Rulepack promotion, or V1 release.

## V0.3 scope

- Review-only side-by-side comparison of exactly **two or three** selected
  public evidence candidates on the *current search results page*.
- Source identity, SHA-256, revision, grouped revision count, purpose code,
  license-review status, version-unknown status and fixed UCIE review prompts.
- Advisory text is owned by UCIE and taken exclusively from existing
  source-specific PROFILE constants. No external PR title/body/instruction
  is used as a source of executable advice.
- All compare requests independently repeat verified Stage10/12/15 ledger
  linkage; a stale, unknown, ambiguous, forged or unapproved candidate is
  blocked. No persisted selections, search history, third-party GET,
  operating SQLite writes, new scheduler registration or package export.
- Search, pages, facets and detail continue to use existing V0.2 functions.
  Original V0.1/V0.2 files and launchers remain unchanged.
- Compare form carries original bounded search term, kind, domain, source,
  page number and page size as hidden GET fields. The comparison page's
  **선택했던 검색 결과로 돌아가기** link restores that exact filtered page
  and re-checks the two or three previously selected candidate checkboxes
  if they are still present in the freshly source-validated results.
- The return URL is locally constructed from validated fields and SHA-256
  identities. No stored session, arbitrary redirect URL, JavaScript,
  operating DB write or scheduler changes. Old item-only comparison deep
  links still work; with no incoming context, their return link goes to
  the initial form.


## Owner Windows installation

Use only pinned new-file deployment; never bulk reset/clean/pull an owner
worktree with unrelated tracked local changes.

New files:
- src/ucie_miner/library_compare.py
- src/ucie_miner/library_browser_v03.py
- scripts/ucie_library_browser_v03.ps1
- tests/test_ucie_library_v03.py

After CI and single-file installation, first stop the existing browser
with Ctrl+C. Run:

    & 'D:\UCIE\scripts\ucie_library_browser_v03.ps1'

Open the emitted http://127.0.0.1:PORT/ address on that same PC.
Search all candidates, mark exactly two or three checkboxes and click
'선택한 후보 비교'. Confirm that the comparison shows different public sources,
item hashes, and explicitly unknown applicability/approval fields.
Close with Ctrl+C. Running two browser versions in parallel is unnecessary.

Synthetic-only test:

    $env:PYTHONPATH = 'D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_library_v03.py' -v

No claim of independent version compatibility tests, on-owner measured
performance, approved skills, cross-project learning or completed V1 platform.
