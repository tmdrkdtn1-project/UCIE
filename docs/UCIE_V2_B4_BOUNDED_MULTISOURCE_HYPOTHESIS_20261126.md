# UCIE B4: bounded cross-source mechanism hypothesis composer (2026-11-26)

**Upstream:** PR #387, pinned SHA `69742a5dfe215ceed63747e79da7b66c2b4f7527`.

Implemented in `src/ucie_miner/ucie_v2_b4_multisource_hypothesis_v01.py` with 13 regression methods. This is an **additive, in-memory, UCIE-first-party review-only** consumer of the existing three source pins, not a general free-form text inference model.

## What actually runs

- Normalize 2–12 explicitly curated, source-pinned records into typed mechanism and counterexample vocabularies. Exactly three existing source-backed example records are currently eligible; unknown or fabricated entries are rejected even if their source string matches an approved repository.
- Compare mechanisms across at least **two distinct technologies**. A hypothesis is proposed only when each required mechanism is supported by two distinct technology records.
- Build `BOUNDED_SCOPE_BUDGET` and `OUTPUT_CONTRACT_VALIDATION` review candidates on existing Python/Git/MCP evidence. Put `VERSION_PINNED_TRIAL` on HOLD, since the currently available bounded records support this specific mechanism only from MCP.
- Retain explicit negative-control codes and per-hypothesis source pins; create UCIE-original Korean SkillBook draft text and an inert machine test contract.
- Refuse unknown mechanisms, data-source substitution, altered digests, fake record IDs, unsupported additional fields and omitted curated counterexamples.

## Limitations and next genuine scope increase

This does **not** accept arbitrary public documents or discover semantic mechanisms autonomously. New validated source records need separate owner-approved ingestion and provenance review before being eligible. Existing source hashes authenticate only fixed metadata references; they do not certify technical accuracy or prove a live SDK version. A machine test contract with `actual_tests_executed=false` is not a successful transfer experiment.

The next step is to connect approved source-registry normalized records to this interface with a rights and reviewer gate; then run independent native/held-out tests and actual measured before/after comparison. Do not silently weaken the current strict record allowlist.

## Reproduction / hold gates

```bash
python -m unittest discover -s tests -p 'test_ucie_v2_b4_multisource_hypothesis_v01.py' -v
```

CI for the exact new HEAD remains PENDING until a real workflow run proves it. The existing original V04, operating SQLite, Windows Task Scheduler, signed rulepacks, customer code, model weights, release and commercial rights remain untouched. No GitHub PR/CI outcome grants owner release approval.
