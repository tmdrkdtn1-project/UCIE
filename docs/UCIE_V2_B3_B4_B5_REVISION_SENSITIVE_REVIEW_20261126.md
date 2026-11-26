# UCIE V2 B3-B4-B5 revision-sensitive evidence review (2026-11-26)

UCIE V2 review-only stacked development; parent B5 PR #362 HEAD 3532da7a86e5eb4eaf383033fc21427ae6b3839a. 
Canonical first-party source analysis: B3 source/asset graph in `ucie_v2_revision_impact_v01.py`; B4 source-pinned two-SkillBook hypothesis and third MCP synthetic control in `ucie_v2_generalization_transfer_v01.py`; B5 three-arm paired synthetic controls and source join in `ucie_v2_b5_b4_evidence_join_v01.py`.

## Previously missing correctness boundary
A B5 synthetic trial could be linked to source SHA and bounded B4 hypothesis but its fitness under a NEW upstream revision had not been invalidated. A revision signal (unverified candidate hash, never an authenticated update) must HOLD the existing trial when it can affect the Python/Git SkillBook/principle or MCP capsule target. Unchanged pins and unlinked approved-source signals should not force a blanket retest.

## Implemented scoped engine
`review_revision_sensitive_study(records,signals)` reuses existing strict contracts. Original B5 observations are synthetic-only. B3 validates exact approved source IDs, prior pinned SHA, candidate format and dependency closure. B4 plan identifies the affected hypothesis and exact review tests; B5 result attaches the original hypothesis/capsule/source SHA and retest proposal. Any relevant changed candidate produces `SOURCE_CHANGE_CANDIDATE_HOLD_PAIRED_STUDY_STALE`; missing paired arms produce separate HOLD. No test runs/scheduling/remote GET/worker mutation/production rule adoption.

New targeted negative tests cover changed Python/Git/MCP sources, missing arms, duplicate affected tests, forged source SHA, unapproved repo, PII, forged hypothesis and false approval. No claimed real human study, competitor superiority, rights approval, automatic model training, native Edge UAT, owner Windows release or general-purpose semantic reasoning.

## Scope and gates
Single new source, test, document files on isolated Draft PR. GitHub ACG skip on ordinary Draft, explicit exact-head final four job checkpoint only. Original dirty owner D:\UCIE, operating SQLite, task scheduler, C40/Tunnel, V04, signed rulepacks and other projects untouched.
