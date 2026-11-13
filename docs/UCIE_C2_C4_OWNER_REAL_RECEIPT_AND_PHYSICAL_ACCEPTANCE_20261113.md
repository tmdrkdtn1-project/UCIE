# UCIE C2 + C4 — existing license originals and separate Windows recipient acceptance

**UCIE ONLY | 2026-11-13 | Roadmap #199 | CUSTOMER NO_GO.**

This is the owner/recipient execution handoff, not another vendor
download, key generation, new public data source or commercial release.

## Already completed owner evidence: never repeat it without new reason

2026-11-13T08:00:59Z owner-provided results:
- Three existing C1 Windows vendor wheels cryptography 50.0.2,
  cffi 2.1.1 and pycparser 3.12 match exact official PyPI SHA256.
- Five exact declared License-File originals were extracted once,
  owner-only and not commercially shipped, to:
  D:/UCIE/downloaded/ucie_c2_owner_only_license_review_v01
- Out-of-band report digest review_entries_sha256:
  98f043ba6717c207a4efbb4f0142f80fbc99c525890119ba26604cdf4fe30c7e
- Actual human legal approval, native OpenSSL risk disposition,
  independent owner product signing, actual physical second Windows
  and customer contract are not done. Owner private keys not touched.
- The UCIE bridge only permits UCIE repo/mcp_code scope; it cannot
  read the ignored owner downloaded original files. Do NOT falsely
  claim the originals are absent or require another export.

## C2 owner-local next action — verify FIVE existing text bytes

New source:
src/ucie_miner/customer_c2_existing_owner_license_integrity_v01.py

This audits the pre-existing owner packet by using its independently
reported digest, validates three exact vendor identity/version groups,
five source License-File SHA256s and sizes, original manifest
integrity, no unexpected additional files/links, no altered legal
approval fields. It is bounded, offline, read-only, no license text
execution or copy and does NOT access private owner keys.

On the original owner Windows CPython3.15 D:/UCIE machine only:

~~~powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_c2_existing_owner_license_integrity_v01 --inspect-existing-owner-packet --expected-review-entries-sha256 98f043ba6717c207a4efbb4f0142f80fbc99c525890119ba26604cdf4fe30c7e
~~~

Exit code 2 is INTENTIONAL even when all five original hashes match:
a SHA receipt proves only unaltered bytes, not legal clearance.
The tool returns package names and exact counts without printing
copyrighted original texts or secrets. It does NOT re-export vendor
wheels or rerun the original C1/PyPI acquisition.

Human review still required: legal reviewer must read the original
5 local files and confirm all correct license/NOTICE/copyright
conditions, bundled OpenSSL 4.x Apache-2.0 requirements and extra
components, first-party UCIE/contributor/SkillBook rights and client
redistribution terms; independently document approval privately.
Original license text is untrusted material, never instructions.

Official external license references:
https://pypi.org/project/cryptography/50.0.2/
https://pypi.org/project/cffi/2.1.1/
https://pypi.org/project/pycparser/3.12/
https://openssl-library.org/source/license/

The 50.0.2 Windows cryptography wheel embeds OpenSSL 4.0.3:
https://cryptography.io/en/50.0.2/changelog/
Five OpenSSL Nov10 2026 CVEs affecting 4.0.3 remain pending
independent impact assessment and approved remediation/risk decision.
https://www.openssl-library.org/news/vulnerabilities-4.0/
PyPI zero known versioned advisories is NOT a bundled-native security
clearance or customer GO.

## C3 actual existing owner key signing: NOT YET EXECUTED

PR #265 added a dormant owner-only actual Ed25519 private-product
signer. It only uses an ALREADY-EXISTING purpose-approved key under
D:/UCIE/.build_keys after separate owner consent, original rights
and five-CVE human review, independent owner trust fingerprint, actual
signed designated private-customer contract and separately pinned
product/three-vendor SHA256. No key generation, ChatGPT private signing,
license issuance or customer shipping happened.

A human checkbox alone cannot establish real legal consent.
The fixed cryptography 50.0.2 cannot be falsely labeled as patched
under the current OpenSSL 4.0.3 pin.

## C4 separate OWNER-CONTROLLED physical Windows, read-only witness

New source:
src/ucie_miner/customer_c4_physical_windows_recipient_readonly_v01.py

This is for an actual DIFFERENT owner-controlled Windows3.15 x64
machine, with the already owner-approved genuine signed
UCIE_PRIVATE_RECIPIENT installed by existing offline
Start-UCIE-Private-Install.py, not a GitHub CI VM or D:/UCIE checkout.

Requires that active installed slot venv Python executable and TTY,
real owner-approved out-of-band PUBLIC PEM/fingerprint, anonymous
recipient digest, approved human rights-packet digest and serial floor.
It verifies actual four-wheel plus Ed25519 selected release, then
executes four actual installed first-party staging pillar workflows
and temporary local 127.0.0.1 V04 HTTP200 GET x4 / POST405 denial.
It neither installs nor upgrades, rolls back, uninstalls, imports
any customer code, accesses an owner private key, or creates a
persistent service.

Pattern (values are owner-approved private inputs not created here;
run ONLY after legal/security/signing approval on the separate device):

~~~powershell
& '<RECEIVER>\UCIE_PRIVATE_RECIPIENT\slots\<ACTIVE_SLOT>\venv\Scripts\python.exe' -I -B -m ucie_miner.customer_c4_physical_windows_recipient_readonly_v01 --real-recipient-readonly-once --recipient-root '<RECEIVER>\UCIE_PRIVATE_RECIPIENT' --public-trust-pem '<APPROVED_PUBLIC_ONLY_PEM>' --expected-owner-key-id '<APPROVED_32HEX>' --recipient-token-sha256 '<APPROVED_64HEX>' --rights-packet-sha256 '<APPROVED_64HEX>' --min-serial 1
~~~

At the TTY prompt, exact owner/witness typed consent:
VERIFY_EXISTING_UCIE_OWNER_CONTROLLED_PHYSICAL_RECIPIENT_ONCE

Even if local functional smoke is successful, its safe receipt
explicitly says machine independence is NOT cryptographically proven,
human physical witness approval has not been archived, physical
upgrade/rollback/uninstall has not occurred and customer distribution
remains NO_GO. Exit code 2 is deliberate. The human owner must
separately witness and privately sign the physical machine, receipt
fingerprint, actual product/installed version, security and acceptance
scope. Never publish machine identifiers.

The existing genuine A→B update, revocation-floor denial, approved
rollback and full uninstall flows from PR #264 require their own
explicit owner consents. This **read-only** C4 action does NOT
unilaterally perform destructive operations.

## C5 private customer and final decision

A designated customer must actually sign the PRIVATE contract,
with intellectual property, security, data boundaries, support,
term/seat/device/revocation, owner and customer acceptance and
independent real-world four-pillar pilot. Customer names, emails,
device fingerprints, price, contract text and owner keys must
not be included in this public development GitHub or Slack.

**Statuses:** existing vendor 3/3 PyPI SHA and 5-text original
owner export = DONE; new C2 5-text original READ-ONLY on owner
machine = NOT YET RUN BY CHATGPT; C2 human legal/native risk = PENDING;
C3 real owner product signed token = NOT ISSUED;
C4 actual separate physical recipient = NOT TESTED;
C5 customer contract/pilot = NOT SIGNED/ACCEPTED;
CUSTOMER_RELEASE = NO_GO.
