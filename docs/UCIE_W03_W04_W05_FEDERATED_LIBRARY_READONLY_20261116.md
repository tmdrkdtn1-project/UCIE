# UCIE W03/W04/W05 federated read-only Library: 2026-11-16

PROJECT=UCIE. WORKROOM=UCIE 통합개발방. NO EXTERNAL PROJECT SOURCES.
STATUS=INTEGRATION_IMPLEMENTED_LOCAL_QA_PASS__NO_PRODUCT_RELEASE.

## Roadmap lineage

Exact canonical master: docs/UCIE_V1_MASTER_ROADMAP_20261027.md
W01 -> W03 approved public source adapter.
W02 -> W04 common candidate metadata and source-linked public Library.
W01+W02 -> W05 engine/skill/learning-logic positive research.
W06 official metadata, W07 approved Rulepack, W08 evaluation,
W09 packaged export and W10 evolution remain separate acceptance gates.

The four pillar goals are coding-error prevention, reusable development
engine/skill/learning-logic improvements, a searchable Virtual Library,
and experience-driven incremental Library improvement. This new slice
does NOT constitute full P3, P9 or V1 acceptance.

## Implemented functionality

New module: src/ucie_miner/library_federated_readonly_v01.py.

- One bounded read-only query/CLI against the existing first-party UCIE
  W01 Source Registry, W03 public_source_adapter.adapter_plan,
  W04 source-linked Stage10/12/15 ledger search,
  approved official document reference shelf, and UCIE first-party
  Python test-recipe reference shelf.
- Optionally reuses W05 classify_public_capability_metadata on an
  explicitly injected bounded **offline caller-supplied** public
  metadata snapshot, with the exact W01/W03 approved source/URL gate.
  No implicit API calls, no persistence and no inference that this is
  an actually proven or useful engine/skill or a real training result.
  Default W05 source data is NOT LOADED, not silently scored as zero
  real-world capabilities.
- A fixed source plan for each of exactly 5 currently approved public
  repos; plan is INERT and grants no additional network permission.
- Deterministic first-party reference / recipe / optional offline W05 /
  source-linked W04 result ordering with source filter, bounded
  query, offset, page size <=20 and W04 deduplicated PR revision grouping.
- Each item has source_id, public_url, kind, purpose/domain,
  origin_shelf, evidence_level, and explicit false flags for
  licence/version/applicability/performance, owner approval and export.
- Official-reference SHA is a hash of the *URL string*, NOT verified
  external document bytes. W05 classification is title-cue-only; raw
  PR title is NEVER returned. W04 source linkage remains exactly the
  existing verified Stage10/12/15 in read-only SQLite query-only mode.
- Independent compare_visible_items() and CLI --compare-left/--compare-right
  compare *provenance only*, not which skill or fix performs better.
- If W04 linkage is missing or a Unicode query cannot be represented
  by legacy W04, result explicitly reports PARTIAL and no global
  complete count. Official document pointers can still be shown with
  clear scope. --no-legacy is a purposefully restricted reference
  shelf query, never a full Virtual Library.
- No additional endpoints, other public repositories, user files,
  customer context, connected apps, downloaded code execution,
  project scanning, network GET, model training, automatic release or
  production database writes.

## Owner Windows direct local read-only evidence

On real D:\UCIE the UCIE-only independent one-file test ran **10/10 PASS**.
For query=python, limit=6, legacy W04 linked review status was
READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO, with **795 grouped matches**
and one matching first-party official-reference test recipe. Displayed
six results. GET=0, operating DB writes=0, approvals/auto-promotion=0.
These are **795 unverified public evidence search matches**, NOT 795
validated, usable or individually approved skills.

Separate synthetic fixture established exact Stage10/12 source linkage
with 2 existing W04 unverified revisions plus 5 reference items, stable
cross-shelf page offsets, no duplicate identities, negative source
selection, prompt-injection-like query rejection and offline W05
3 distinct positive title-cue kinds. A missing Stage12 queue is
explicitly PARTIAL, never accepted as an empty real-world Library.

Related historical suites:
test_ucie_positive_capability_discovery.py 12 PASS.
Two other older single-file suites were not executed in this run
because the current bounded UCIE test bridge returned INVALID_ARGUMENT:
test_ucie_public_adapter_library_search.py and
test_ucie_library_w05_w06_shelves.py.
They must not be claimed as fresh PASS.

The new source+test have not yet received independent GitHub CI unless
a subsequent verified Actions receipt documents exact commit status.

## Read-only usage

    cd D:\UCIE
    $env:PYTHONPATH = 'D:\UCIE\src'
    .\.venv\Scripts\python.exe -B -m ucie_miner.library_federated_readonly_v01 --query python --limit 6

Approved exact-source selection:

    .\.venv\Scripts\python.exe -B -m ucie_miner.library_federated_readonly_v01 --source-id repo:python/cpython --query python --limit 6

Reference-only shelf:

    .\.venv\Scripts\python.exe -B -m ucie_miner.library_federated_readonly_v01 --no-legacy --limit 10

These commands do not call GitHub and do not update SQLite or task
scheduler. Comparison requires two IDs from the SAME visible page,
no approval or ranking is inferred.

## Next gates, do not conflate

1. W03: pinned adapter connector integration, owner-approved API
   budget and safe collection recovery **only after** independent base
   miner HTTP403 diagnosis. P11 job6 remains held at 5/5.
2. W04: connect federated read-only result to existing Library user
   presentation and W06 existing Stage14 public metadata with exact
   evidence-type trust contracts; do not collapse official document
   references, PR titles and first-party recipes into "one verified fix".
3. W05: independently verify concrete positive technical claims with
   source-pinned revisions, license and UCIE-authored bounded tests;
   only then consider meaningful comparative improvement evidence.
4. W07/W08/W09/W10: approval-bound Rulepack linkage, measured safe
   performance/accuracy, approved portable export and first-party
   versioned improvement loop. Full four-pillar designated-customer
   release remains NO_GO.

STATUS=W03_W04_W05_READONLY_FEDERATION_LOCAL_10_PASS__
W04_OWNER_795_UNVERIFIED_MATCHES__NO_GET_NO_DB_WRITE__
FULL_VIRTUAL_LIBRARY_INTEGRATION_PENDING__P11_HTTP403_HOLD__
AUTO_PROMOTION_AND_CUSTOMER_RELEASE_OFF.
