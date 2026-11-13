# UCIE C3.1 — existing-key offline signed metadata review (DRAFT)

## Change
The new local_public_pr_trusted_recipient_v01.py reuses existing C3 Ed25519 verifier, B2 metadata inspection, the V04 renderer and strictly unverified records. A separate GET /local/trusted-public preview never changes or relaxes the original unsigned /local/library and /local/evolution signed-sidecar HTTP400 gates.

## Existing keys ONLY
An owner may already have suitable keys. Their absence is NOT inferred from this PR. UCIE Admin's read-only tool cannot enumerate ignored secret folders. This change does NOT create, inspect, copy, replace, or export owner private keys.
The recipient consumes ONLY a separately owner-approved public PEM at UCIE/.build_keys/ucie_c3_public_metadata_owner_trust.pem, together with an independently accepted 32-lowercase-hex owner public key ID and a positive minimum serial. The source of these trust inputs is an out-of-band owner acceptance process, NEVER the capsule or signature itself.
The recipient also needs three separately placed PUBLIC-only files at its clean UCIE root: .ucie_b2_public_pr_metadata_v01.json, .ucie_b2_public_pr_metadata_v01.sha256, .ucie_c3_public_pr_owner_attestation_v01.json. Real private-key or real metadata export has NOT been invoked. Missing files or unmatched trust -> FAIL_CLOSED.

## Example owner-authorized command (not executed)
Only on an owner-managed clean recipient UCIE checkout with empty runtime, use an already installed compatible Python:

    <recipient-python> -B -m ucie_miner.local_public_pr_trusted_recipient_v01 --recipient-ucie-root <absolute-UCIE-root> --expected-owner-key-id <previously-approved-32hex> --min-serial <separately-accepted-number> --port 0

The CLI verifies before binding its 127.0.0.1 listener; every GET verifies the signature and trust again. No arbitrary paths in queries, POST, external network, key creation, private key reads, scheduled tasks, miner, C40, or database writes.

## What passes and what remains blocked
Actual Ed25519 validation can authenticate only possession of the specified key and exact PUBLIC metadata bytes. It does NOT independently establish that the owner approved the key enrollment or confirm upstream PR fix correctness, license/NOTICE clearance, independent security QA, customer entitlement, or release authorization. All imported rows remain UNVERIFIED_CANDIDATE_ONLY and manual approval controls remain disabled.

A recipient compromised clock can subvert expiry; owner-managed serial floors and key revocations require real out-of-band governance. This PR does NOT provision a trust anchor or claim a fresh independent second Windows recipient accepted it. C2/C4/C5 and customer GO remain NO_GO.

## Acceptance
Exact PR HEAD Windows/Ubuntu Python3.13+3.15 CI, zero-skip genuine cryptography test on a vendor-equipped runner, real loopback HTTP safety tests, prior C3/B2/V04 regression, and clean first-party-only installed wheel HTTP400 are required. CI must not be reported PASS before observed. No merge or owner source overwrite before verification and separate owner acceptance.
