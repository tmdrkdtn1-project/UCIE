# UCIE — Four-Pillar Product Charter and Development Roadmap

**Authoritative product direction (owner clarification, 2026-10-27).**
UCIE is an independent, public-evidence-based **development intelligence and reusable capability library platform**. It is **not merely a coding error prevention tool**. The four pillars below are coequal *end goals*; the Virtual Library is the shared product foundation, and continual evolution is an ongoing feedback loop, not a final optional feature.

## Four non-negotiable product objectives

### 1. Prevent coding errors
Find recurring errors in Python, PowerShell, Windows, Git, and MCP/API technologies; explain failure conditions, safe calls, version applicability, and regression checks. Recommend prevention before an issue occurs. A candidate, tested rule, signed rule and independently certified finding are different states.

### 2. Discover and improve effective development/maintenance engines and skills
From **only approved public technical evidence**, identify useful general-purpose engines, skills, algorithms, reusable development procedures, test methods and **learning-engine logic**. Compare alternatives using explicit criteria (practical utility, correctness, portability, maintainability, performance where measurable). Produce UCIE-authored, safely abstracted capability specifications and improved candidates. Discovery is not limited to bug-fix PRs; positive engineering patterns and maintainability improvements matter. Do not claim that a description or a code-generation prompt constitutes a working engine.

### 3. Build a categorized Virtual Knowledge Library usable by any type of project
A searchable, versioned catalog of preventive rules, **reusable engines, skills, and learning-engine logic**. Users of any project type can **select and export approved public/generic artifacts** for use in their own independently authorized environments. UCIE never gains authority to inspect, import private experience from, or control those projects. The library is a product, not just SQLite storage.

Organize each library entry with bounded, inspectable metadata:
- Identity: stable item ID, item type (prevention rule / engine / skill / learning logic / test recipe), category, keywords, purpose, supported language/platform/runtime/version, dependencies and interface contract.
- Evidence: exact allowed public source, ownership, revision/PR or commit, publication/merge date, license and provenance evidence, hashes, limitations and source trust status.
- Application: preconditions, supported inputs/outputs, safe steps, regression/negative tests, expected benefits and measurable tradeoffs, incompatibilities and usage constraints.
- Lifecycle: candidate/tested/reviewed/approved/published/deprecated/retracted status, version lineage, duplicates, supersession, reviewer/owner decision, export packaging/signature status.
- Experience: authorized UCIE-native experiments, observed failures/successes and related improvements, kept separate from unreviewed source claims and approvals.

**Library MVP** is complete only if a user can search by problem, task, language, platform, use case or capability; inspect grounded evidence and limitations; compare relevant items; and obtain an explicitly approved, version-pinned, reusable artifact. A hash-only index or a list of PR URLs is **not** this acceptance criterion.

### 4. Continually evolve the Virtual Library from the first three activities
Maintain a repeatable improvement loop: new approved public evidence and **UCIE's own authorized synthetic/isolated test observations** → deduplication and lineage → useful discovery or improvement hypothesis → safe experiment/evaluation → result recorded with limitations → revised library entry or explicitly rejected hypothesis. Reuse failed attempts as negative lessons so recurring errors and duplicate development decrease.

Evolution means measurable improvements to the library and its reusable engines/skills; it **does not** mean unattended source execution, silently changed model weights, automatic promotion, or learning from private project files, conversations, connected apps, or per-project telemetry. Model training or weight updates would be a separately designed and approved capability, not a present claim.

## Product architecture

```text
APPROVED PUBLIC TECHNICAL INPUTS ONLY
        |
        +--> A. Coding Error Prevention Knowledge --------+
        |                                                 |
        +--> B. Engines / Skills / Learning Logic --------+--> C. VIRTUAL LIBRARY
        |         Discovery, Comparison, Improvement      |    classify / index /
        |                                                 |    search / trace /
        +--> Approved Evidence and UCIE-Owned Test Records+    version / package
                                                                |
                                                        independent consumers
                                                   select public/generic artifacts
                                                   (no UCIE project access)
                                                                |
        D. CONTINUAL EVOLUTION <--- UCIE-owned evidence / safe experiments /
             |                     improvement and rejection records ONLY
             +----> improves A, B and C; no private feedback return path
```

## Final UCIE V1 product roadmap — P0–P9 (2026-10-27)

**Canonical detailed plan:** [UCIE V1 Master Roadmap](UCIE_V1_MASTER_ROADMAP_20261027.md).
**Machine-readable final goals/work-order preview:** `python -m ucie_miner.product_plan` (inert, read-only, no network or deployment).

The four pillars above are coequal; two foundational systems are mandatory and not optional appendices:

