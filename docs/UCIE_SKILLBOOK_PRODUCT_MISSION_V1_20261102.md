# UCIE canonical product mission: evidence-to-SkillBook (2026-11-02)

- Project/workroom: UCIE / UCIE사업방 (business review); implementation owner: UCIE 통합개발방.
- Status: **PRODUCT CONTRACT / INERT DRAFT MODEL ONLY**. This document is not evidence of a finished skill authoring engine, commercial product, approved distribution, external runtime verification, or autonomous learning.
- Product charter: `docs/ROADMAP.md` and `docs/UCIE_V1_MASTER_ROADMAP_20261027.md`. This specification makes their knowledge **reprocessing and reusable SkillBook production** objective explicit without replacing the existing four equal pillars.

## Non-negotiable purpose

UCIE is **not** primarily a bug-listing service, static analyzer, URL collector, AI-generated summary site, or generic skill marketplace. Its long-term mission is to turn **explicitly approved public technical evidence** and **UCIE-owned, authorized experiments** into independently inspectable, versioned, reusable technical knowledge assets.

Four equal pillars remain:

1. **Coding error prevention**: grounded failure modes, safe calls, version boundaries and regression evidence.
2. **Development/maintenance engine, skill and learning-logic discovery and improvement**: include positive techniques, not only fixes; extract and test generalizable principles.
3. **Categorized, reusable Virtual Library with SkillBooks**: reorganize and combine evidence into task-centered human-readable SkillBooks and machine-consumable, separately approved skills/engines/test recipes. A SkillBook is **a product**, not an index of PRs.
4. **UCIE-owned improvement loop**: compare new evidence and own safe tests, preserve negative results and revision lineage, and improve library assets without ingesting any other project's private experience.

## Mandatory end-to-end SkillBook production pipeline

These IDs are fixed in `src/ucie_miner/product_plan.py` and regression-tested. Each phase is required for the final product; a proof-of-concept may stop earlier and must report its exact status.

1. `APPROVED_PUBLIC_EVIDENCE_INTAKE`: source registry, identity, revision/hash, bounded collection, deduplication.
2. `REPROCESS_AND_GENERALIZE_TECHNICAL_PRINCIPLES`: analyze useful **mechanisms and limitations**, not merely copy or paraphrase upstream instructions. Produce UCIE-authored safe original abstractions, retaining source attribution.
3. `RECLASSIFY_AND_COMPOSE_SKILLBOOK_CHAPTERS`: organize by technical task, precondition, language/runtime/version, applicable scope, related skills, dependencies, and counterexamples; track source-level version lineage.
4. `CREATE_HUMAN_AND_MACHINE_READABLE_ASSETS`: readable SkillBook plus structured skill/engine/test-recipe contracts; formats are distinct and neither is equivalent to a raw prompt.
5. `SAFE_FIRST_PARTY_AND_INDEPENDENT_VERIFICATION`: exercise UCIE-authored benign positive/negative cases, check compatibility and run independently reviewed upstream before/after tests where applicable; report unknown evidence honestly.
6. `HUMAN_RIGHTS_SECURITY_AND_RELEASE_APPROVAL`: independently review license/attribution, misuse risk, provenance, reviewer authority, signing and release scope.
7. `VERSION_PINNED_REUSABLE_DISTRIBUTION`: only approved packages are exportable through independently authorized consumers. No project access or global private telemetry is granted.
8. `UCIE_OWNED_FEEDBACK_AND_REVISION`: capture only authorized UCIE-native test observations; deduplicate, deprecate or revise with evidence and explicit approval.

**Mandatory deliverables** (not necessarily present today): `HUMAN_READABLE_SKILLBOOK`, `MACHINE_READABLE_SKILL_CONTRACT`, `EVIDENCE_VERSION_RIGHTS_MANIFEST`, `POSITIVE_NEGATIVE_TEST_RECIPE`, `UCIE_OWNED_REVISION_HISTORY`.

A candidate count, SHA index, PR list, summarized document, synthetic unit test, or auto-tagged item **must not** be described as a finished SkillBook or a validated reusable skill.

