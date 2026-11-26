# UCIE V2 genuinely connected iterative review-only learning cycle

UCIE-only stacked Draft on PR #375 exact head 5e6b7634ceb9393789f9db387bd5a4924948f2ee.

The owner-approved Virtual Library purpose is cumulative knowledge reprocessing and falsifiable generalization. Earlier V2 modules already existed for original SkillBook source lineage, bounded paired synthetic candidate comparison, original hypothesis revision, review history, and generating next drafts from accumulated history. This milestone JOINs them as a single Python entrypoint:
`advance_virtual_library_review_cycle(source_history,feedback_registry,revision_history,before_fixtures,after_fixtures,fixture_sha256=...,expected_revision_head_sha256=...)`

1. Validate exact SHA-pinned original history, review-only feedback and expected previous review head; fail closed on stale.
2. Build prior next candidate generation from previous review history.
3. Compare paired first-party synthetic fixtures on SAME IDs/source/truth/baseline; ONLY challenger prediction may differ. This is supplied synthetic observation, not execution of generated code.
4. Append the actual validated revision report to the existing bounded review history. Exact repeat dedupes and does not increase learning count.
5. Rerun next-generation hypothesis factory on the NEW history; previous revision and negative lessons now materially change the next drafts. Produce per-candidate original human-readable SkillBook *addenda* with before/after draft hashes, explicit privacy counterexample, review status and required test direction. Addenda are not actual modifications to signed SkillBooks.
6. Return a deterministic full SHA-pinned receipt and updated in-memory history, preserving original source, version, failed hypotheses, old source HOLD, and isolated release/rights gates.

12 regression tests: actual new generation, replay dedupe, second changed iteration, stale head, forged approval, changed ground truth, wrong fixture SHA, cross-candidate leakage, unresolved source HOLD, input immutability, deterministic hashes and non-adoption. No scheduler, disk, DB, network, customer/private data or model training. Owner Windows local dirty worktree, SQLite, V04, ACG task, signed packs untouched. The prior PR #375 4/4 full CI run 45785851171 completed SUCCESS for exact parent HEAD; separate exact-head four-lane CI needed for this change.
