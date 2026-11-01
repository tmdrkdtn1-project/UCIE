# UCIE V0.5: Bundled public evidence claim intake, receipt integrity and viewer

Date 2026-11-01. Scope: UCIE only; public technical evidence routes.
This is a **REVIEW CLAIMS RECEIPT** system, not an independently verified
fix, SPDX license opinion, version compatibility declaration, or signed
Rulepack delivery.

## One combined milestone

1. Manual opt-in receipt registration: owner selects an exact source-linked
   public candidate SHA-256, one of four review gates, an approved official
   public evidence URL, a *claimed* content SHA-256, and optional version hint.
   No freeform text, code, credential, reviewer's identity, local file path,
   executable recipe or external source scanning.
2. Source and binding validation: each write re-reads UCIE's source-bound
   Stage10/12/15 handoff, checks known candidate identity, source SHA and
   unverified state. Approvals are never inferred.
3. Dedicated append-only receipts: private to UCIE's local
   D:\UCIE\runtime\public_review_v05\receipts, with deterministic receipt ID,
   self-integrity digest, duplicate collapse, and fail-closed corrupt/unknown
   rows. A local exclusive lock serializes explicit writes, with temporary
   file and atomic rename. Stale lock => fail closed for manual remediation.
   No existing operational SQLite DB, scheduler, or Rulepack changes.
4. Read-only receipt browser: V0.5 inherits V0.4's search, filters,
   comparison, detail and result-return behavior. Each candidate's
   검증 준비표 displays the submitted public URL, claimed digest, submission
   time and counts per gate. All six gate states remain NOT_VERIFIED, except
   the existing SOURCE_LINKAGE_ONLY_NOT_FIX_VERIFIED.
5. Regression and security: synthetic owner-only handoff, duplicate,
   tamper, wrong project/symlink, fake approval, unapproved URL, 2–3 comparison
   and actual HTTP localhost tests; CI Windows/Linux Python 3.13/3.15.

## Important semantic distinction

The provided public citation has NOT been fetched or attested by this
feature. The digest has NOT been calculated by this feature. A submitted
claim cannot flip version approval, legal license signoff, independent
regression PASS, security review completion, owner signature,
auto-promotion, candidate release, or external code execution.

Only exact official public document hosts and narrowly typed URLs for the
candidate's pre-approved repository are accepted as citation references;
there are NO network requests. Submitted URLs are untrusted text, not
instructions. Browser is GET-only and binds localhost Host.

## Owner installation without broad git sync

V0.1–V0.4 modules and scripts are unchanged. Verify exact merged commit
and install only these NEW files:

- src/ucie_miner/library_review_records_v05.py
- src/ucie_miner/library_browser_v05.py
- scripts/ucie_library_browser_v05.ps1
- scripts/ucie_review_record_v05.ps1
- tests/test_ucie_library_v05.py
- docs/UCIE_LIBRARY_V05_PUBLIC_REVIEW_CLAIMS_20261101.md

Do not run git reset --hard, git clean, or pull into a worktree with
unrelated local changes.

Start the browser (only on the owner Windows PowerShell, not SSH):
    & 'D:\UCIE\scripts\ucie_library_browser_v05.ps1'

The browser prints http://127.0.0.1:PORT/ . Search, open 검증 준비표,
inspect the receipt counts (initially 0), return to same filtered results.

The receipt writer is SEPARATE and never invoked from a browser button.
Only with a real, manually supplied public evidence URL and claimed digest,
a user may explicitly invoke scripts/ucie_review_record_v05.ps1 with
-ItemId, -Gate, -EvidenceUrl, -ClaimedSha256 and optional -VersionHint.
NO review data is created until a complete valid owner command is executed.

Test only with synthetic fixtures:
    $env:PYTHONPATH = 'D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_library_v05.py' -v

Owner Windows acceptance of V0.5 is separate from CI. No claim is made
that any current candidate records are legally licensed, tested,
ready for use, or approved for deployment.
