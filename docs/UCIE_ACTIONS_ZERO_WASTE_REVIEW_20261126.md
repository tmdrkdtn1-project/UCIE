# UCIE Actions Zero-Waste — Isolated Review 2026-11-26

PROJECT: UCIE only. Main f5fbaca6c94f50130941570090c2c555cf92d816; V2 draft PR #359 266857243c9f5c1e8241f123e138556b449c2c88. Owner product baseline and four pillars unchanged.

## Financial fact
Owner Billing Usage by repository for this month: UCIE gross USD 97.46. Owner confirms Actions is the budgeted product. Gross is not net invoice. Aim to reduce measured UCIE Actions gross usage at least 70% relative to comparable change mix; this is a TARGET not an achieved saving. Verify exact billing SKU, rate, premium runner, gross/net, storage and actual minutes in future owner-provided billing evidence.

## The radical change: drastically lower cloud execution frequency

Current UCIE has 12 workflows on V2 draft head. stage1-offline-tests.yml runs Windows and Ubuntu by Python 3.13 and 3.15 on EVERY PR and main push. Dedicated Chromium, Edge, PowerShell and MCP workflows can also run when their changed path filters match. Repeated commits to a draft therefore fan out into many jobs.

**L0 — everyday development: no automatic full GitHub Actions**. Run bounded UCIE-only first-party offline checks on isolated developer sources. The operating dirty owner Windows checkout is NOT a test sandbox. Source-only local tests cannot claim GitHub CI or production PASS.

**L1 — explicit milestone PR validation**. One stable routing/status entrypoint. Documentation-only and low-risk changes use one focused Python3.15 source check. Any core/security/rights/provenance/unknown/requirements/CI infrastructure change requires four-platform offline matrix. Relevant browser/PowerShell/MCP changes preserve the dedicated native tests. A skipped or pending required check cannot be relabeled PASS; first verify branch protection before changing any event trigger. Consolidate commits before a bounded validation run.

**L2 — full final acceptance**. For EVERY actual merge/release candidate on the exact final HEAD, require Windows/Ubuntu by Python3.13/3.15 and all relevant native browser/PowerShell/MCP checks, plus independently protected source/owner/license/release gates. No automatic customer release. Owner Edge Windows UAT remains separate. A green early fast check is NOT L2 readiness.

## Four-stage safe transition

1. Inventory all 12 workflow trigger paths/jobs, branch-protection check names, permissions, and rollback SHA. Identify duplicated jobs and exact required status dependencies.
2. Unit-test deterministic typed router on UCIE-authored inputs: paths normalization, CI edits -> full check, high-risk -> 4 environments, browser/PowerShell/MCP -> native tests, unknown/forged paths -> fail closed, release/owner permission false.
3. Build a shadow-mode centralized orchestration workflow. Keep legacy workflows while comparing *one bounded test head*, not indefinite parallel double charging. Keep required status names or intentionally reviewed branch-protection migration; never skip an entire required workflow with paths-ignore.
4. After exact-HEAD comparison passes, propose disabling redundant automatic PR triggers in selected legacy workflows, moving these to manual or reusable dispatch; no automatic application until separate owner approval and activation gate. PR cancellation by exact PR only, never cancel main, release, approval. Minimize caches and artifacts without losing necessary screenshot/native evidence.

## Measurement & safeguards

Measure paid Actions gross amount, SKU, billed and total runner minutes, job counts, repeat attempts, artifact storage and independent gate coverage on the same work mix. Goal: 70%-90% lower CI trigger overhead where repeated draft activity dominates; actual savings UNKNOWN until Billing comparison.

Keep all current V04 routes/CSP, owner dirty Windows, SQLite, scheduled tasks, C40/Tunnel, signed rules, authorized public source allowlist, source rights, virtual-library eight-stage pipeline and B6 designated-customer release policy unchanged. No new public source, customer code, model training, auto-promotion, signing or deployment.

The review branch intentionally opens NO PR and adds NO active workflow: otherwise the existing automatic PR matrix would execute immediately. Local classifier offline prototype and 14 regressions verified only in the isolated assistant container; not yet committed as a CI-verified UCIE runtime source.

TRACKING https://github.com/tmdrkdtn1-project/UCIE/issues/360
STATUS: REVIEW_ONLY. NO_TRIGGER_CHANGE. NO_SAVINGS_CLAIM. NO_OWNER_HOST_MUTATION.
