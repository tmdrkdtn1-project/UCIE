# UCIE V2 G4.1 — Windows Microsoft Edge 격리 브라우저 인수 (2026-11-26)

PROJECT=UCIE ONLY · STATUS=ISOLATED_WINDOWS_GITHUB_EDGE_QA_ONLY · OWNER_HOST_PENDING · B6_NO_GO

## 원본 및 현재 승인 범위
- Main pin: `f5fbaca6c94f50130941570090c2c555cf92d816`. Operating Windows original tree is dirty; do not touch.
- Stack: V2 design Draft PR #351, evidence/novice PR #352, targeted B3 PR #353, bounded B4 PR #354, synthetic-only B5 PR #355, functional G0–G2 PR #356, Linux Chromium G3 PR #357. All remain Draft and unmerged.
- G3 exact source HEAD: `32540fff57919ea888499ce9441b17df0ac8c9d4`. Linux Chromium UI: GitHub run `45756157764` 17/17 real browser tests PASS. Offline Ubuntu/Windows 3.13/3.15: `45756157777` 4/4 SUCCESS. This does NOT validate G4 branch before its own HEAD checks.
- G4.1 approval is **disposable GitHub-hosted Windows runner QA only**. It does not authorize `D:\UCIE` mutations, resident V04, owner Windows Edge automation, customer files, operating SQLite/task, C40/Tunnel, sources outside approved five repos, prompt/model training, signing, or customer release.

## 구현과 검증 계약
1. **Reuse** the existing 17 source-joined browser tests `tests/test_ucie_v2_g3_isolated_browser_v01.py` instead of making a second copy. Explicit `UCIE_G3_BROWSER_QA=1` plus `UCIE_G3_BROWSER_CHANNEL=msedge` selects real Playwright `chromium.launch(channel="msedge", headless=True)`. No 'Chromium is Edge' substitution is permitted: browser `navigator.userAgent` must contain `Edg/`; else fail closed.
2. New runner-only workflow `.github/workflows/ucie-v2-g4-isolated-edge.yml` targets `windows-latest`, exact PR HEAD, pinned Python 3.15 and Playwright 1.58.0, verifies an actual installed Edge binary and `Malgun Gothic` Korean font. It does not install Edge or modify owner PC; no live service or customer data.
3. Browser tests cover real UCIE `render_preview()` joined to original B1–B4 case IDs and old GET handlers on a `127.0.0.1` temporary port, same prior 3 choices, native fallback on strict CSP/JS disabled, keyboard/Enter/focus, 320/390/768/1024/1440 widths, CSS 200% zoom, long Korean, offline/unsupported cases, forged rights HOLD, privacy-safe network boundary and one primary safe action with technical details disclosure.
4. The run writes `g4-edge-browser-receipt.json` and `g4-edge-*.png` screenshots as **UCIE-owned synthetic-only evidence**, with exact git HEAD, Edge UA/version, zero observed humans/owner Edge modifications/customer rights and independent QA still pending. A test log and screenshot from G3 Linux must not be reported as Windows Edge PASS.
5. Existing four-matrix general offline CI must pass separately on the G4 PR exact HEAD. The G3/G4 browser test module skips under the general offline workflow without opt-in; SKIP is not browser PASS.

## Next-work review / acceptance decision
- **G4.1 DONE** only after both Windows Edge real browser workflow and unchanged four-environment offline CI finish success on the same exact G4 HEAD; inspect synthetic screenshot for readable Korean, one first action, no horizontal clipping.
- **G4.2 OWNER Windows Edge is NOT THIS TEST.** Before attempting actual owner-host acceptance, require explicit authorization, preserve/backup existing dirty files, verify installed owner local V04/ports/CSP/security/rollback and perform read-only-first Windows Edge checks. No auto-upgrade or deployment from CI.
- **B5 real user evidence** remains 0 first-time coder participants, 0 expert reviewers, 0 buyers until separately consented/recorded human studies. Do not infer human time-to-safe-action or market value from synthetic benchmarks.
- **B4 Virtual Library development** retains coequal priority. New held-out *approved public source* generalization, failed-transfer counterexample, rights/version lineage and independent review remain pending; curated Python/Git→MCP synthetic transfer is not universal automatic inference.
- **B6 C0–C5 commercial distribution NO-GO** pending independent rights/security, Windows recipient installer/update/rollback/signing, first-use owner acceptance and separate owner approval.
