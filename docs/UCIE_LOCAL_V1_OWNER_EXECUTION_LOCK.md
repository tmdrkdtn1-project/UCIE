# UCIE LOCAL V1 - HARD-CODED OWNER EXECUTION CONTRACT

Owner decision: 2026-11-08. Executable contract: src/ucie_miner/local_v1_priority_v01.py.

## Strict development order

1. LOCAL PRODUCT (mandatory now): L1 one Windows launcher and browser; L2 four real user workflows on UCIE-only public evidence/first-party code; L3 local restart/offline/error owner acceptance.
2. ONLINE + DESIGNATED CUSTOMER DELIVERY (blocked until local V1 accepted): private distribution, license/signature, online hosting, commercial installer, SBOM/rightsholder/security review and pilot. The separate full commercial release gate remains NO_GO.
3. PERIPHERAL/EXPANSION (blocked until local V1 accepted): new collectors, scheduler refactors, extra dashboards/platforms/skills, performance tuning, additional proof-only infrastructure.

Start no task unless it directly enables an LG1-LG6 local product user action or fixes an observed blocking defect. The source-coded LOCAL_WORK allowlist is mandatory for new local-app entrypoints. Deferred/unknown task requests are denied. Fake web arguments, approval flags or synthetic receipts cannot turn local GO true; owner acceptance must be independently observed and source-reviewed.

Enforcement scope: the new Local V1 UI and the priority CLI invoke require_local_work(). This does not claim a host-wide Git permission change, repository branch protection, or control of all legacy scripts. Existing collector and Windows scheduler are deliberately not modified.

## One-command real local product entrypoint

Run on owner Windows PowerShell:

    & D:\UCIE\scripts\start_ucie_local_v1.ps1

The foreground app uses the existing UCIE venv and localhost only.
The launcher now **automatically selects a free local port** and opens
the actual product URL in the browser (for example,
http://127.0.0.1:<assigned-port>/local). Do NOT manually open the old fixed
http://127.0.0.1:8767/local URL: another service may already own that port and
return JSON such as {"error":"NOT_FOUND"}. If the browser does not open, copy
the exact `local_app_url` value printed by the UCIE Python process. Verify
`/local/health` on the same assigned port: the schema must be
`UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01`. Ctrl+C stops UCIE Local V1.
This does NOT stop or modify any process already using port 8767.
There is no cloud, customer code or other-project scan, Windows service
installation, privileged deployment or unreviewed code execution.

Four real user paths:
- /local/error : user query -> existing UCIE public evidence -> original URL/version/unverified state -> UCIE safe manual guidance and regression test PLAN (not applied patch).
- /local/engine : choose one of three implemented first-party algorithms -> execute bounded calculation -> show actual numerical result and its synthetic workload limitation.
- /local/books : search the two existing human-readable SkillBooks -> navigate actual chapter/machine contract and official source -> preserve draft/unapproved/export-disabled state.
- /local/evolution : read existing genuine UCIE-only public miner ledger inventory and indexed change candidates -> original source, unverified state and next manual review action. No automatic promotion.
The existing /catalog read-only browser remains accessible in the same local app.

## Release acceptance: all six mandatory

LG1: owner starts one app and navigates all routes on D:\UCIE.
LG2: four meaningful real operator workflows from public-only evidence and first-party code, including negative/missing-data cases.
LG3: exact public provenance/version/limitations, no invented approvals.
LG4: stop/restart/offline existing-data usage and fail-closed errors.
LG5: strictly UCIE only; no private/customer/other-project reads, no scheduler, miner or automatic promotion changes.
LG6: actual owner-host user walkthrough with a reproducible sanitized receipt.

Status is LOCAL_V1_OWNER_ACCEPTANCE_PENDING. Running tests or executing a synthetic recipe is not full owner-operated Local V1 GO; online/customer release is separately NO_GO.

Scope-targeted tests: tests/test_ucie_local_v1_product_v01.py (priority deny, UI route, genuine existing first-party recipe and public evidence contracts), tests/test_ucie_local_v1_owner_readonly_smoke_v01.py (exact-owner live UCIE public read, skipped elsewhere). Existing owner worktree must be preserved; no git reset, clean or mass-stage. Daily 09:00 report remains PAUSED.

Authoritative issue: https://github.com/tmdrkdtn1-project/UCIE/issues/199
