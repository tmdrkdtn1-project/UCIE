# UCIE Library V0.4 — Candidate review preparation (2026-11-01)

## Scope

On the owner Windows machine, browse already-approved **PUBLIC SOURCE ROUTES**
from the existing UCIE Stage10/12/15 source-linked W04 ledger. Existing
V0.2/V0.3 implementations and the hourly collector remain unchanged.

The V0.4 new view **검증 준비표** is a **READ-ONLY per-candidate verification
plan**, not an executed verification or completed approval workflow. Every
request recomputes the current UCIE handoff with the original ledger
fingerprint, source revision and source skills checks. Source metadata and
review blockers are bound to exact candidate SHA identities.

The six review gates explicitly separate:
1. Source provenance / immutable reference / SHA linkage observed.
   This does NOT prove the fix works.
2. Release version applicability: NOT_VERIFIED.
3. License and permitted reuse: NOT_VERIFIED.
4. Independent regression reproduction: NOT_VERIFIED.
5. Security impact review: NOT_VERIFIED.
6. Human owner approval and distribution: NOT_VERIFIED.

Unknown blocker codes are not surfaced as arbitrary external instructions.
The allowed review questions and next actions originate only from existing
UCIE-owned fixed skill profiles. User-entered statements, third-party PR
text and successful CI of the *browser* are never treated as candidate
verification receipts.

No review record is written or edited. No credentials, external code, fetch
requests, source-file browsing, project-to-project access, auto-promotion,
scheduled task changes or package export. No V1 Library acceptance claim.

## New files to install

Only these NEW paths, after pinned commit and CI verification:
- src/ucie_miner/library_review_v04.py
- src/ucie_miner/library_browser_v04.py
- scripts/ucie_library_browser_v04.ps1
- tests/test_ucie_library_v04.py

The owner may have unrelated local working files. Do NOT broadly pull,
reset, clean or checkout. Preserve the existing V0.3 UI as a fallback.

Windows PowerShell:

    & 'D:\UCIE\scripts\ucie_library_browser_v04.ps1'

Open the emitted http://127.0.0.1:PORT/ URL on the *same machine*, search
and click **검증 준비표** for one public candidate. Check that all six
gates show missing external proof and no candidate becomes approved.
The search-result back link reconstructs the exact current filters/page.
V0.3 compare selection continues to work.

Synthetic-only regression:

    $env:PYTHONPATH = 'D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_library_v04.py' -v

V0.4 is **verification readiness** only. Future actual evidence recording
must be source-pinned, independently tested, opt-in, and separately reviewed
before any status can move beyond NOT_VERIFIED.
