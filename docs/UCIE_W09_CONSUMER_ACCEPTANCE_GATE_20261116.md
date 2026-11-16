# UCIE W09 Consumer-side acceptance and non-release gate — 2026-11-16

PROJECT: UCIE only. Source scope restricted to the approved independent
public repositories and their official public documents.
STATUS: W09_READONLY_CONSUMER_GATE_IMPLEMENTED__V1_RELEASE_NO_GO

## Canonical roadmap lineage and already-existing evidence

W03/W04/W05 federated metadata Library PR291, W06 Stage14 official
evidence PR292, W05/P8 real metadata benchmark PR293 and W07/W08
first-party QA / owner signed Rulepack review PR294 were merged only
after independent GitHub CI 4/4 PASS.

The existing repo already provides:
- signed_rule_library: ORIGINAL W07 Serial4 and Serial5 cryptographic
  verifier, public owner trust, expiry and fifth-addendum parent SHA.
- product_v1.integrated_product_preview: strict selected existing signed
  MANUAL rule reference from the original W09 descriptor (NOT a new
  package, not owner general-purpose release).
- manual_consumer_v1: original separate consumer verifier, which rereads
  the original signed ZIP and public trust at consumption time. It
  refuses changed/forged references, expired/revoked trust, changed
  pack identities and automated application.
- portable_consumer_qa: existing bounded first-party standalone DRAFT
  ZIP exact-key search parity in an independent -I Python process, with
  canonical source/ZIP/manifest comparison and no upstream code.
- w07_w08_independent_readiness_v01: original signed manual reference
  and UCIE-authored heldout plus P8 linked metadata exact-key evaluation,
  human QA/licensing explicitly NOT signed off.

## New integrator, no new permissions

File: src/ucie_miner/w09_consumer_acceptance_v01.py
Status without signed original pack paths:
  W09_NO_EXISTING_SIGNED_RULE_SELECTION_RELEASE_NO_GO
Status with original signed pack verified but no exact rule chosen:
  W09_SIGNED_OWNER_RULE_SELECTION_REQUIRED_NO_GO
Status with exactly one original signed manual reference successfully
reverified in a separate Python consumer process:
  W09_ORIGINAL_MANUAL_CONSUMER_REVERIFIED_RELEASE_NO_GO

1. Only D:/UCIE owner checkout and explicitly marked disposable
   TEMP/UCIE synthetic test roots are permitted, no other-project
   sources or unrelated files.
2. Always regenerates W07/W08 first-party readiness and runs the
   existing portable draft consumer QA in isolated temporary Python
   processes. No persistent ZIP is produced, installed or distributed.
   The standalone draft's 3 parity cases use only bounded sanitized
   unverified PR metadata or UCIE-authored synthetic examples.
3. If and only if existing signed Serial4 ZIP, owner PUBLIC trust PEM,
   optional Serial5 and one exact visible 64-hex selected item are
   supplied, call existing product_v1 selected-manual producer and
   the ORIGINAL manual_consumer_v1 in another isolated -I Python
   process, using strict bounded stdin JSON and first-party source code
   from the current UCIE checkout. Recheck original pack SHA, parent
   SHA, signed rule/item ID, W09 descriptor, original reference digest,
   consumer signature/trust/expiry receipt and every manual-scope
   non-approval flag. No source scanning/rule application in this gate.
4. Existing risk-signed MANUAL rule verification is not independent
   human QA, legal/license consent, supported version coverage, a
   proof of fixed security issue, a general skill-pack license or
   customer permission. Every output remains NO_GO.
5. A bounded SHA256 is only a reproducibility review handle, NOT
   a cryptographic owner signature, release authority or capability
   approval. Every path/ID/status used for a selected reference is
   regenerated from the original first-party original verifier and
   consumer. No approval by caller-supplied receipts.
6. No external GET, local operating DB writes, private signing key,
   import of upstream code, new signing or permanent file export,
   scheduler change, model training, P11 rearm or auto-promotion.

## Owner Windows local QA (fresh result)

New tests/test_ucie_w09_consumer_acceptance_v01.py:
10 cases, **9 passed / 1 skipped / 0 failed**, total 2.5 seconds
on the actual UCIE owner host after correcting a synthetic-fixture
expected count (W04 had two source-linked entries but the portable
PR-only consumer intentionally excludes one git/git COMMIT reference).

Actual D:/UCIE READONLY result:
- source linked P8 metadata rows: 1,335;
- first-party portable DRAFT: three standalone exact-key cases passed
  in independent Python process, not a signed or customer-approved app;
- real owner signed package supplied: FALSE;
- actual manual signed rule consumed: FALSE;
- network requests: 0; operating DB writes: 0;
- release authorization, license signoff and promotion: FALSE.

The one locally skipped test is the actual genuine synthetic Serial4
signature -> W09 producer -> independent manual consumer -> mutate old
pack -> fail closed integration. It requires the existing old
test_ucie_w07_w09_signed_library module, absent from the owner machine's
bounded test bridge. On GitHub's full checkout it is expected to run:
do NOT claim a positive genuine cryptographic roundtrip PASS until
independent GitHub Actions has run and passed on the exact PR commit.

The 9 executed local tests include real first-party independent draft
QA, source-linked PR-only contract, wrong paths and source escapes,
forged rights/release flags, malformed signed zip denial, forged
consumer receipt, W07 fake approval rejection, stable unsigned digest
and live D:/UCIE read-only observation.

## Owner read-only command — no existing signed paths needed

    cd D:\UCIE
    $env:PYTHONPATH='D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.w09_consumer_acceptance_v01 --ucie-root D:\UCIE --queries 32 --repeats 3

Optional exact owner MANUAL Rulepack consumer inspection, never
issue new packs, requires real existing owner-supplied paths:

    --serial4-pack EXISTING_SIGNED_ZIP
    --owner-public-trust EXISTING_PUBLIC_PEM
    --select-item EXACT_VISIBLE_SIGNED_RULE_ID
    --serial5-pack OPTIONAL_EXISTING_FIFTH_ADDENDUM

These are command arguments only, not stored secrets. Never pass a
PRIVATE signing key. No arbitrary executable, network URL, public PR
title, credential, user project path or automated export is accepted.

## Next separate W10 and V1 decisions

Genuine owner signed original files and exact selected manual rule are
not currently supplied. No independent human QA, version/repro rights,
security regression, consumer host signoff, package ownership license
or explicit customer release authorization has been granted.

W10 revision and rollback must stay isolated from original signed
packages and require source SHA pinning, independent heldout and
regression QA, manual approval and a rollback audit trail before any
promotion. P11 PUBLIC_INCREMENTAL_MINING job6 stays REVIEW_REQUIRED
5/5; base PublicMiner HTTP403 is a separate owner review hold.
Never resume its network GET as a side effect of W09.

STATUS=W09_READONLY_FIRST_PARTY_DRAFT_CONSUMER_QA_LOCAL_9_PASS_1_SKIPPED__
REAL_OWNER_MANUAL_SIGNED_CONSUMPTION_NOT_RUN__
W09_CUSTOMER_RELEASE_NO_GO__P11_NETWORK_HOLD__AUTO_PROMOTION_OFF.