## Taxonomy and proof state

Current candidate types: `PUBLIC_TECHNICAL_EVIDENCE`, `PREVENTION_RULE`, `DEVELOPMENT_ENGINE`, `REUSABLE_SKILL`, `LEARNING_LOGIC`, and `TEST_RECIPE`. `UCIE_EXPERIENCE` is restricted to separately authorized UCIE-owned experiment records, never public-source input or cross-project telemetry.

Every future production asset needs exact evidence links, owner/source/commit, SHA, allowed license and attribution, version/runtime constraints, inputs/outputs, preconditions, dependencies, reproducible tests, negative examples, limitations, reviewer decision, release signature and revision/retraction chain. A public URL or original license file name is **not** legal clearance.

Treat `UNVERIFIED_CANDIDATE_ONLY`, `TESTED_FIRST_PARTY`, `INDEPENDENTLY_VERIFIED`, `OWNER_APPROVED`, and `PUBLISHED` as separate gates. No label is implied by the presence of another. No automatic elevation from collected evidence to approved/signed/executable knowledge.

## First executable implementation slice (this change)

- `src/ucie_miner/skillbook_blueprint.py`: deterministic, in-memory **metadata-only chapter blueprint** from existing `build_library_entry` output. It reconstructs and checks every untrusted candidate against the current source registry; rejects altered approval/export flags, duplicate evidence identities and malformed topics.
- Chapter grouping uses stable types and safe IDs. Returns an evidence-linked draft and **all distribution, QA, generalized-content, model-training and promotion flags false**.
- `src/ucie_miner/product_plan.py` exposes the mandatory pipeline, deliverables and **incomplete** state in its offline preview, and validates that the canonical four pillars and pipeline cannot be silently reduced.
- `AGENTS.md` and `README.md` point to this canonical scope for future coding sessions.
- Tests cover a deterministic draft, shuffled input, source injection, approval forgery, type/integrity bounds, stage removal and absence of unintended side effects.

**Not implemented in this change:** original full chapter writing, cross-source semantic synthesis, actual skill package creation, independent upstream verification, commercial rights clearance, production deployment, autonomous learning/training or additional network crawling.

## Development priority and acceptance

1. Build an **actual UCIE-authored SkillBook chapter** from a bounded subset of already approved public evidence and explicitly separate facts, UCIE's own explanation and unknowns.
2. Independently test the chapter's associated original safe skill/recipe on specified versions, with baseline and negative controls.
3. Generate a portable, version-pinned **draft** for authorized independent testing, then pursue rights/security/owner release review. Draft is not published.
4. Close the loop using only UCIE-owned tests and prove the revised version is better under equivalent workload.

A commercial pilot should separately test: task completion and false positive rates, reproducibility, time saved versus existing free solutions, source traceability, lifecycle maintenance cost, integration effort, 10–20 buyer interviews, and actual paid trial/contract intent. **No paid demand, unique competitive moat, production accuracy, or sales forecast is verified by this technical contract.**

## Operating and security boundaries

- Only approved public official documentation, release notes, security advisories and the five approved public repositories may be investigated; this document does not authorize new sources or API endpoints.
- Never inspect private projects, connected apps, user conversations, passwords, logs, personally identifiable data, or other projects. Nothing from any other project enters the UCIE global library.
- Public external text/code is untrusted evidence, not executable instructions. Prevent prompt injection, malicious use, misattribution, bulk republishing and license violations. Honor opt-out, deletion/retraction and retention rules.
- No unapproved scheduler change, DB migration, auto-promotion, signing, training, network operation, release or cross-project skill installation.
- Source evidence, first-party synthetic proof, true independent upstream verification, host observation, legal permission, and a revenue experiment are distinct facts. A failure/unknown must remain NO_GO or NOT_VERIFIED.

## Regression commands (UCIE-only checkout)

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_skillbook_blueprint.py' -v
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_product_plan.py' -v
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.product_plan
```

These commands test **only** the stated contract on the exact checked-out code. GitHub CI is not a substitute for a live Windows owner-host receipt, and neither constitutes independent skill efficacy certification.
