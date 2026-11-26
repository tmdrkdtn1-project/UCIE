# UCIE V2 Feedback Registry and Affected-Only Experiment Triage (2026-11-26)

UCIE-only source development stacked after Draft #369 exact parent `3aed60f05619cd6159d284198608d16d1fcb5972`. Distinct from operating SQLite, source miner, owner Windows scheduled snapshot, V04 Local and any customer data.

This milestone integrates original SHA-pinned Virtual Library history, original paired candidate proposals, first-party synthetic 3-control feedback and duplicate-aware iteration. The new `ucie_v2_feedback_registry_v01.py` returns a detached, append-only hash-linked **review registry** in memory. Each receipt includes source history head, candidate IDs and SHA, exact feedback cycle and iteration digests, bounded test names and review decisions. Exact repeats are deduped, old events kept without rewriting and chained digest validated.

Candidate review decisions:
- `HOLD_SOURCE_REVISION`: earlier approved-source change signal unresolved; 3 synthetic fixture matches do not clear it.
- `HOLD_INCOMPLETE_PAIRED_EVIDENCE`: missing paired B5 observation.
- `REJECT_SYNTHETIC_CONTROL_FAILURE`: contract control results mismatch and cannot support the intended hypothesis.
- `REVISE_REVIEW_ONLY_OUTPUT_GUARD`: synthetic controls match, but privacy/output-specific exclusions must be preserved; not a production adaptation.
- `REVIEW_CANDIDATE_SYNTHETIC_NOT_INDEPENDENT`: bounded synthetic match, still awaiting independent upstream/owner QA.
- `HOLD_PREVIEW_NOT_TESTED`: no actual synthetic fixture was executed.

`prioritize_review_experiments` deterministically sorts review tasks from current candidate decisions, with priority 1 for unresolved source-change HOLD, priority 2 for failed or incomplete controls, priority 3 for ordinary review and counterexamples. These priorities and test names are *proposals* only, not job dispatch. No automatic schedule, deployment, user code execution, write to owner disk, rights approval, signed rule pack adoption or training.

This registry is review-only **in-memory**; its hash chain is not a cryptographic signature or full provenance proof. History still requires source approval and independent tests. The original scratch-store supports only its original asset history schema; it is NOT silently repurposed for feedback records. If persistent feedback storage is later approved it needs a separately verified repository/lock.

Includes targeted first-party tests for clean/incomplete/source HOLD, real opt-in 3 UCIE synthetic fixtures, preview, duplicate, cross-history forgery, tampering, mismatched iteration, fake control, and non-mutation. GitHub Actions Draft default skip is not PASS; exact-head matrix acceptance is separate.
