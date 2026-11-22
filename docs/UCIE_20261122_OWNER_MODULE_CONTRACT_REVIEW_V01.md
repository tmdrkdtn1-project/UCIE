# UCIE Owner-Local Functional Review Packet V01 — REVIEW ONLY

**Purpose**: Move beyond aggregate counts and prepare an actionable *owner-local* source/test/API review for the 8 first-party original-only Python modules named by direct static imports. This is NOT a migration or runtime parity declaration.

## Grounded checkpoint (owner Windows; 2026-11-22 KST)

- Isolated staged source main `fa1dc281f528749fe59673792b6c47ac9c56a9db` after owner-only fast-forward.
- 20 originally untracked UCIE Python source-module path candidates: 8 distinct direct-import referenced, 11 root-symbol candidate, 3 overlap, 16 union, 4 without either observed style. All K0/HOLD.
- 14 original-only code/test referring files with stage-unindexed first-party module imports had original-only source module-name candidates. This does **not** establish successful import, 14 distinct modules, or equivalent functionality.
- 129 original-only test files had test-like AST syntax; **not** executed/collected/verified.

## New first-party isolated reviewer

Source: `src/ucie_miner/owner_module_review_v01.py`

The program requires the same exact staged-only Windows checkout with branch `main`, exact first-party origin URL, clean-or-verified-EOL-only Git status, and `D:\UCIE` original source identity through the existing read-only `layout_audit_v01.py` preflight. All local code input is limited to the already-authorized UCIE-only `src/ucie_miner`, `src/ucie_public`, `scripts` and `tests` Python/PowerShell scopes. Original code is **never imported or executed**.

Dry run (aggregate JSON only; no file writes):

```powershell
& 'D:\UCIE_PROJECT\UCIE\.venv\Scripts\python.exe' -I -B 'D:\UCIE_PROJECT\UCIE\src\ucie_miner\owner_module_review_v01.py'
```

Explicit optional *local report* (the only new write, outside both repositories):

```powershell
& 'D:\UCIE_PROJECT\UCIE\.venv\Scripts\python.exe' -I -B 'D:\UCIE_PROJECT\UCIE\src\ucie_miner\owner_module_review_v01.py' --write-private-report
```

With the explicit flag, one no-overwrite report is saved to:

`D:\UCIE_PROJECT\UCIE_OWNER_REVIEW\UCIE_OWNER_MODULE_REVIEW_<stage_sha_12>.json`

The report contains **private original module names, UCIE-relative original source/test references, public callable/class declarations, and staged name/argument-shape candidate paths**. The report contains no original code body, secrets, or raw byte hashes. The owner must **not paste or upload it to GitHub or this chat**. The aggregate CLI JSON contains *no* original module names, file paths, symbol names or source content. The file is created in an owner-local UCIE review directory only after the explicit opt-in, never under the operating checkout or staged Git repository. Existing output is never overwritten.

## Safe interpretations and decision gates

- A same-name/argument-shape stage declaration is **only a static review lead**, not equivalent behavior, import compatibility, signature compatibility, or deployment readiness. Source code with dynamic imports, constants, decorators, type comments, side effects or re-exports may not be represented.
- A linked original-only test is **not proof that it was executed or passed**. No original test code is executed.
- Original-only modules with only root-symbol leads or no observed lead remain K0/HOLD, not unused or deletable.
- The report is not an owner approval to copy/merge an original source file. Every actual source/test adaptation requires separately reviewed source provenance, dynamic import analysis, staged isolated tests, reversal plan and an explicit operation grant.
- Protected bridge-state records, SQLite, scheduler, C40/tunnel, original Git state, unrelated projects and live cutover remain excluded. LIVE_CUTOVER_NO_GO.

## Acceptance

- CI must pass Windows/Ubuntu × Python 3.13/3.15 using disposable synthetic fixtures.
- Actual owner-host results require a clean pinned stage-only fast-forward to the CI-verified merged SHA and local read-only invocation; GitHub CI is not an owner-machine acceptance.
- Record local dry-run summary in UCIE issue #199. Do not attach the private packet. Preserve all K0 holds.
