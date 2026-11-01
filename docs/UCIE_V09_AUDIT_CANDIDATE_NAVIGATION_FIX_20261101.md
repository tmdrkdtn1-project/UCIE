# UCIE V0.9 — owner-reported audit candidate navigation repair (2026-11-01)

## Owner acceptance defect

Owner confirmed V0.6–V0.7 Windows function acceptance 4/4, then
installed V0.8–V0.9 and provided a real Windows audit screenshot showing
588 valid source-linked public candidates but **zero V0.5 submitted review
receipts**. Existing V0.7 priority review queue displays only candidates
with received claims. The audit dashboard consequently showed no selectable
candidate links, making the V0.9 public original SHA check unreachable.

This is a navigation defect, **not** a source verification, miner, ledger
integrity or permission error. AUDIT_REVIEW_REQUIRED_NO_GO is correct.
A receipt-free candidate must remain selectable.

## Patch

- /audit has a prominent **공개 후보 선택 · 전체 원장** section before
  the statistics, with five source-balanced preview links and a
  **전체 공개 후보 목록 열기** link even when 588/588 have no receipts.
- /audit/candidates displays every current source-linked, unverified
  candidate across bounded 20-row pages, source/domain selectors,
  deterministic stable ordering, previous/next navigation and direct
  **후보 검토하기** links.
- /audit/item/<sha> remains the existing source-linked V0.7 detail;
  its existing V0.9 **공개 원본 SHA 대조 실행 (명시적 조회)** link
  triggers the approved public API only when clicked.
- Source/domain choices belong to UCIE's immutable five approved public
  repositories and skill registry. Unknown/duplicate URL fields, bad pages
  and off-allowlist candidates are rejected; all text is escaped.
- The original V0.7 claim-prioritized queue intentionally remains empty
  without received claims; candidate selection is independent of it.

## Regression

Synthetic fixture has 26 linked candidates and zero receipts. Tests cover
five-source preview, page1=20/page2=6 without duplication, Python filter,
empty legal cross-filter, disallowed query fields, explicit-click-only
public proof, localhost Host validation and GET-only behavior.
No real external fetch occurs in CI.

No candidate becomes tested, legally licensed, version-specified, approved,
or exportable. Owner-host Windows final acceptance remains separate from CI.

## Minimal owner installation

Replace only one V0.9 browser file after checking exact old and new Git blob
SHA values, and add two new files:

- src/ucie_miner/library_browser_v09.py (replace exact prior blob only)
- tests/test_ucie_v09_audit_navigation.py (new)
- docs/UCIE_V09_AUDIT_CANDIDATE_NAVIGATION_FIX_20261101.md (new)

V0.1–V0.8 code, operating DB, existing review receipt directory,
V0.9 public source probe and the hourly task remain unchanged.
Do not blanket git pull, reset, clean or access another project.

Owner acceptance: Audit dashboard -> candidate list (zero receipts allowed)
-> candidate review -> click explicit public source SHA check.
All displayed fix/version/license/regression/owner gates remain unverified.