1. **Source Registry and source selection:** evaluate public API sites, technical documentation, tools and datasets for utility, provenance, license, access policy and current explicit approval. Do **not** treat future candidates as approved sources.
2. **Modular automatic public-source acquisition:** allowlisted API/document adapters, bounded incremental ingestion, checkpoints, deduplication, scheduling and safe failure recovery, leading into the Virtual Library. Reuse the existing UCIE hourly GitHub miner.

| Milestone | Product outcome | Verified current boundary (2026-10-27) |
|---|---|---|
| P0. Existing engine foundation | Preserve the public-only collector, evidence ledgers and approved signed rules; fix only blocking defects | Observed one successful hourly unverified intake and Stage12→17 review 2/2; Serial5 owner-signed; not V1 certification |
| **P1. Source Registry** | Catalog accepted/research-only sources, ownership, API/access/license/version scope; reject unapproved fetch | **NEXT**: approved repo allowlist exists; generalized registry absent |
| **P2. Modular public data intake** | Connect approved GitHub/official doc feeds to a common adapter contract; keep API budget and safe incremental pipeline | **PARTIAL**: bounded GitHub and official metadata stages exist; generic adapters incomplete |
| **P3. Virtual Library** | Unified indexed/searchable categorized knowledge of engines, skills, learning logic and prevention rules | **NEXT**: separate ledgers exist, unified library not complete |
| P4. Engine/skill/learning-logic discovery | Extract useful *positive* development techniques and improvement candidates, not just bugs | **FOUNDATION_ONLY**: skill profiles/heuristics exist |
| P5. Prevention knowledge integration | Import versioned, evidence-bound, signed/unsigned error-prevention rules into searchable Library | **PARTIAL**: multiple scanners/rules exist; library integration missing |
| P6. First-party safe testing/improvement | Execute bounded UCIE-authored regression and capability evaluation; show measured improvement | **PARTIAL**: synthetic tests exist; generalized evaluation incomplete |
| P7. Portable capability packages | Package approved general-purpose skill/engine/learning logic with interfaces, dependencies and lineage | **NOT_IMPLEMENTED** as generalized product |
| P8. Learning from UCIE-owned experience | Capture failures/successes and revise library contents and reusable methods without private project feedback | **PARTIAL**: revisions/dedup exist; closed-loop improvement missing |
| P9. UCIE V1 integrated product | Source acquisition → discovery → library query → evaluation → approved export → library evolution | **NOT_ACCEPTED** |

**Immediate development order:** W01 Approved Source Registry and W02 Library Entry taxonomy in parallel; bridge W05 discovery contracts; then W03 existing collector adapter, W04 read-only catalog search, W06 approved documentation connector, W07 rule integration, W08 first-party evaluation, W09 capability packaging, W10 evolution/V1 integration. See the canonical master document for exact dependencies, statuses and acceptance criteria.

**Current milestone:** `P0_BASELINE_OBSERVED__P1_AND_P3_NEXT`. P2 and P4 reuse existing partial functionality; no new error-rule race or redundant re-testing.

## Source boundary / trust and distribution

- Permitted external public evidence is confined to official technical documents, releases, security advisories and the expressly approved repositories: `python/cpython`, `PowerShell/PowerShell`, `git/git`, `modelcontextprotocol/python-sdk`, `actions/runner-images`. Do **not** expand the repository allowlist without a separate owner instruction.
- Keep UCIE separate from all other projects: no private code, repositories, user files, connected apps, project metadata or experiences; no cross-project knowledge interchange; no globally mixed private data.
- External code/text is untrusted input, never an instruction to execute. No bulk source copying, raw patch redistribution or secrets in committed artifacts.
- Respect license, opt-out, deletion, retraction and public-source ownership. Distribution should use only authorized, original/generalized content with grounded evidence and required attribution.
- Existing owner's manual approval, signature, QA limitations and release scope remain unchanged. No unattended rule promotion, signature, deployment, project scanning or model-weight training.

## Status terminology / evidence discipline

`IMPLEMENTED` means code exists; `CI_PASS` means tested on the stated exact commit; `HOST_OBSERVED` means an explicit local receipt; `APPROVED` requires an actual authorized decision; `V1_ACCEPTED` requires the integrated product criteria above. These are **not interchangeable**. Stage12/17 review proposals are unverified knowledge candidates, not proof of corrected behavior.

## Legacy implementation Stages remain valid

Original Stage1–4 design and later Stage10–18 modules are **implementation history**, not UCIE's four product goals. Stage1 offline PUBLIC_ONLY and signed-demo scaffolding, Stage2 public-miner/evidence-gate prototypes, Stage3 dedicated Windows hourly miner, and Stage4 owner's two distinct QA/release routes remain governed by their existing detailed docs, including `docs/STAGE4_AUTOMATED_QA_OWNER_APPROVAL.md`. The manual owner-risk acceptance route is not independent legal or security signoff. Existing signed Serial4/5 artifacts remain immutable and separate from unsigned sixth/seventh candidates. Product goals do not themselves authorize any additional runtime/network access.
