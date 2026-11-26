# UCIE V2 B5 paired-control milestone — review only

Date: 2026-11-26 KST. Scope: PROJECT=UCIE, workroom=UCIE integrated development. Starting restore reference: parent PR #359 HEAD `266857243c9f5c1e8241f123e138556b449c2c88`. Current parent is a *Draft* stacked on #358, and **not** production main. Current actual main had Actions cost change `98a3b5b08b466c2f0ae897c039df0719f94f98d6`; it did not merge the V2 PR stack.

## Defect prevented and product-relevant implementation

Previous B5 synthetic comparison summarized each method in isolation. If one synthetic participant had a baseline row but lacked a matching row in `GENERAL_TOOL` or `UCIE_V2_REVIEW_ONLY`, the method-specific aggregate could still be produced without explicit completeness of a paired comparison. Never derive real product advantage from those group averages.

New `src/ucie_miner/ucie_v2_b5_paired_controls_v01.py` calls the **existing** authoritative schema validator, rejects unknown names/PII/real-human claims/duplicate rows via that validator, then requires each synthetic subject to have all three comparison methods before computing intra-subject differences. Missing comparators and empty samples become `HOLD`, not valid comparisons. Negative safety regressions and false version/rights claims are separately counted. Even complete synthetic pairs remain **only synthetic report shaping**, with all claims of human effectiveness, competitive lead, buyer willingness and customer release false.

`tests/test_ucie_v2_b5_paired_controls_v01.py` tests paired positive, incomplete/empty HOLD, duplicate, unsupported real origin, extra PII, overclaim/safety regression, cohort mismatch, two-cohort samples, and impossible synthetic speed advantage.

## Recovery and ACG use

- ACG integrated skill is an operating discipline, **not a background auto-hook**.
- Separate scoped recovery point: parent PR #359 `2668572...`; separate new development branch `feature/ucie-v2-b5-paired-control-evidence-20261126`. GitHub branch is a remote committed ref; there is **no claim** of a local clean Windows owner-tree ACG snapshot or recovery of uncommitted data.
- Pre-publish isolation: source tests in disposable assistant Python with a **locally transcribed B5 validator mirror**, 10/10 PASS. This is not a test against the full actual upstream implementation. Source exact-head GitHub CI and review are independent, still necessary.
- No new scheduled Actions, no local owner Git ref/Windows/SQLite/task changes, no UCIE worker or live V04 route, no network-driven code execution, no real person data, no new source list, no B6 release.
- Open at most one Draft review PR after cohesive source+test+document commit batch. Existing default Draft PR stage1 may run one Ubuntu/Python3.15 job; this costs runner time, so avoid repeated micro-commits. Full `ucie-full-ci` label and relevant native checks only at final owner-approved milestone.

## Evidence limits and next gate

This review is a bounded B5 correctness contract, not a real human evaluation. Need actual separately owner-authorized first-use studies, consent and ethics, independent comparative protocol checks, exact source/run/runner provenance, genuine buyer interviews, Windows owner Edge and B6 rights to make market/buyer claims. No fabricated user samples.

Acceptance requires source SHA-pinned original B5 regression and 4-platform final test on **this exact new head**; no treating parent's green CI as inherited PASS. Keep B0-B6 and four product pillars unchanged.

STATUS: SOURCE_REVIEW_ONLY; NO_HUMAN_B5; NO_AUTO_RELEASE; NO_OWNER_HOST_CHANGES.
