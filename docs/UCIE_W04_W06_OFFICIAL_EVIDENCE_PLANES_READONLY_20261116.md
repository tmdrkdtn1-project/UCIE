# UCIE 2026-11-16 — W04 / W06 independent evidence-plane integration

PROJECT=UCIE. No external customer or other project content.
SOURCE_SCOPE=exactly five previously owner-approved public repositories
and corresponding official public documentation references.
STATUS=READ_ONLY_SEARCH_IMPLEMENTED__LOCAL_QA_PASS__PRODUCT_NO_GO.

## Canonical roadmap linkage

W01 Source Registry -> W02 candidate LibraryEntry -> W03 approved public
adapter preview -> W04 source-linked Stage10/12/15 candidate library.
W05 development engine / reusable skill / learning-logic signals remain
unverified title heuristics, not adopted technology.
This change adds W06 read-only Stage14 public document/release/security
metadata. Stage14's official metadata fingerprints MUST NOT be conflated
with W04 merged-PR review candidates or with the in-memory *URL-string*
hashes of official document references.

## Implemented

- Existing src/ucie_miner/library_shelves.py
  search_official_metadata_shelf now accepts a strictly bounded
  offset 0..20,000, separate from the existing <=20 result limit.
  Uses the unchanged Stage14 schema/source/identity attestation,
  existing SQLite URI mode=ro, PRAGMA query_only=ON and stable
  ORDER BY source,kind,upstream_reference,content_sha256.
  No migration/write or new HTTP route. Default offset 0 preserves
  existing callers.
- New src/ucie_miner/library_federated_official_v02.py
  search_with_official_evidence(root, query, source_id, official_kind,
  limit, offset, official_offset, include_w04) composes the merged
  W03-W05 federated read-only catalog (PR #291) with existing W06
  Stage14 official metadata shelf. Both windows remain **separate**:
  independent total_matches and offsets; W04 and W06 totals NEVER
  aggregated as distinct verified capabilities.
- Existing Stage14 official metadata rows are projected into a safe
  UI/search view with a deterministic metadata inventory ID, but this
  ID is explicitly NOT a document content hash, verified document
  revision, owner signature or capability quality score. Preserves
  allowed source, official kind, metadata digest, reference scope,
  observed UTC and URL. No untrusted text, patches, PR titles, tokens
  or downloaded code.
- Missing W06 ledger reports PARTIAL with total_matches_unknown (None),
  not a fabricated zero verified official findings. Missing W04
  source linkage also reports PARTIAL independently. Unicode query
  support remains limited by old W04 contract, with explicit PARTIAL.
- compare_catalog_to_official(...) only compares provenance and
  evidence levels between one visible W04-style candidate item
  and one visible W06 metadata item. Never asserts the same fix,
  verified vulnerability remediation, benchmark benefit, license
  or version compatibility.
- First-party safe text-only operator UI (no web server) and JSON
  output options: query, source filter, official kind, two
  independent page offsets. Never invokes a public GET, execution
  of source code, model training, rule promotion, approval, or export.

## Actual read-only Windows owner evidence (D:/UCIE)

First-party UCIE-only independent single-file
tests/test_ucie_w04_w06_official_evidence_planes_v02.py:
**8/8 PASS**. The live read-only inventory returned:
- W04 merged PR linked unverified search hits for query=python: **795**.
- W06 official metadata document/release/advisory inventory: **1,478**
  (all official metadata kinds, unfiltered; W04 query filtering does
  NOT imply W06 query filtering).
- First results: six items per window at limit=6.
- Both W04 and W06 source linkage/ledger structure passed their
  existing first-party checks.
- 0 public GET and 0 operating SQLite writes.
- No model-weight change, approval, customer export or release.

These hit counts are **not 2,273 approved technical improvements**;
they are two incommensurable, unverified evidence inventories.

The synthetic TEMP/UCIE tests exercised:
- empty W06 ledger vs known zero results,
- stable W06 pagination across document/release/advisory,
- source and official-kind filtering,
- source/reference drift, unsafe offsets, injected query and invalid
  W06 record rejection,
- W04+W06 both present with real stage10/12 fixture and dual trust gates,
- provenance-only cross-plane comparison,
- human-readable no-GET operator UI.
No external API was used.

## Read-only operator usage

    cd D:\UCIE
    $env:PYTHONPATH='D:\UCIE\src'
    .\.venv\Scripts\python.exe -B -m ucie_miner.library_federated_official_v02 --query python --limit 6

JSON with exact source and advisory focus:

    .\.venv\Scripts\python.exe -B -m ucie_miner.library_federated_official_v02 --query python --source-id repo:python/cpython --official-kind advisory --limit 6 --format json

Next official metadata page without changing W04 page offset:

    .\.venv\Scripts\python.exe -B -m ucie_miner.library_federated_official_v02 --query python --limit 6 --official-offset 6

## Independent acceptance still pending

- Exact GitHub cross-platform CI for the new pull request, including
  old callers of search_official_metadata_shelf(default offset=0).
- W05 independent measurement of actual capability improvement
  using UCIE-authored regression/benchmark receipts and exact
  source/commit/license review. A PR title signal alone does NOT pass.
- W07 Rulepack QA gate, W08 independent comparative evaluation,
  W09 authorized portable export and W10 controlled improvement loop.
- Main PublicMiner GitHub HTTP403 remains owner review HOLD. P11
  PUBLIC_INCREMENTAL_MINING job6 remains REVIEW_REQUIRED. No changes
  to scheduler, collection, model or candidate promotion in this slice.

STATUS=W04_W06_SOURCE_LINKED_DUAL_VIEW_LOCAL8PASS__
OWNER_W04_795_W06_1478_UNVERIFIED_INVENTORY__
GET0_DBWRITES0__P11_NETWORK_HOLD__CUSTOMER_RELEASE_NO_GO.
