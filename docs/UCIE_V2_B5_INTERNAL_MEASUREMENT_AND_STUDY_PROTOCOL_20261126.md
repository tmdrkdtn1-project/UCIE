# UCIE V2 B5 — 실측 준비·내부 증거 검증 묶음 (검토 전용)

- Date: 2026-11-26 KST
- Project: **UCIE ONLY**
- Status: **FIRST_PARTY_INTERNAL_BENCHMARK_IMPLEMENTED; ACTUAL_HUMAN_AND_COMMERCIAL_STUDY_PENDING**
- Parent: B4 Draft PR #354, whose pinned HEAD was \`cc73e1f8567eaf1d02f28492c4d455dca8edd870\` before this PR. B3/B4 source/QA is not operating authorization.
- Approved design: Draft PR #351, B0→B6 from UCIE V2 product engineering Skill, with four equal pillars and Virtual Library reprocessing/generalization central.

## A. What is now implemented

1. \`ucie_v2_b5_internal_probe_v01.py\` executes **actual UCIE-first-party review code**, not mock JSON: existing synthetic MCP issue/control, B1 pinned Capsule and UNKNOWN/HOLD, B2 generated HTML from same Capsule, B3 no-change graph and zero proposed unrelated retests, B4 source-linked hypothesis, positive/negative/control synthetic transfer and original chapter. It measures per-cycle **wall clock, CPU process time and Python \`tracemalloc\` peak**. It checks truth/rights/independent QA/export/version/case/lineage on every repeat.
2. \`ucie_v2_b5_comparison_contract_v01.py\` locks one case \`mcp-prompts\`, three **comparators** (official docs, general tool, UCIE), two **user groups** (first-time coder and technical reviewer), target metrics, sample ranges, and a strict no-free-text/no-PII **synthetic-only** aggregation parser for dry runs.
3. Regression tests cover actual internal module linkage, request/version/rights hold, false CI/SDK/QA and price claims, resource profile claims, unauthorised observations, boolean-as-int forgery, duplicate rows, PII, oversized records, unsupported methods, subject/cohort mismatch and explicit false customer benchmark.
4. \`scripts/ucie_v2_b5_disposable_probe.py\`: manual one-shot JSON receipt, no network, no saved file, no service or scheduler. Run ONLY in an isolated checkout.

## B. Reproduce on an isolated first-party UCIE checkout

\`\`\`sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -B -m unittest tests.test_ucie_v2_b5_internal_probe_v01 tests.test_ucie_v2_b5_comparison_contract_v01 -v
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -B scripts/ucie_v2_b5_disposable_probe.py
\`\`\`

The broader GitHub offline workflow runs \`python -m unittest discover -s tests -v\` on Linux/Windows Python 3.13/3.15 on this PR's exact source. CI result must be checked after final commit; no PASS may be carried forward from ancestor PRs. Timing and peak traced Python allocations are runner-dependent and **NOT** whole-host RAM, GPU, operating cost, human task time, speedup over docs, or statistically validated business value.

## C. Baseline and human study gates still open

Future owner-authorized, opt-in actual user studies must compare the **same task** using (a) official documentation, (b) ordinary tools where appropriate, (c) UCIE; record correct safe next step, accurate version/rights limitation, evidence found, first-action time, overclaims, relative revalidation cost and documentation comprehension. First-time coders proposed 5–8, technical reviewers 2–3. Separately interview 5–10 prospective *buyers* for willingness/rights/install barriers. These are **targets only, not observed sample size**. Real recruiting, consent, anonymized protected record storage/retention, native Windows Edge, competitor access, independent QA and owner UI acceptance all require separate work and authorization.

Do not use the synthetic parser to claim buyer interviews or market acceptance. It deliberately rejects \`OWNER_AUTHORIZED_HUMAN\` rows to prevent user-provided labels from becoming false proof. Actual human data require a separately approved ingestion/consent/review contract; none implemented here.

## D. Safety and scope

- No new \`/local/ask\` POST, endpoint, upload, external AI, source collection, arbitrary command execution, Windows task, SQLite migration, customer data acquisition or service restart.
- V04 Premium Dark/owner dirty checkout, main, historical signed Rulepacks, operating DB and Tunnel C40 unchanged.
- No model-weight training, automatic generalization to unknown sources, auto-promotion, publishing, distribution, signing or commercial release.
- The comparison contract **defines** future measurement; only disposable internal CPU/wall/Python-memory workload is measured now. False confidence count 0 in this controlled contract is **not** a real-user false confidence estimate.
- B4 still remains **bounded first-party structured inference**, not full open-domain autonomous reasoning, and must retain negative lessons, source lineage, version and rights gates.
- Owner Windows Edge QA, first-use observer study, technical independent QA and actual licensed recipient acceptance stay **NO-GO** until separately evidenced.

## E. Acceptance distinction

| Layer | Current proof |
|---|---|
| UCIE Skill rules | Structural-only; not Windows enforcement |
| B1-B4 source modules | CI on each exact Draft PR head (separately verify) |
| B5 standalone internal resource+truth checker | New code and tests; this PR exact-head CI gate required |
| B5 real human task, buyer willingness, external comparisons | **NOT PERFORMED** |
| Owner V04 and customer release | **NO-GO** |
