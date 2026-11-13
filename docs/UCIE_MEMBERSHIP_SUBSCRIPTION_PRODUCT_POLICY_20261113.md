# UCIE membership subscription — signed access implementation and customer launch gates (2026-11-13)

**Product business model: PERSONAL OWNER, MEMBERSHIP SUBSCRIPTION. NOT PERPETUAL SOFTWARE SALE OR PER-INSTALL PAYMENT.**
Owner may later incorporate a company; that later transaction should resolve rights/license and customer-contract assignment then, not make up an existing company now.

## Membership scope vs. software integrity

Existing C3/C4 Ed25519 *product artifact* entitlement binds the exact first-party wheel, all 3 vendor digests, 4 product pillars, owner public key, recipient token, rights packet and serial. Earlier technical A/B trial tokens expire in **30 days**, which continues to work without breaking the original tests. For NEW genuinely authorized C3 owner signatures the bounded product-artifact validity is **1095 days (3 years)**, with only these two EXACT duration choices accepted. This stable product integrity token is NOT proof of a paid subscription, does NOT authorize paid features alone, and remains independently revocable through an owner serial floor. Every `/local` customer route still requires a separate valid short signed membership lease. A paid monthly/annual subscription therefore does NOT require reinstall of the SAME genuinely signed wheel at each billing renewal. Customer rights/security and distribution remain NO_GO until actually approved.

New UCIE signed **membership** has its OWN purpose-separated Ed25519 domain and canonical record with fixed membership subscription ID SHA, recipient token SHA, owner public-key ID, signed legal rights SHA, plan, calendar billing interval, owner-attested actual provider receipt SHA, owner-controlled renewal sequence, minimum product license serial, signed billing state and UTC dates. Existing approved owner private PEM is only loaded in the separate owner-host signer after distinct TTY consent, pre-existing SHA-pinned legal/security/customer contract decision and separately SHA-pinned owner-reviewed billing event; NEVER create a new key silently.

Monthly and annual are BILLING INTERVALS, not a purchase of a forever-install license. Calendar months handle leap February; annual uses calendar anniversary. A signed **offline ACCESS LEASE** expires within **35 days** even on annual payment, and cannot outlive the paid term (or the at-most-7-day owner-approved grace period). A new owner-signed lease is a *status refresh*, NOT a second charge. The annual customer remains entitled to the paid period if periodic valid leases are supplied, subject to signed cancellation/revocation and valid product entitlement. Offline use is limited by owner-issued floor, signed lease expiry and the machine clock, not independently trusted server time.

## Provisional feature access tiers (not prices)

| Tier | Error prevention | Development engine and skills | Virtual library / SkillBooks | Evidence evolution |
|---|---|---|---|---|
| Standard | Yes | No | Yes | No |
| Complete | Yes | Yes | Yes | Yes |

Tier names and allowances are IMPLEMENTATION DEFAULTS for QA, not a commercially approved published price, seat count or package matrix. Customer-signed membership grants exactly the selected tier, bound to one independently approved recipient token. Multi-seat pooling/seat registration is NOT implemented, even if named future Team/Business. Always protect full third-party OSS rights; these tiers restrict UCIE's proprietary service features, not license rights granted separately by cryptography/cffi/pycparser/OpenSSL.

## Status rules and single entrypoint access enforcement

| Signed billing status | Within paid period and valid lease | At/after period end |
|---|---|---|
| ACTIVE | Access to tier features | EXPIRED: deny |
| CANCEL_AT_PERIOD_END | Access through paid period (if lease stays refreshed) | EXPIRED: deny without new charge |
| PAST_DUE | Tier access through already paid term (if lease valid) | At most 7-day signed grace: /local/library and /local/books listings only, no executable SkillBook, engine, review or evolution; then deny |
| SUSPENDED or REVOKED | Immediately deny once newly signed status reaches this offline device | Deny |

Regardless of billing status, lack of independent owner public key/recipient, missing real C3 product validation, wrong membership account, invalid signature, short access-lease expiration, old renewal sequence, malformed dates, raw payment receipt forgery, or future-issued token => DENY. Customer-created work products are NOT deleted upon cancel/expiry/revocation, and personal customer code is not added to the public miner.

Product Local V04 server `customer_private_offline_lifecycle_v01.serve_selected` now **requires** an independently pinned subscription ID and minimum renewal sequence in addition to product C3 trust, and checks the selected genuine signed product PLUS currently selected Ed25519 membership on **each GET**. Deep links `/local/error`, `/local/engine`, `/local/library`, `/local/books`, `/local/skillbook-run`, `/local/review`, `/local/evolution`, `/local/guide/...` are mapped server-side, not merely hidden from the menu. Unrecognized /local routes cannot claim authorized membership. The launcher now requires subscription ID and minimum renewal sequence. A small on-device dark themed /local/membership status page displays only the verified tier, billing cadence, period end and offline lease deadline. The signed member can view status after expiry/revocation, but all paid deep links remain denied. It never renders account hashes, key material, payment receipts or customer names. QA staging UI without a real membership is NOT a paid customer service.

## Renewal, cancel, revoke, no reinstall

