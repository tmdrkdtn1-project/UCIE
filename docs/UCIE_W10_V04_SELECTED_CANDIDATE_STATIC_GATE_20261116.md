# UCIE W10 v04 - exact P9 proposal to immutable candidate commit static gate

Date: 2026-11-16 KST
Project: UCIE ONLY
Status: FIRST_PARTY_SOURCE_DIFF_STATIC_REVIEW_ONLY; RELEASE NO-GO

## Inherited verified baseline

- W09 first-party consumer QA remains review-only without owner-supplied genuine signed original or manual selected rule.
- W10 v01 PR #296 main a8be4639ca38eb6ff03d3b90d2e6ad86a14abf20: genuine P9 hash-linked first-party revision proposals and owner source pin, no restoration.
- W10 v02 PR #297 main 96691586bd02dd4ead1906176e2de814db2b094d: SHA-256 + Git blob SHA-1 and TEMP-only byte roundtrip.
- W10 v03 PR #298 main 6bb42d3a83fdb07966de9f77c30ccfc59672652a: local Git ancestry/tree/path/blob and optional fixed-path owner source archive, no historical deployment assertion.
- Owner observed library_exact_index.py SHA-256 6e27de83192b066f73b9574d2a591607bcc1bef9512b97f94c5bdd3af528ee7e; unchanged current source is NOT an authenticated previous deployment backup.

## v04 source and review behavior

Source: src/ucie_miner/w10_selected_candidate_review_v04.py

1. Recomputes the exact original v01 P9 source-linked proposal queue from a dedicated UCIE root. Caller must name one 64-character proposal ID. No automatic proposal selection or approval. Only original P8 ucie_miner.library_exact_index:EXACT_QUERY_POLICY first-party synthetic proposal is eligible in this slice.
2. Reuses the actual W09 read-only review and W08 current-baseline nine-case heldout oracle via W10 v01. Optional exact W09 review SHA lease rejects stale receipts. These checks apply to CURRENT first-party baseline only, NOT to proposed candidate behavior.
3. Reuses W10 v03 local prechange immutable Git commit, exact path/mode/blob SHA1/SHA256, ancestry and fixed-path owner archive review; no restore file is created. Missing owner archive remains NO_GO.
4. Optional candidate group requires together: direct-child full Git commit SHA, SHA256, Git blob SHA1. Candidate must be exactly one direct child of prior commit; Git tree diff must consist ONLY of src/ucie_miner/library_exact_index.py. No other paths, merges or intermediate commits.
5. Candidate Git object bytes are read ONLY, never imported/bytecode-compiled/executed. AST parsing requires valid Python, unchanged top-level imports, retained original definitions, and no top-level expression or control block. This is STRUCTURAL ONLY, NOT independent security or functional equivalence acceptance.
6. Reports original experiment ID, exact proposal state, prior/candidate source pins, changed Git paths, W08 baseline results, optional archive presence, and explicit NO-GO release flags.

## QA and negative controls

Tests: tests/test_ucie_w10_selected_candidate_review_v04.py. Each test uses a fresh TEMP/UCIE repository, two first-party synthetic Git commits and actual temporary P8 proposal queue. Candidate adds an inert comment only, NOT a product improvement. Tests include exact proposal selection, missing candidate, SHA tampering, W09 stale digest, direct-parent requirement, one-file Git scope, import change, invalid syntax, top-level execution, cross-root denial, forged W10 approval, CRLF working tree and no operating file writes.

Even positive review cannot attest actual historical owner archive capture/deployment, candidate functional or negative-security regression, independent human QA, real signed W09 consumer after rollback, owner deployment authorization or customer V1 release.

## Safety and next gates

No new network GET, P11 rearm, scheduler, operating DB, working source, other project data, signing, rule promotion, model weights or release. Base PublicMiner HTTP403 and P11 network job6 REVIEW_REQUIRED at attempts5/5 remain held.

Require exact PR HEAD Windows and Ubuntu Python3.13 and Python3.15 independent 4/4 CI PASS plus actual new tests OK (skips do not count) before merge. Follow-on: genuine approved first-party functional candidate with isolated independent behavior+negative regression, authenticated owner-captured previous version and W09 owner consumer re-verification. Never execute untrusted upstream code.