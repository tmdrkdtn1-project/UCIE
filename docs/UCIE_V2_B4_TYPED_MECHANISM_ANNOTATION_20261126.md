# UCIE V2 B4: typed W02 mechanism annotation comparison

Parent verified CI: PR #391 HEAD `22a8a04647947776dba4928c85cce5a967e84651`, run #45802408652, Windows/Ubuntu 3.13/3.15 all succeeded. This is prior-HEAD evidence, not a result for this change.

## Implementation

The new `compare_draft_annotations` receives public metadata through **existing W01/W02 intake HOLD gate**, then checks a bounded list of explicitly first-party review-only mechanism annotations. It rejects unexpected fields, mismatched library item/digest, forged approval, duplicate annotations, unknown mechanisms, missing counterexamples, and mutable external text.

Each annotation is stored in a normalized in-memory result with source/version provenance, preconditions and negative examples. The comparator groups annotations by explicit mechanism, requiring **two different approved technology owners**, not merely two PRs or a repo and a doc from the same owner, before creating a provisional *test proposal*. It does not auto-classify arbitrary source text. Every such proposal is REVIEW_ONLY_TEST_PROPOSAL_NOT_TECHNICAL_FACT, with positive/negative/unchanged-control contracts marked not executed. All new W02 records remain unreviewed until explicitly annotated; neither these draft annotations nor purpose-code matches are authenticated technical proof.

- Code: `src/ucie_miner/ucie_v2_b4_typed_mechanism_annotation_v01.py`
- Tests: `tests/test_ucie_v2_b4_typed_mechanism_annotation_v01.py`
- Reproduction: `python -m unittest discover -s tests -p 'test_ucie_v2_b4_typed_mechanism_annotation_v01.py' -v`

No operating DB, owner V04, scheduler, rulepack, source registry, collector, model weights, private data, automatic approval/signing, or customer distribution touched. Stage B4's genuine next acceptance is independently authenticated source revision + UCIE-authored positive/negative native trials + reviewer/rights decision, all separate.
