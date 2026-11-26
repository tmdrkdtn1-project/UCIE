# UCIE V2 candidate-specific measured synthetic evidence prioritization

Scope: UCIE-only Draft stacked on PR #372 exact head ddf314a68c4a8563b8e90e6819cf56c3d56729af. New source `ucie_v2_candidate_evidence_priority_v01.py` is a first-party, in-memory **per-candidate** synthetic evaluation. Neither the older B5 source metrics nor the synthetic MCP controls prove real customer benefit.

## Contract
Each of the two original SHA-pinned hypotheses must have its **own** disjoint case IDs and provenance. Shared cases across hypotheses are blocked: a pooled synthetic improvement must never be attributed to every candidate. Strict fixed input fields; maximum 128 synthetic cases across candidates; per candidate screening threshold minimum 8 observations with >=3 positive and >=3 negative. These thresholds are first-party engineering test-screen rules, **not statistical confidence or B6 acceptance**.

Calculate paired regressions and improvements separately. A single correctly classified baseline case becoming wrong receives priority 1 for review; missing/imbalanced controls receive HOLD priority 2; unresolved source revision is priority 1 regardless of apparent gain, and no synthetic evidence can clear it. Review-only candidate improvements remain priority 3. The output contains each candidate, source history head, feedback registry SHA, exact per-candidate fixture hash, FPR/FNR delta, allowlisted proposed tests and no auto dispatch. No adoption, signature, independent verification, training, native Edge UAT or customer distribution.

Tests: 13 targeted cases for per-candidate regression, partial missing data, zero denominator, unbalanced classes, leakage across candidate case IDs, unknown IDs, non-authorized data fields, SHA mismatch, >128 bound, reproducibility, source HOLD and non-adoption. Original developer owner worktree, operating DB, Task Scheduler, C40, V04 and signed packs are untouched.

Gate: parent PR #372 4-environment CI at run 45784118322 was still in progress when source planning started; do not borrow a pass from parent HEAD. Current Draft needs its exact-head full original CI. Never interpret skipped Draft job as test PASS.
