# UCIE B3/B4 — signed offline Windows full-product installer, A/B release slots and gated Local V04

**UCIE-only — 2026-11-13 KST. User-facing product release is still NO_GO.**
This document replaces repeated incremental planning for the installer.
It is one contiguous implementation/rehearsal handoff, not a legal
contract, an actual designated-customer entitlement or permission to
distribute vendor binary wheels.

## Actually implemented software

First-party module:
src/ucie_miner/customer_private_offline_lifecycle_v01.py

- Build an actual **private technical candidate directory** named
  UCIE_PRIVATE_BUNDLE from an exact current first-party wheel, three
  pinned C1 vendor wheels and a separately supplied detached customer
  entitlement signature. Directory includes 4 real wheel files,
  canonical integrity manifest, SPDX-2.3 inventory (licenseDeclared
  NOASSERTION), fixed NOTICE_REVIEW_REQUIRED.txt and the detached
  entitlement bytes. This intentionally does not give legal clearance.
  It does not download code, upload, distribute, create keys or infer
  real owner approval.
- Re-read every wheel ZIP+PEP427 RECORD, verify SHA256, validate the
  canonical manifest and SBOM, check the genuine purpose-separated C3
  Ed25519 signature against a **separately provisioned owner PUBLIC
  key/fingerprint**, caller-accepted minimum serial, recipient token
  SHA256 and rights packet SHA256. No private PEM is ever read.
- Install or update from a verified bundle under a **separate**
  UCIE_PRIVATE_RECIPIENT folder, not D:/UCIE and not a project checkout.
  The versioned/signature-bound slot has its own Windows Python3.15
  venv with a real **--no-index --require-hashes** 4-wheel dependency
  resolver, pip check, all 4 installed first-party workflows, and
  Local V04 127.0.0.1 GET+POST smoke. A new slot is activated by an
  atomic active.json pointer only AFTER the install checks succeed.
  Any failure leaves the previous active slot unchanged; abandoned
  new slot requires explicit human review before retry.
- Real product A version 0.1.0 and **source-distinct B 0.1.1** are both
  allowed in the purpose-separated C3 verifier only when the
  independently expected product version matches the signed record.
  Wrong version/customer/wheel SHA/rights packet, expired owner
  signature, replay and serial-floor downgrades fail closed.
- Client work surface: the installed recipient contains
  Launch-UCIE-Private.ps1. It accepts the independently approved
  PUBLIC trust key path and SHA pins at each invocation, resolves
  only the current 16-hex slot, starts the active slot's own
  installed Python and serves **127.0.0.1 only**. The new
  customer-specific Local V04 handler **rechecks the signature and
  actual on-disk wheel hashes before every HTTP GET**. Forged or
  expired material returns HTTP403; no owner-only D:/UCIE main()
  override or Windows background service registration is used.
- Rollback switches the pointer back to the still-installed previous
  signed slot **only after revalidating it using the CURRENT
  independently provided serial floor**. A revoked old signature
  can never silently reappear by selecting an old directory.
  Technical uninstall requires a distinct literal consent and
  removes only bounded registered slots, leaving the dedicated
  recipient directory intact; unknown root files block deletion.
  Original owner checkout/runtime DB/schedulers/C40/Cloudflare remain
  outside the supported path.

## Repeatable actual Windows technical acceptance

Single existing B3/B4 full-vendor CI is extended, NOT copied into
another repetitive PR. It installs the current first-party wheel and
official SHA/RECORD-checked native versions cryptography 50.0.2,
cffi 2.1.1 and pycparser 3.12, and exercises 4 pillars/V04, removal
and reinstall on disposable Windows.

In that **same workflow**, while all native vendors are installed,
it constructs source-distinct A0.1.0/B0.1.1 wheels, signs their
customer-bound metadata with ONE throwaway Ed25519 key kept in
CI memory, builds 2 real 4-wheel candidate directories, and uses
the actual customer lifecycle code to perform:

A offline install → signed active local UI HTTP200 + tampered
signature HTTP403 + restoration → B offline install → deny
revoked-serial A rollback → valid independent-serial A rollback
→ valid B recovery → actual technical uninstall of both venv
slots → verify no inherited owner data, no customer GO.

The 16 new lifecycle tests, 18 existing C3 customer tests and
4× Windows/Ubuntu standard matrix must execute with **zero crypto
skips** in native-equipped recipient. All steps must report
accurate SHA-anchored CI results; a job that has not run is NOT PASS.

## Actual owner/physical customer release blockers

The following are not fulfilled by any CI synthetic fixture, a
technical SPDX inventory, a rights-packet hash or a green disposable
GitHub Windows VM:

1. C0 independently approved complete SkillBooks and all four
   pillars as actually used by designated customers.
2. C1 owner-finalized commercial installer identity/Authenticode
   signing, production version policy, operator/user support,
   version migration and repair across real customer storage.
