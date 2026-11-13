# UCIE C3 — public PR metadata owner Ed25519 authentication v0.1

## Scope: real cryptographic authentication, NOT customer release

The C3 module reuses existing first-party UCIE Ed25519 primitives backed by cryptography. It signs the B2 public candidate capsule SHA256 plus an explicit UCIE-only purpose, trusted owner key fingerprint, monotonic serial, issue UTC, and 30-day expiry. The signature authenticates possession of the correctly pinned owner key, NOT upstream fix correctness, independent third-party source verification, license clearance, human approval, or customer distribution. No release GO.

**No real owner private key was generated, opened, exported, signed with, or provisioned by this implementation.** Synthetic Ed25519 keys were generated only in test memory, and no real owner B2 source capsule was exported or uploaded.

## Owner-only signing is a separately authorized action, NOT performed

- Exact owner root: D:\UCIE; requires interactive Windows CPython 3.15 from D:\UCIE\.venv\Scripts\python.exe; fails for CI/automations.
- Dedicated owner key must already be safely provisioned at D:\UCIE\.build_keys\ucie_c3_public_metadata_owner_private.pem. No implicit key generation.
- Public candidate bytes must already exist under existing Git-ignored D:\UCIE\downloaded: .ucie_b2_public_pr_metadata_v01.json and its .sha256.
- Explicit fresh one-time owner consent text: UCIE_OWNER_SIGN_PUBLIC_METADATA_LOCAL_ONLY_ONCE. Separately preapproved 32-lowercase-hex owner key ID and positive serial required.
- Output is O_EXCL one-time-only: D:\UCIE\downloaded\.ucie_c3_public_pr_owner_attestation_v01.json. No overwrite, upload, transfer, network, DB write, process restart or customer package.

Owner syntax ONLY after the owner has explicitly provided and approved an actual key, fingerprint and the pre-existing public capsule:

    D:\UCIE\.venv\Scripts\python.exe -B -m ucie_miner.local_public_pr_owner_auth_v01 --owner-sign-once --serial 1 --expected-owner-key-id <approved32hex>

## Independent recipient verification (not executed with a real owner key)

Recipient must provision owner public key separately at its own UCIE/.build_keys/ucie_c3_public_metadata_owner_trust.pem. The expected fingerprint and minimum serial must come through an authenticated OUT-OF-BAND owner trust channel; not from the capsule, signature, same folder SHA, or self-declared key. An attestation signed with a different key, a stale serial, future-issued or expired issuance, noncanonical JSON/PEM, or modified candidate bytes MUST fail closed.

    <python-in-recipient-venv> -B -m ucie_miner.local_public_pr_owner_auth_v01 --verify-recipient --recipient-ucie-root <absolute-path-to-UCIE> --expected-owner-key-id <approved32hex> --min-serial 1

The result explicitly states signed_metadata_only=true, owner-key trust verified, but independently_verified_upstream_fix=false, license_cleared=false, human_approved=false, and customer_distribution_authorized=false. Offline verifier cannot prove real time, key revocation, or upstream PR release inclusion. Owner controls monotonic serial floor externally to prevent simple rollback.

## Existing Local V04 is intentionally unprivileged

A separate C3 attestation sidecar appearing next to B2 metadata without independent owner trust will return HTTP 400 FAIL_CLOSED, NOT silently downgrade to the unsigned preview. Normal unsigned preview remains UNVERIFIED_CANDIDATE_ONLY and /local/review denied. The browser does NOT automatically trust keys bundled with a candidate and does NOT claim production authorization.

## Acceptances & boundaries

- Owner Windows: genuinely execute ephemeral Ed25519 sign/verify, reject wrong key/fingerprint, tamper, duplicate keys, scope-forged release, bad serial and replay, stale/future time, malformed trust key. Test keys remain in memory only.
- Clean GitHub Windows Python3.15 first-party-only wheel: unchanged official-document GET8 and synthetic metadata GET3, plus forged C3 signature sidecar HTTP400; actual cryptography vendor verification NOT claimed in this no-vendor wheel.
- Existing full CI Win/Ubuntu Python 3.13/3.15 and owner bounded suites required for merge.
- External cryptography distribution review/NOTICE/security remains C2 NO_GO, independent owner-managed trust key acceptance, real signed recipient and C3 customer entitlement remain NO_GO, C4 full independent recipient/C5 customer GO remain NO_GO.
