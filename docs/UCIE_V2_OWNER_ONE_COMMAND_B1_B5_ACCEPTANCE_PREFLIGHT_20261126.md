# UCIE V2 first-owner acceptance: one command, source-locked B1-B5 and safe Edge review

UCIE-only standalone `ucie_v2_owner_preview_preflight_v01` is bundled with Draft #384 (source-pinned). It responds to the owner's previously observed real Windows problems: another Python virtual environment was accidentally selected, an old Draft worktree did not know `--case all`, and PowerShell UTF-16 redirection displayed a blank HTML page. This **new isolated program fixes the UTF-8 file/open path and validates the exact source-linked B1-B5 HTML before opening a browser**. It does not install itself or modify V04.

`python -m ucie_miner.ucie_v2_owner_preview_preflight_v01 --check` produces one JSON offline static contract result (four fixed cases, three B3 scenarios, B5 source proof and comparator, version/SHA, no active third-party resources, no input/form/script, no misrepresented approved customer rights), and **does not create files or open browsers**. `--open` is explicit only: render static HTML, verify immutable hash and exact official links, save UTF-8 to deterministic collision-safe OS temp file with exclusive creation (reuse verified exact file), invoke Windows default HTML handler. Real Edge browser identity and user visual/keyboard/mobile usability are **not** programmatically asserted. The entrypoint never accepts arbitrary file paths, source input, URLs or customer code; no network, source execution, auto-promotion, schedule, operating SQLite, signed rules, online route, change to V04, or cross-project data.

Owner commands after reviewed PR code is available in a SEPARATE `D:\UCIE_V2_ACCEPTANCE` checkout, not the operating `D:\UCIE` original:
```powershell
$env:PYTHONPATH = "D:\UCIE_V2_ACCEPTANCE\src"
& "D:\UCIE\.venv\Scripts\python.exe" -m ucie_miner.ucie_v2_owner_preview_preflight_v01 --check
& "D:\UCIE\.venv\Scripts\python.exe" -m ucie_miner.ucie_v2_owner_preview_preflight_v01 --open
```
PowerShell redirection and inline Python are unnecessary. This only checks self-consistency/known first-party sources; not a live upstream independent reference check, hosted acceptance, production code diagnosis, actual UX 5-user comparison, owner approval or customer use. Human-subject experiments require separate consent and independent evidence. Recheck CI at same exact HEAD with Ubuntu/Windows Python3.13/3.15 jobs and source SHA. Label skipped jobs != PASS.

Unrelated protected owner local files, V04 app/route, scheduler, private content, rules and DB remain untouched.
