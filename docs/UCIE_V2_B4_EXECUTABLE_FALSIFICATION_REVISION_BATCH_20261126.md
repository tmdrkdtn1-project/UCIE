# UCIE V2 B4 — executable falsification → revision → original asset batch

Parent: PR #392 exact verified SHA `55f56e53f0bcc6a12dc90d550b5b304147291146` (GitHub Actions #45803571676: Ubuntu/Windows × Python 3.13/3.15 success on that prior SHA).

## One coherent B4 vertical feature

1. **Evidence intake**: W01/W02 approved registry and candidate contract. Inputs are two fixed UCIE-owned metadata fixture records linked to the exact PowerShell #28087 merge and Python #153462 merge references. The Python fixture's `a*64` evidence digest is an explicitly synthetic placeholder, NOT authenticated source material.
2. **Annotation**: existing B4 typed annotation comparer preserves version scope, distinct technology owners, preconditions and negative controls. Proposal status is review-only, never technical fact.
3. **Executable first-party trial**: six harmless string inputs: two exact positive versions, two prefix-spoof negative cases, and two unchanged controls. UCIE's intentionally weak baseline uses prefix acceptance; the first-party challenger validates exact numeric version tokens. This tests *only this original toy algorithm* and never launches real PowerShell, Python SDK, customer code, upstream source or networking.
4. **Quantitative comparison**: for the six fixed first-party cases, the expected executable result is baseline 4/6 correct, challenger 6/6; baseline 2 false accepts, challenger 0; unchanged controls unaffected. This is not an external benchmark, customer accuracy estimate, SDK compatibility finding, or evidence of a deployed correction.
5. **Revision disposition**: if the paired comparison truly improves under unchanged controls, produce `PROPOSE_REVISION_FOR_INDEPENDENT_REVIEW` with affected-only retest IDs and retained negative lessons. Never change canonical SkillBooks/rules.
6. **Original assets**: Korean readable SkillBook draft + inert, machine-readable exact-version comparison engine contract with explicit input/output/negative tests, no runtime activation or export permission.
7. **Lineage**: reproducible SHA-256 receipts and bounded, in-memory, hash-linked, idempotent revision history. No operating DB write or new scheduler.

## Limits and required next gates

The trial makes no claim about upstream patches, actual environment behavior, current-version availability, independent QA, license rights, commercial release, customer code, training, or autonomous semantic discovery. W02 source approval is not source-revision authentication; annotation provenance is still first-party draft. A further separate controlled native trial and reviewer/rights decision would be required to promote any asset.

Only UCIE files are modified. Locked V04, operating database, source collector, owner Windows scheduler, signed rules, host services, and private-customer distribution are untouched.

## Reproduction

```bash
python -m unittest discover -s tests -p 'test_ucie_v2_b4_falsification_revision_batch_v01.py' -v
python -m unittest discover -s tests -p 'test_ucie_v2_b4_typed_mechanism_annotation_v01.py' -v
python -m unittest discover -s tests -v
```

**Exact-head CI must be run separately:** historical 4-environment success from PR #392 does NOT validate the new commit. No independent QA or owner-host acceptance is claimed by a green GitHub run.
