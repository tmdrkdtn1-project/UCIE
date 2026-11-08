# UCIE LOCAL V1 - HARD-CODED OWNER EXECUTION CONTRACT

Owner decision: 2026-11-08. Executable contract: src/ucie_miner/local_v1_priority_v01.py.

## Strict development order

1. LOCAL PRODUCT: owner-accepted on 2026-11-08 after L1 browser, L2 four functional tasks and L3 restart/offline/bad-input checks. The local-only signoff is recorded in docs/UCIE_LOCAL_V1_OWNER_ACCEPTANCE_20261108.md.
2. LOCAL AUTO-START + DATA MATURITY (CURRENT): preserve the accepted Local V1 as an auto-started owner-only localhost tool; continue already allowlisted public evidence collection, provenance/version verification and regression quality. No new paid hosting or customer publication while evidence is immature. Autostart guide: docs/UCIE_LOCAL_V1_WINDOWS_AUTOSTART_20261108.md.
3. ONLINE + DESIGNATED CUSTOMER DELIVERY (DEFERRED): customer hosting, licensing/signature, domain, public Cloudflare routes, independent security/SBOM/rights and pilot require a separate source-reviewed owner decision AFTER data maturity. The existing O1 hosting preparation source is dormant.
4. PERIPHERAL/EXPANSION (LAST, remains blocked): additional collectors, scheduler refactors, dashboards/platforms/skills, performance improvements and optional proof systems require their own priority decision.

Existing Local V1 tasks remain allowed after actual owner signoff. Source-coded LOCAL_WORK dispatch remains fail-closed for online launch, customer distribution and peripheral work until an independent approved change is made. Deferred/unknown task requests are denied. Fake web arguments, approval flags or synthetic receipts cannot turn local GO true; owner acceptance must be independently observed and source-reviewed.

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
- /local/library : unified search of W04 public source candidates, editorial drafts and two human/machine SkillBooks; the existing /local/books bookmark redirects here. User can invoke only the two existing UCIE-authored disposable/static SkillBook demos via /local/skillbook-run, preserving each book's draft/unapproved/export-disabled state.
- /local/evolution : read existing genuine UCIE-only public miner ledger inventory and indexed change candidates -> original source, unverified state and next manual review action. No automatic promotion.
The existing /catalog read-only browser remains accessible in the same local app.

## Release acceptance: all six mandatory

LG1: owner starts one app and navigates all routes on D:\UCIE.
LG2: four meaningful real operator workflows from public-only evidence and first-party code, including negative/missing-data cases.
LG3: exact public provenance/version/limitations, no invented approvals.
LG4: stop/restart/offline existing-data usage and fail-closed errors.
LG5: strictly UCIE only; no private/customer/other-project reads, no scheduler, miner or automatic promotion changes.
LG6: actual owner-host user walkthrough with a reproducible sanitized receipt.

Status: UCIE_LOCAL_V1_OWNER_ACCEPTED_GO on 2026-11-08, by explicit owner decision (see docs/UCIE_LOCAL_V1_OWNER_ACCEPTANCE_20261108.md and GitHub issue #199). The owner's acceptance is for the local operator product and does not individually approve unverified public candidates, drafted SkillBooks, real-project scanning, external security QA, online/customer release or any other-project access. Commercial/customer release remains NO_GO.

Scope-targeted tests: tests/test_ucie_local_v1_product_v01.py (priority deny, UI route, genuine existing first-party recipe and public evidence contracts), tests/test_ucie_local_v1_owner_readonly_smoke_v01.py (exact-owner live UCIE public read, skipped elsewhere). Existing owner worktree must be preserved; no git reset, clean or mass-stage. Daily 09:00 report remains PAUSED.

Authoritative issue: https://github.com/tmdrkdtn1-project/UCIE/issues/199
