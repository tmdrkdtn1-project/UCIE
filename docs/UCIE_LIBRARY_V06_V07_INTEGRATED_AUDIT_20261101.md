# UCIE V0.6 + V0.7 — Unified source-bound audit and prevention-review milestone

Date: 2026-11-01. Repository: UCIE only. Status: browser and audit code,
synthetic CI; *not* independent upstream fix verification or approved rules.

This is one bundled milestone, **not** two separate deployments:

1. **V0.6 public evidence classification.** Recheck that claims remain V0.5
   unverified receipts bound to the candidate SHA. Classify an official
   document URL, a public PR/commit, an exact license-file citation, or a
   CI-run URL as citation *shapes*. These are not evidence of page contents,
   license grant, applicable release version, independent CI result,
   security signoff or fixed behavior.
2. **V0.7 complete review audit.** Use ONE current Stage10/12/15
   source-linked handoff and ONE read of the dedicated V0.5 receipt
   directory; do not re-read the 584+-candidate ledger for every row.
   Report receipt integrity, stale/orphaned submissions, source SHA drift,
   inconsistent claimed digests/versions for the same public citation,
   domain/source/gate distribution, and a bounded review queue.
   Conflicting reports carry NO_GO.
3. **Inert prevention rule review guides.** Display UCIE-authored fixed
   domain-specific review questions and safe-next-check tokens, never
   executable scripts, Rulepack artifacts or trusted results from an
   unverified PR. Unclassified/unsupported sources fail closed.
4. **Integrated localhost read-only UI.** Keep V0.5 search, comparison,
   pagination, selected-candidate restoration and receipt viewer intact.
   New /audit and /audit/item/<64-hex> show cross-candidate checks, blocked
   items, proof gates and inert review guidance. GET-only, no external
   scripts, no network calls to untrusted PRs, no cookies.
5. **Real regression gate.** Synthetic all-candidate audit, one-pass
   source read, conflict/orphan/forgery/release protection, corrupted
   receipt rejection, and local HTTP status and boundary tests on
   Windows/Linux Python 3.13/3.15.

## Hard status boundaries

- V0.5 user-submitted document SHA is *not* recomputed by V0.6.
- No candidate upstream release version, copyright license, regression
  behavior or security fix has been independently verified by this task.
- CI proves UCIE audit/browser software behaviors, NOT the correctness of
  third-party change candidates.
- Source provenance check != code fix verification.
- The audit summary SHA-256 is for local report integrity/repeatability;
  not a cryptographic reviewer signature or license approval.
- All candidates remain UNVERIFIED_CANDIDATE_ONLY; all rule guides are inert.
- Zero auto promotions, approvals, package exports, collector changes,
  scheduler registration or operating DB writes.
- No other local project, connected account, user file or private source
  may be mined by these modules.

## Owner install and smoke QA

Keep all prior V0.1–V0.5 code and data unchanged. After PR merge and
SHA-pinned review, install only the **six new files** below:

- src/ucie_miner/library_proof_assessment_v06.py
- src/ucie_miner/library_audit_v07.py
- src/ucie_miner/library_browser_v07.py
- scripts/ucie_library_browser_v07.ps1
- scripts/ucie_audit_v07.ps1
- tests/test_ucie_library_v07.py


Do not use blanket git pull, reset --hard, clean or checkout over owner
worktree changes.

Owner Windows PowerShell:
    & 'D:\UCIE\scripts\ucie_audit_v07.ps1'
    & 'D:\UCIE\scripts\ucie_library_browser_v07.ps1'

The first command prints a bounded JSON audit with receipt hash and no
persistent writes. The second prints the ephemeral 127.0.0.1 URL. On
the same PC check: search; compare 2-3; review worksheet; select
**전체 공개 근거 검증·감사 현황**; select one candidate audit item.
Verify all version/license/regression/approval statuses remain unverified,
and back navigation still preserves filters/page and prior selections.

Windows synthetic regression:
    $env:PYTHONPATH = 'D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_library_v07.py' -v

### Future independent proof gate

Actual external content hash re-computation from official release bytes,
source license file consistency, pinned independent safe regression
runner receipt, and owner signed release attestation must be implemented
and separately proven before transitioning any candidate to VERIFIED.
