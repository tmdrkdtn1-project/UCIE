# UCIE V2 B2 — Owner Windows Edge screenshot handoff (2026-11-27)

**Status:** PREPARATION ONLY. This procedure and any resulting screenshots are **not** independent UI acceptance, user testing, a source rights license or product release.

## Exact source scope

- Parent isolated B2 PR #400 (Draft). Use the **exact reviewed head**. The capture script and its tests live on this PR; do not copy code into a running V04 instance.
- All activity restricted to **UCIE isolated development worktree**. Never run this procedure in `D:\\UCIE` (owner protected original), do not modify Windows scheduled tasks, startup services, production DB or other projects.
- The server serves exactly two source-pinned first-party UCIE authored case selectors on `http://127.0.0.1:<free_port>/v2/truth`. No customer code or external address.
- A fully integrated production experience is **not** demonstrated; this is a localhost-only prototype.

## Operator-opt-in steps

1. Open a PowerShell window in an isolated UCIE checkout at the exact PR head. Verify the expected Python environment and run targeted CI/tests first.
2. In PowerShell terminal A, run:

   ```powershell
   python -m ucie_miner.b2_truth_preview_server_v01 --open-browser
   ```

   The output line `UCIE_V2_B2_TRUTH_PREVIEW_READY http://127.0.0.1:<port>/v2/truth` provides the **actual random port**. No trial runs from HTTP or from the default launch.
3. In PowerShell terminal B, with the actual URL substituted, run:

   ```powershell
   python scripts/ucie_v2_edge_visual_probe_v01.py --url "http://127.0.0.1:<port>/v2/truth" --output-dir "D:\\UCIE_DEV_PATCH\\runtime\\qa\\edge_truth_<unique_run_id>"
   ```

   Use a **new, empty directory** for each run. Script uses the installed Microsoft Edge executable from the standard Program Files locations, captures 5 CSS width requests (320/390/768/1024/1440 at 900 height), records artifact SHA-256 hashes and returns `SCREENSHOTS_CAPTURED_VISUAL_QA_PENDING`. It creates no screenshot when not explicitly invoked. Screenshot artifact files may contain local UI information; do not upload them publicly by default.
4. Inspect the five images; then **manually** inspect real Edge at 200% page zoom and use keyboard Tab/Enter/Shift+Tab and the skip link. Mark real browser accessibility, no overflow, 200% page zoom and Korean text wrapping as **PENDING** until observed. A screenshot alone does not test keyboard/focus or responsive viewport accuracy.
5. Optionally run a **separate**, explicitly requested synthetic proof preview:

   ```powershell
   python -m ucie_miner.b2_truth_preview_server_v01 --open-browser --run-synthetic-demo
   ```

   The second process runs fixed UCIE-authored Python/Git synthetic fixtures at startup **only**, stores receipts in volatile memory, then displays them via GET. It is not an exact tested-version receipt for any customer runtime. Do not treat receipt SHA or CI as upstream authentication.

## QA checklist

- At five widths: no clipped titles, panels, buttons, digests or horizontal scrolling; actual width must be confirmed visually
- 200% Edge page zoom: all information reachable; no lost focus
- Keyboard-only: skip link accessible, focus visible, navigation complete without mouse
- The two fixed cases have matching Capsule IDs; unrecognized source or duplicate query rejected
- Without opt-in: `자체 시험 기록이 연결되지 않았습니다`
- With opt-in: only first-party synthetic observations; **runtime version applicability UNKNOWN, independent QA PENDING, rights NOT APPROVED, distribution prohibited**
- Host mismatch -> 403; POST -> 405; no form, upload or new V04 routes
- Record exact branch HEAD, Windows version, Edge version, capture SHA receipt, actual observations, defects and reviewer identity/date

**No automatic PASS**. Capture script has no CSS overflow detector, contrast engine, keyboard bot or actual 200% page-zoom verification. A `SCREENSHOTS_CAPTURED_VISUAL_QA_PENDING` receipt is purely evidence inventory.
