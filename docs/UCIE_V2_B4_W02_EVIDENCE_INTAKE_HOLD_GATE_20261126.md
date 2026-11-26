# UCIE V2 B4: W01/W02 public-evidence intake HOLD gate

**Parent**: PR #389, SHA `ba18a8d614c0ecc4f55756fa902136ef020aef1d`.

This adds a bounded **generic intake adapter** for existing W02 public Library candidates, separate from the tightly curated B4 mechanism composer.

## Implemented

- `triage_w02_evidence(records)`: validates up to 24 records with the **existing** `build_library_entry()` W02 contract and approved W01 registry. It does not fetch content or enable a new endpoint. Duplicate exact records are counted once, conflicting source/revision hashes or hidden version conflicts are rejected.
- Every incoming approved but not semantically reviewed candidate has `HOLD_MECHANISM_NOT_REVIEWED`, zero accepted hypotheses, and explicit missing gates for source revision authentication, mechanism/counterexample annotation, first-party test, independent QA and rights/release.
- Matching purpose codes across multiple distinct sources is only `SAME_PURPOSE_NOT_MECHANISM_PROOF`, not validation of a common technical principle.
- `combined_curated_and_unreviewed` returns a **separated** view: the existing four-technology curated review may contain bounded proposals while newly supplied W02 items remain HOLD; it never promotes unreviewed records automatically.
- 14 first-party test methods cover validated public metadata, duplicate/revision/version conflicts, unapproved sources, forged approval/QA, order determinism, over-budget input, and no I/O.

## Important limits

A registry-approved public source is not an authenticated exact revision, technical assertion, license grant, rights signoff or independent QA. W02 `evidence_sha256` is treated as unverified metadata until independently authenticated. This change does **not** semantically process arbitrary public source text or discover mechanisms autonomously; that would require a separately curated, testable mechanism annotation layer with a source/reviewer trust gate. No raw untrusted source text is executed, copied into a prompt, or imported from private repositories.

## Verification

Code committed in Draft; no exact-head PASS asserted. Test command on an authorized isolated UCIE checkout:

```bash
python -m unittest discover -s tests -p 'test_ucie_v2_b4_w02_evidence_intake_gate_v01.py' -v
python -m unittest discover -s tests -p 'test_ucie_v2_b4_fourth_technology_bridge_v01.py' -v
python -m unittest discover -s tests -p 'test_ucie_v2_b4_multisource_hypothesis_v01.py' -v
```

No mutation of V04, live DB, owner Windows scheduler, signing, deployed services, existing source registry, source collectors, model weights or commercial release. No customer/project corpus access. Keep Draft and unmerged until exact-head CI and owner-host acceptance are separately evidenced.