3. C2 independent first-party and third-party LICENSE/NOTICE/SBOM,
   redistribution/legal/security and publisher provenance review.
4. C3 owner's already existing genuine appropriate signing key
   proof, separately pinned customer PUBLIC trust, customer contract,
   revocation policy, real customer-specific entitlement issuance.
   No key creation is required merely because ChatGPT cannot access
   ignored owner key paths.
5. C4 a distinct owner-managed physical Windows recipient with
   real signed customer content and complete install/upgrade/
   rollback/uninstall/customer-use acceptance, not GitHub CI.
6. C5 actual designated customer pilot, contractual/business
   approval and explicit final commercial GO.

**Customer distribution remains NO_GO** until external evidence and
owner approval complete. Do not ship the ephemeral vendor binaries
created on a public GitHub runner. The existing 18 modified tracked
D:/UCIE files and operating public miner are preserved.

## Current authoritative links

Roadmap: https://github.com/tmdrkdtn1-project/UCIE/issues/199

The merged prior release-engineering base:
https://github.com/tmdrkdtn1-project/UCIE/pull/263

This implementation must be verified from its exact tested PR SHA
and merged only after both full installed Windows and standard
cross-platform CI pass.


## Standalone Windows customer-side technical bootstrap (no prior UCIE)

Every **technical** UCIE_PRIVATE_BUNDLE now contains
Start-UCIE-Private-Install.py, copied byte-for-byte from the first-party
wheel's reviewed Python source and checked again against its SHA-pinned
resource, alongside exactly four real wheels, canonical manifest,
SPDX inventory, rights-review HOLD notice and detached signed
customer entitlement.

An independently trusted Python 3.15 Windows interpreter can run
this standalone standard-library script with:
- --bundle <absolute UCIE_PRIVATE_BUNDLE>
- --recipient-root <absolute UCIE_PRIVATE_RECIPIENT>
- --product-version 0.1.0 (or separately authorized 0.1.1)
- --expected-product-sha256 <owner independently confirmed wheel SHA256>
- --expected-cryptography-sha256 <independently approved hash>
- --expected-cffi-sha256 <independently approved hash>
- --expected-pycparser-sha256 <independently approved hash>
- --public-trust-pem <owner-approved PUBLIC key path>
- --expected-owner-key-id <independently confirmed 32-character ID>
- --recipient-token-sha256 <recipient-specific SHA256>
- --rights-packet-sha256 <separately approved rights packet SHA256>
- --min-serial <approved revocation floor>
- --consent UCIE_PRIVATE_OFFLINE_TECHNICAL_RECIPIENT_INSTALL_ONCE

Example syntax (technical QA only, NOT an instruction to ship):
```powershell
& '<existing-Windows-Python-3.15>' -I -B '<approved-bundle>\Start-UCIE-Private-Install.py' --bundle '<approved-bundle>' --recipient-root '<independent-recipient>\UCIE_PRIVATE_RECIPIENT' --product-version 0.1.0 --expected-product-sha256 '<approved-hash>' --expected-cryptography-sha256 '<approved-hash>' --expected-cffi-sha256 '<approved-hash>' --expected-pycparser-sha256 '<approved-hash>' --public-trust-pem '<approved-public-PEM-path>' --expected-owner-key-id '<approved-32hex>' --recipient-token-sha256 '<approved-64hex>' --rights-packet-sha256 '<approved-64hex>' --min-serial 1 --consent UCIE_PRIVATE_OFFLINE_TECHNICAL_RECIPIENT_INSTALL_ONCE
```

The entry script checks **all 4 independently supplied SHA256 pins
BEFORE installing or importing ANY downloaded wheel**. It then creates
a disposable hash-locked verifier venv and installs only the 3 approved
vendor wheels without a network or sdists. From inside that ephemeral
native-equipped verifier it ZIP-imports the independently pinned
first-party wheel, requires a genuine C3 purpose-separated Ed25519
customer signature, and calls the existing full offline 4-wheel slot
installer. The disposable verifier is deleted. A failed consent,
wrong hash, wrong owner PUBLIC key or invalid signed recipient must
not create/activate a customer product.

After a legitimate technical install, the recipient has
Launch-UCIE-Private.ps1; its explicit public trust parameters
are required every launch and the installed active slot rechecks
the signed entitlement and all wheel hashes on EVERY GET. There is
no automatic client launch or background service registration.

**Installer distribution itself must be authenticated out of band**;
these code checks cannot prove that an installer script was delivered
by the owner rather than a substitute. Current test-only public GitHub
source and SHA receipts do not grant redistribution rights for vendor
binaries or permission to issue/sell customer entitlements.

Acceptance also includes executing this exact standalone script in
a newly created disposable Windows receiver with no UCIE package
preinstalled, failing a wrong vendor SHA without creating the
recipient, and actually installing/uninstalling the signed A product.
This is NOT acceptance of a different physical owner-managed device.
