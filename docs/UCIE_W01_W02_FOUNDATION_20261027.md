# UCIE W01 + W02 First Functional Batch (2026-10-27)

## Scope and authoritative status
- Work items: **W01 Source Registry V1**, **W02 Virtual Library Entry Contract V1**.
- These are **actual importable code modules**, not just P0–P9 planning constants.
- They do **not** mean W03 generic collection adapters, W04 indexed Library search,
  W05 engine/skill extraction, V1, or a production deployment have finished.
- Existing `docs/UCIE_V1_MASTER_ROADMAP_20261027.md` remains the product charter.

## W01 / public source registry
Module: `src/ucie_miner/source_registry.py`.

- Reads the **existing** `public_discovery.SOURCES` five-source allowlist,
  owner labels from `evidence.SOURCES`, and the five pinned public documentation
  URLs from `public_evidence_routes.DOC_ENDPOINTS`.
- Produces **ten active records** (5 independent public repositories + 5 exactly
  pinned official-document endpoints) and **four research-only source names**.
- Research-only names remain non-actionable; they have no URL or fetch method.
- Each record has source ID, type, public URL where approved, provenance label,
  existing access method, material classification and license-review limitations.
- A registry entry **never authorizes a new URL or network fetch**; the older
  hardcoded URL allowlists, rate caps and stage-specific opt-ins remain authoritative.
- No source added, no new scheduler, no operational DB or model write.

Preview after the exact code is present in the dedicated UCIE checkout:

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.source_registry
```

## W02 / Virtual Library metadata contract
Module: `src/ucie_miner/library_entry.py`.

- Defines strictly bounded public candidate types:
  `PREVENTION_RULE`, `DEVELOPMENT_ENGINE`, `REUSABLE_SKILL`,
  `LEARNING_LOGIC`, `TEST_RECIPE`; `UCIE_EXPERIENCE` is reserved
  for *later verified UCIE-owned* experience and blocked for external candidate input.
- `build_library_entry(record)` requires exactly: `kind`, `source_id`,
  `evidence_reference`, `evidence_sha256`, `purpose_code`,
  `version_scope`, `dependencies`.
- Only binds PR/merge/commit references to the already approved source and
  exact official-doc URLs; rejects unrelated, unapproved and research-only sources.
- Creates a reproducible SHA256 library identity; marks every imported candidate
  `UNVERIFIED_CANDIDATE_ONLY`, `NOT_APPROVED`, unsigned and non-exportable.
- No source text, patch, external commands or project data retained.
- Only an in-memory schema/record constructor is present. **Persistent Library
  index and actual search are W04, not a W02 claim.**

Preview:

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.library_entry
```

## Narrow quality gate
`tests/test_ucie_source_registry_library_entry.py` includes focused offline
examples of active and blocked source identities, real-shaped Stage12 public
candidate metadata, pinned official docs, typed Library items, deterministic
identity, missing/invalid metadata, and no network access. The existing plan
test is updated to report W01/W02 *code foundation available but not host
deployed*, not full milestone accepted. Exact-head GitHub Actions must pass
before claiming CI_PASS; the owner-PC command remains a separate observation.

## Immediately following development batch

1. **W03 Acquisition adapter**: reuse the existing Stage9–15 GitHub fetch and
   check-point logic behind a small read-only common adapter contract. No
   collector rewrite, additional API budget or scheduler registration.
2. **W04 Virtual Library search**: read already existing Stage10–17 SQLite
   ledgers with `mode=ro`; join safe, indexed source/revision/evidence metadata
   to W02 entries, category/version/keyword filters; never claim unverified
   entries are approved. Do not overwrite or migrate original ledgers.
3. **W05 engine/skill/learning logic**: generate strictly reviewed, public,
   generic capability candidates independently from bug-fix counts. Run
   targeted UCIE-authored synthetic evaluations later, no model weights.

Operational host status, licensing signoff and independent QA are **not**
inferred from this development or its CI.
