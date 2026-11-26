# UCIE V2 revised hypothesis review-only feedback ledger

Part of stacked Draft based on PR #373 exact commit a54579238f7e444ef2f9612f3790bb94759bc4de; source-only.

A separate in-memory history stores SHA-pinned original hypothesis revision/retest reports with append-only hash chain, exact source history identity, duplicate suppression, cap 32 and signed/owner/QA flags forcibly false. This explicitly distinguishes *revision proposal recorded* from *validated new technical principle*.

`review_revision_lessons` provides an inspectable record of rejected synthetic challenger, retained draft, revised draft and HOLD with original cross-source privacy counterexample; does not write training data, update operating rulepacks or schedule tests. Full review report and its child candidate SHAs must remain unchanged. A local unsigned hash chain detects accidental alteration, not adversarial signed provenance.

Regression cases validate append, duplicate, replay against another history, forged approval, altered candidate verdict, no source mutation and no auto-training.