New module `customer_membership_recipient_v01.py` verifies the existing signed product and imports a higher-sequence signed membership snapshot into a versioned directory, then atomically changes a pointer only after checking both real Ed25519 proofs. The approved stable C3 product-artifact token is distinct from this monthly/annual membership lease, so an ordinary renewal changes just the member snapshot and does not reinstall wheel binaries. It rejects lower renewal sequences, same-sequence changes, unknown recipient-root files and tampered local snapshots. Customer files and the installed product slots are not deleted or overwritten for a renewal. The importer CLI accepts only the explicitly bounded `UCIE_SIGNED_MEMBERSHIP_INBOX/member.json` and `member.sig.json` beside the intended `UCIE_PRIVATE_RECIPIENT` root (the owner must arrange safe private transport). The separately pinned minimum renewal sequence is ESSENTIAL: the local mutable pointer alone cannot defend against a deliberate offline disk rollback.

Real cancellation and refunds happen at the **payment provider and customer contract layer**, not by client changing text. Once cancellation-at-period-end is authenticated externally, the owner signs an updated state with a larger sequence and the device imports it. Immediate suspension/revocation behaves likewise. When the machine remains offline, those changes cannot propagate instantly; the short signed access lease bounds that window. Simply editing or copying a JSON membership file never confers rights without owner Ed25519 signature.

## Production owner signing / payment truth boundary

Module `customer_membership_owner_sign_v01.py` needs exact individual owner Windows3.15 interactive consent and an existing key under ignored `.build_keys`, plus human-approved original third-party LICENSE/NOTICE, first-party SkillBook/IP rights, OpenSSL Nov 10 five LOW CVE risk disposition (the fixed cryptography50.0.2 wheel must NOT be falsely marked patched), current designated customer private contract, and independent SHA-pinned owner-reviewed actual provider billing event with recurring-payment disclosure/consent confirmation, including the current short lease issue timestamp. The signer verifies the signature using the independent PUBLIC key and writes the signed pair only to ignored owner-local `downloaded`, never to GitHub/Slack. A human-confirmed provider event is NOT a cryptographically verified provider webhook; don't claim real payment capture merely because a Boolean was approved.

**NO live merchant/payment provider is selected or connected.** Therefore recurring charges, refunds, invoice issuance, customer cancellation portal, payment event webhook verification, onboarding/identity/KYC, secure trusted-time anti-rollback, seat registry, self-service auto renewal, tax/legal customer notices and actual production deployment are **NOT COMPLETE**. Implement a provider-specific authenticated webhook and owner server ledger ONLY after actual merchant credentials, contractual terms, tax and consumer-law review. Never accept an unsigned client payment status as authorization. No operational SQLite, hourly miner, customer code, scheduler, private key or other project is accessed here.

## Test contracts

New owner Windows test modules must execute signed EDS with EPHEMERAL test keys ONLY:
- `test_ucie_membership_subscription_v01.py`: 25 cases signed monthly/annual calendar rights, offline 35-day lease expiry and refresh, tiers, cancellation, grace, revocation, fake signatures, wrong recipient/product, no payment-provider claims.
- `test_ucie_membership_recipient_v01.py`: 16 cases atomic import, no reinstall renewal, replay/sequence, revocation, cancellation, wrong product, no customer data deletion.
- `test_ucie_membership_owner_sign_v01.py`: 11 cases legal owner/receipt/recurring charge consent SHA structure and private-key read-before-consent denial.
- `test_ucie_membership_local_http_v01.py`: 7 actual loopback HTTP tests on synthetically signed membership, tiered direct paths, no token, cancellation, revocation and renewal without reinstall.
- Existing 16 lifecycle tests plus all vendor-inclusive Windows installation/signed A/B/rollback QA must continue PASS. Native CI must run new 59 tests with zero skips INSIDE actual installed four-wheel product and cryptography Windows ABI. CI uses synthetic keys and ephemeral developer-owned data ONLY.

## Actual customer commercialization gates — honesty required

1. Existing owner actual vendor wheel SHA 3/3 and 5 LICENSE text SHA/15,755bytes are **DONE**; user-provided actual owner CLI. Human vendor/NOTICE, first-party/SkillBook rights, OpenSSL LOW CVE independent security approval still PENDING.
2. Real recurring payment processor account, payment provider selection, webhook signature verification, tax/renewal/withdrawal disclosures, prices and paid membership T&Cs are NOT CONNECTED or finalized. They require a specific merchant and owner/customer agreement.
3. Actual owner product-private Ed25519 membership and customer entitlement not issued; no key generated or accessed. Real designated customer's signed contract and physical Windows accepted pilot still NOT DONE. CI VM is NOT physical independent acceptance.
4. UCIE remains **subscription-first proprietary software** owned by the rightful individual owner now, with future legal company transfer only after incorporation. Customer owns own work outputs and gets a time-bounded service license, not a transfer of UCIE intellectual property. Third-party open-source licensing rights remain intact.

**Current status**: SUBSCRIPTION_ENGINE_TECHNICALLY_IMPLEMENTED_AND_TESTED (once exact CI is green), LIVE_BILLING_AND_CUSTOMER_RELEASE_NO_GO.