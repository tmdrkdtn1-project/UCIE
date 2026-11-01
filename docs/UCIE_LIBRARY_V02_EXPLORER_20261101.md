# UCIE Library V0.2 — Ranked Public Evidence Explorer (2026-11-01)

Status: UCIE-authored standalone local review-only slice, NOT complete Virtual
Library V1. Reuses original verified W04 Stage10/12/15 source handoff. No API
calls or collection, no database or scheduler mutation, no third-party
source code execution, no cross-project access, no candidate promotion.

## Scope and UX

- Read-only search across **all** currently source-linked candidate revisions
  (up to the 1000 existing accepted W04 handoff bound), not the initial 20 rows.
- Without a search term, deterministic round-robin distribution over approved
  public source repositories, avoiding an all-PowerShell first page.
- With text, bounded **lexical** relevance weighting for purpose_code, domain,
  source and public URL. Not semantic ranking, vulnerability severity,
  independent evidence quality, trust score or model inference.
- Filter by domain/source/kind and inspect counts by domain and source.
- Page size 5, 10, or 20, bounded to 200 pages. Full result page traversal
  through HTML GET links. Exact hash-linked detail routes.
- Detail: code-derived purpose summary, public PR link, revision, evidence SHA,
  version **UNDETERMINED**, license-review status, explicit unverified and
  unapproved indicators. Does NOT expose source snippets or claim fixed behavior.
- Duplicated review revisions for the same public source/PR/purpose are grouped
  and counted without considering them independently approved.

## Owner host use (Windows D:\UCIE)

Owner worktree may have unrelated tracked local modifications. **Do not** run
git reset --hard, git clean, or broad pull. Bring only these NEW files from an
exact CI-tested Git commit when reviewed:
- src/ucie_miner/library_explore.py
- src/ucie_miner/library_browser_v02.py
- scripts/ucie_library_browser_v02.ps1

The existing V0.1 launcher and code remain unchanged.

Run:

    & 'D:\UCIE\scripts\ucie_library_browser_v02.ps1'

The JSON startup receipt prints a new, local-only http://127.0.0.1:PORT/
address. Open from the same owner PC browser. The process occupies the
PowerShell session until Ctrl+C. No Windows task registration or service
installation takes place.

## Tests / acceptance

Synthetic, bounded HTTP loopback tests:

    $env:PYTHONPATH = 'D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_library_v02.py' -v

Acceptance requires no false approval, incomplete Stage12 source linkage
blocking results, strict path/parameter/HTTP method filtering, safe HTML
escaping, deterministic paged result completeness and exact detail identity.

Caveat: passing disposable CI tests does NOT prove owner-host database
validity, latency, web browser display or full Library V1 acceptance.
