# UCIE Stage12 handoff capacity incident - 2026-11-09

Scope: UCIE-only existing approved public metadata. No private project data, source execution, operating SQLite writes, new collector/scheduler, Cloudflare changes, new paid hosting, candidate promotion, or customer distribution.

## Owner facts before repair

- Exact owner Windows checkout: D:/UCIE
- Stage12 review file: runtime/stage12_unverified_review.sqlite3
- Connection: sqlite3 mode=ro, PRAGMA query_only=ON
- Review queue: 1,008 rows and 1,008 unique fingerprints, all UNVERIFIED_REVIEW_CANDIDATE_ONLY
- SQLite PRAGMA quick_check: ok
- Existing Stage10/opted-in Stage15 source re-derivation: source revisions 1,008, linked 1,008, pending 0
- Handoff: LINKED_UNVERIFIED_NO_GO; tasks 1,008 UNVERIFIED_CANDIDATE_ONLY; auto_promoted=false, production_approved=false, deploy_allowed=false
- The verifier threw PolicyError: invalid public candidate review ledger because it enforced a separate hardcoded limit of 1,000 tasks. No evidence of SQLite corruption.

## Three mismatched consumer caps

1. automated_candidate_qa._checked_handoff: 1,000 task maximum rejected the entire W04 verified-source handoff.
2. experience_application.MAX_CATALOG_ROWS: 1,000 task maximum blocked real Local V1 public catalog evaluation after the first cap was fixed.
3. library_exact_index.MAX_CATALOG_ROWS: 1,000 task maximum blocked exact source-backed batch queries on the same set.

Canonical Stage12 source maximum is public_candidate_staging.MAX_ROWS = 10,000. All three source-linked consumers now reuse that original fixed cap. Independent search page limit (20), exact batch limit (32), upstream allowlists, source/merge-SHA validation, license and owner approval gates remain unchanged. Other subsystems' small sample caps were not broadened.

## Verified red/green execution

- Before the fix: the new six-test suite failed four tests as expected; the original owner read-only smoke failed four tests with the bad handoff.
- After fixing only the first handoff cap: new suite 6/6 PASS, owner Local V1 smoke 2/4 PASS; the remaining failures were public catalog benchmark and its browser path.
- After all three fixes: expanded owner suite 7/7 PASS on actual 1,008-row source-linked ledger, with search, exact lookup and catalog benchmark; existing owner Local V1 complete browser/search/review smoke 4/4 PASS.
- Boundary: 10,000 rows checked as source-linked but NEVER approved; 10,001 rejected; forged approval, duplicate fingerprint and missing verification block rejected. Incomplete provenance remains NO_GO.
- Source changes made by exact-SHA leases with automatic isolated backups. No operating public data, public miner, scheduler or other unrelated files changed.

## Gate separation

These are local code/owner read-only integration test receipts, not proof that the already running windowless Windows UCIE process has reloaded the source. After GitHub PR merge the owner may restart ONLY UCIE-LocalV1-Web, then check the local health endpoint and real Edge search/engine links. Never restart UCIE-PublicMiner-Hourly or another service for this issue.

Remaining data-quality objective: collect evidence for source version and license completeness, duplicate rates, source linkage lag, genuinely reproduced fixes and false positives. Counts of unapproved candidates do not equal approved error-prevention rules.

Roadmap: https://github.com/tmdrkdtn1-project/UCIE/issues/199
