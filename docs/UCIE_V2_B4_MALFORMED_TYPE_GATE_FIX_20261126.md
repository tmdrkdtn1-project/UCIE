# UCIE V2 B4: malformed-input validation repair (2026-11-26)

Parent: Draft PR #390 at `a233f6dd5f282cdfe9126ced050e4789f7404346`.

## Focused review outcome
The earlier source-bound composer and hypothesis history validated allowable values but performed membership checks before checking the types of some fields. A malformed unhashable `source_id` or `claim_code` could consequently raise Python `TypeError` rather than their documented `MultiSourceError` or `EvolutionError`. This is an error-boundary weakness, **not** proof of production exploitation.

Updates:
- Require exact-string source ID, technology and review origin before lookups in the source-backed comparison layer.
- Require exact types for revision event claim/source/reason/pin/decision, affected concept list and boolean retest flag before hash/membership checks.
- Four negative regression methods targeting malformed source IDs, technology object, claim list and bool/int impersonation.

## Reproducibility and limits
```bash
python -m unittest discover -s tests -p 'test_ucie_v2_b4_multisource_hypothesis_v01.py' -v
python -m unittest discover -s tests -p 'test_ucie_v2_transfer_knowledge_evolution_v01.py' -v
python -m unittest discover -s tests -p 'test_ucie_v2_b4_fourth_technology_bridge_v01.py' -v
python -m unittest discover -s tests -p 'test_ucie_v2_b4_w02_evidence_intake_gate_v01.py' -v
```
No executable source fetched in this workroom. The container could not resolve GitHub DNS for a checkout. GitHub Actions on prior Draft branches was skipped; this branch's exact-HEAD test results are not yet verified. Keep the PR Draft. No V04, operating database, scheduled jobs, original Windows checkout, signed rules, customer intake, auto-promotion, model training or commercial release changed.
