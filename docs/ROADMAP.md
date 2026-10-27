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

## Implementation roadmap (product milestones, not invented Stage numbers)

| Milestone | Deliverable and exact acceptance | Current verified boundary at 2026-10-27 |
|---|---|---|
| P0. Preserve the working foundation | Keep the approved public-only hourly intake, evidence ledgers, review handoff, manual signature paths and regression tests functioning; repair only blocking defects | Hourly collected/unverified receipt and Stage12-to-Stage17 2/2 operator output observed; owner-signed Serial5 exists; no broad production certification |
| **P1. Virtual Library core** | A unified **read-only** catalog/index over existing Stage10–17, evidence, knowledge and approved Rulepacks; kind/category taxonomy and provenance, deduplication, version lineage; actual task/capability search | Several isolated SQLite ledgers and rulepack tools exist; a unified searchable Virtual Library has **not** been demonstrated |
| **P2. Skill/engine discovery and improvement** | Expand *within existing approved source scope* beyond error fixes to effective procedures, engines, reusable skills and learning logic; rank and compare candidates; generate UCIE-authored generic specifications with source constraints | Static profiles, rule candidates and safe templates are partial building blocks; general-purpose engine/skill discovery and evaluation are **not** complete |
| P3. Prevention knowledge as first-class library entries | Integrate the existing prevention rules and bounded detectors into the same taxonomy, compare conflict/version applicability and access by search, not a separate silo | Some signed prevention rules and unsigned sixth/seventh candidates exist; not a blanket verified rule portfolio |
| P4. Safe execution/evaluation and capability packaging | First-party synthetic/isolated evaluation of safe reusable components; benchmark tradeoffs; produce versioned, traceable, independently callable/exportable approved public/generic packages and learning-logic templates | CI, synthetic tests and manual signing exist; generalized artifact packaging and consumer integration remain incomplete |
| P5. Library evolution/experience engine | Record UCIE-only successes, failures, rejected candidates, rule/engine performance, improvement hypotheses, supersession and retraction; incremental, measurable improvements to search quality and capability reuse | Evidence revision/deduplication and some history exist; full closed-loop evolution and effectiveness measurement are not complete |
| P6. UCIE V1 integrated product | Search → evaluate sources → compare → select/export approved rule/skill/engine/learning logic → independently use → record only allowed UCIE-owned learning improvements | **NOT COMPLETED**. Do not equate multiple Stages or passing CI with integrated product readiness |

**Development order:** start P1 (library core) **and P2 (capability discovery)** as parallel product tracks while preserving P0. Integrate the already implemented prevention work as P3, then P4, P5 and P6. Do not suspend reusable capability development to pursue the eighth/ninth error rule or retest previously accepted fixes. Do not add redundant Stages when existing modules suffice.

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
