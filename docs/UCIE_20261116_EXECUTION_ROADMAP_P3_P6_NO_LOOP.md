# UCIE 2026-11-16 execution roadmap correction — deliver product outcomes, stop gate-only loops

Scope: UCIE only. Owner D:/UCIE dirty working tree is NOT synchronized, reset, or changed by this GitHub branch.
Authority: docs/ROADMAP.md (four pillars and P0-P9 product criteria), docs/UCIE_V1_MASTER_ROADMAP_20261027.md (historical work order), docs/UCIE_FULL_PRODUCT_PRIVATE_CUSTOMER_RELEASE_V1.md (full product + explicit release authority). This status is a *2026-11-16 execution addendum*, not a rewrite of archived 2026-10-27 observed states or an owner approval.

## Rescoped priorities and verified evidence

| Gate | Previously observed | Current decision and proof required |
|---|---|---|
| P0 base | Existing UCIE public-only collector and owner/CI receipts | Preserve only; CI does not certify production scheduler or incident recovery |
| P1 Source Registry | source_registry modules and fixed approved five-repository boundary | Reuse existing allowlist; no new public sources, no unapproved GET |
| P2 intake | GitHub/official metadata pipelines and bounded queues exist | PublicMiner HTTP403 owner HOLD and P11 network job6 REVIEW_REQUIRED attempts5/5 remain separate incidents; no rearm for this project task |
| **P3 Virtual Library** | W04 substring result paging existed; optional W04 exact multiquery index returned first 20 but no exact paging route from CLI; multi-shelf Local UI exists | **Immediate deliverable**: bounded deterministic read-only exact page offsets through API and CLI; retrieve every eligible revision, keep source/approval metadata, no duplicate or forged approval; does NOT meet full approved-export MVP |
| P4 capability discovery | Positive metadata classification/review heuristics and SkillBook/recipes exist | No independent real improved algorithm claimed; protect source/version evidence |
| P5 prevention integration | Verified vs unsigned candidate rules distinguish status | No new signature, promotion, release |
| **P6 measured evaluation** | W08 deterministic synthetic cost/heldout checks, W10 v01-v04 source/rollback/static gates all merged main after matrix CI | **Immediate coverage measurement**: page 27 of 27 UCIE synthetic linked revisions, sorted unique IDs, 0 missing/overlap, positive/negative CLI tests; this is functional coverage, NOT speed or real candidate algorithm benefit. Next substantive step: actual first-party algorithm candidate with independent heldout behavior/security/latency comparison |
| P7 authorized export | Portable draft first-party consumer code and rights boundary exist | Customer-ready private signed full product / license/rights/recipient acceptance still NO-GO |
| P8 experience evolution | P9 review queue with two unapproved candidates, W10 v01-v04 Git source/backup/static review | Do not add v05 merely another SHA gate. Only advance with actual approved-source functional delta, measurable value and postrestore behavior; owner historical backup still not authenticated |
| P9 integrated V1 | Local experience and P9 preview/CI proofs | Full four-pillar V1 private customer acceptance NOT established. Do not claim product completion from code or synthetic CI |

## Nonloop critical path (bounded batches)

### Batch A — NOW (P3 actual use)
Implement and validate exact linked Library pagination. User command `python -m ucie_miner.library_search --source-id repo:modelcontextprotocol/python-sdk --domain MCP/API --kind PUBLIC_TECHNICAL_EVIDENCE --exact-purpose EXCEPTION_HANDLING --limit 10 --offset 20`; only existing local UCIE source-linked ledger is read. Offset bounded by existing MAX_PAGE_OFFSET. Zero-offset remains backward compatible, no new GET/DB writes. Fail closed for negative, bool, out-of-range, source not linked. At least 27/27 first-party synthetic case retrieval plus Windows/Ubuntu Python3.13/3.15 CI 4/4 needed before merge.

### Batch B — NEXT (P6 actual improvement, not gate theater)
Identify an actual first-party functional difference (not a comment-only candidate), pin original and proposed source, independently verify behavior on UCIE-owned heldout test cases including negative security and supported runtime, compare pre/post observable results with stated limits. Do not execute third-party upstream code. No automatic candidate acceptance or owner runtime change.

### Batch C — AFTER OWNER DEPENDENCIES (P9 actual acceptance)
Verify historical owner-retained exact prechange restoration archive and capture provenance, existing signed original/owner trust, license/third-party rights, entire four-pillar private product packaging/security/recipient acceptance, explicit owner deployment/rollback/customer sign-off. P11/public miner network holds require separate owner incident handling, never bypass them to obtain a green result.

## Stop / go accounting

- W10 v01 PR296, v02 PR297, v03 PR298, v04 PR299: developer code/CI milestones, NOT four separate deployment approvals. Do not create v05 solely to expand static-pinning flags.
- No owner Windows checkout/file/DB/Windows task changes, external public GET, new private scope or unauthorized source code execution in this batch.
- Distinguish IMPLEMENTED vs SYNTHETIC_CI_PASS vs HOST_OBSERVED vs INDEPENDENT_QA vs OWNER_APPROVED vs CUSTOMER_RELEASE. Only the actually tested fields can be PASS.
- Existing docs/ROADMAP.md on owner PC was observed locally modified; do not overwrite that file or attempt a Git reset/checkout on D:/UCIE. Maintain this addendum in GitHub and record its exact PR/CI receipt.

STATUS=P3_P6_REAL_FUNCTIONAL_PAGINATION_DEVELOPMENT__OWNER_LOCAL_UNCHANGED__V1_RELEASE_NO_GO

## Discovered nonloop regression blocker (P3 functionality vs W10 historical pins)

Initial exact-head CI #43829319690 ran new P3/P6 tests 12/12 OK on Ubuntu Python3.13/3.15, but each full suite reported 1 failure and 1 error in older W10 v02/v03 tests: W09 historical pinned source SHA was compared to **moving HEAD** after the real W04 source changed. This is a stale regression-test premise, not evidence that the new pagination is an unapproved source change or that the original historical bytes were altered.
Correction: W10 v02 test uses exact original W09 immutable commit aeecc3fc64dc542daba6e40ef29dce66c296ebdf with its original blob SHA1 0f92ed46b68685e0edb98f4fc09c3846b5b8d2c6; W10 v03 historical ancestor/archival test also uses that fixed commit, while independently reporting current HEAD as a separate value. The real original source SHA256 6e27de83192b066f73b9574d2a591607bcc1bef9512b97f94c5bdd3af528ee7e remains checked. **No security test removed or skipped; do not claim PASS until new exact-head matrix CI validates all old and new tests.**
