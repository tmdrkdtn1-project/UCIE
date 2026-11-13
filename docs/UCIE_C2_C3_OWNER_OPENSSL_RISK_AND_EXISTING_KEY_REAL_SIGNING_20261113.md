# UCIE C2/C3 — 2026-11-13 official OpenSSL 4.0.3 review and existing owner signing readiness

**Scope UCIE only / Roadmap #199 / CUSTOMER_NO_GO.**

This is a source-grounded technical-security and human-rights review packet,
not legal approval, a real signed customer license or physical acceptance.

## Confirmed real owner evidence (already captured; no reruns)

At 2026-11-13T08:00:59Z, owner-provided CLI receipts state:
- Existing C1 vendor wheel bytes for cryptography 50.0.2, cffi 2.1.1,
  pycparser 3.12 match their three official PyPI file SHA256 digests.
- 5 exact license-text files extracted in the ignored owner-only folder;
  no external vendor binary exported. Legal human approval is still FALSE.
- PyPI cryptography attestation subject digest matched the official wheel
  digest; an INDEPENDENT Sigstore signature was not verified.
- PyPI per-version 3-package known active advisory count was 0 at that
  instant; embedded OpenSSL native vulnerabilities are not ruled out.
- These are user-provided CLI receipts; ChatGPT did not directly inspect
  the original ignored owner files.

## Official embedded OpenSSL advisory investigation

Cryptography's official 50.0.2 release confirms Windows wheel includes
statically-linked OpenSSL **4.0.3**.
https://cryptography.io/en/50.0.2/changelog/

OpenSSL official 2026-11-10 advisories:
https://www.openssl-library.org/news/timeline/
https://www.openssl-library.org/news/vulnerabilities-4.0/

| CVE | Official severity | Affected feature/precondition | First-party UCIE source observation |
|---|---|---|---|
| CVE-2026-88822 | Low | QUIC connected-socket peer auto-detection | No direct OpenSSL QUIC call found |
| CVE-2026-95691 | Low | QUIC client retransmitted CRYPTO frames | No direct OpenSSL QUIC call found |
| CVE-2026-88823 | Low | AES-GCM-SIV fragmented AAD with empty update | No AES-GCM-SIV call found; only normal AESGCM in native QA |
| CVE-2026-95692 | Low | AES-GCM-SIV nonstandard IV length through EVP cipher init | No AES-GCM-SIV/EVP init call found |
| CVE-2026-107496 | Low | CMS_encrypt with EC group-order 1, OpenSSL 4.0 explicit EC groups option | No CMS_encrypt or PKCS7 call found |

The official patch level for OpenSSL 4.0 series is 4.0.4. As of
2026-11-13 the official download page still listed 4.0.3 as latest 4.0
release and no patched cryptography Windows wheel was confirmed in the
official changelog. Do NOT guess that a fixed wheel exists, or silently
replace this C1 binary with an unapproved source or patched build.

The UCIE-only main source search covered exact targeted API identifiers:
AESGCMSIV: 0, CMS_encrypt: 0, pkcs7: 0, AESGCM: 3 first-party QA files.
GitHub QUIC search included 15 apparent approximate word matches, then
the actual returned source paths were read and no OpenSSL QUIC call
confirmed. This is ONLY a bounded lexical/direct-call observation.
Native vendor binaries, dynamically constructed calls and transitive
dependencies are not fully covered. **Exploit reachability remains
UNVERIFIED, not PROVEN_UNAFFECTED**.

C2 first-party module:
src/ucie_miner/customer_c2_bundled_openssl_advisory_v01.py
It embeds exactly these published fixed-pin facts without network,
database, key or scheduler access. Existing C2 public PyPI review now
includes the separate native OpenSSL five-CVE HOLD even if the top-level
PyPI version-vulnerability count is 0. Neither path ever emits security
approval or customer distribution GO.

## Human legal rights review; NOT a legal signoff

Published claims for reviewed exact versions:
- cryptography 50.0.2: Apache-2.0 OR BSD-3-Clause. Human must review
  the actual dual-license choice and included component notices.
- cffi 2.1.1: MIT-0. Review actual captured license and bundled components.
- pycparser 3.12: BSD-3-Clause. Binary redistributors must preserve
  copyright, license conditions, disclaimer and avoid endorsement.
- statically bundled OpenSSL 4.x: Apache-2.0, additional to the
  cryptography project's license/notice duties.
- UCIE first-party repo intentionally has no standard top-level LICENSE,
  with a designated-customer proprietary commercial objective in
  README/SECURITY. This is not enough to independently prove code and
  SkillBook ownership/contributor authorizations.

Original 5 owner-only License-File contents and full NOTICE obligations
require real human inspection. No customer contracts, rights-holder
names, private filenames/keys or full original license text should be
posted to public GitHub/Slack.

Official sources:
https://pypi.org/project/cryptography/50.0.2/
https://pypi.org/project/cffi/2.1.1/
https://pypi.org/project/pycparser/3.12/
https://spdx.org/licenses/BSD-3-Clause.html
https://spdx.org/licenses/MIT-0.html
https://www.openssl-library.org/source/

## Real C3 pre-existing owner key signing (DORMANT until actual approvals)

Module:
src/ucie_miner/customer_c3_owner_existing_key_product_sign_v01.py

It supports ONLY an existing owner Ed25519 PEM selected by basename in
D:/UCIE/.build_keys with matching separately approved PUBLIC trust PEM
and key ID. It rejects other projects, non-owner hosts, CI, missing
actual interactive owner consent, malformed product/vendor pins and
ambiguous filenames. It does not generate, rotate, export or transmit
any key.

The pre-existing exact C1 wheel receipt and actual 3 vendor SHA+PEP427
RECORD are checked offline. An approved existing product wheel under
D:/UCIE/downloaded must independently match the expected first-party
SHA and version 0.1.0 or 0.1.1. No new wheel download or installation.

**Mandatory C2/C3 human approval file:**
D:/UCIE/downloaded/ucie_c2_c3_owner_human_release_decision_v01.json

Exact required canonical fields:
- schema: UCIE_C2_C3_OWNER_HUMAN_RELEASE_DECISION_V01
- security_disposition: PENDING (denied by default)
- customer_distribution_authorized: false
- first_party_rightsholder_and_contributors_human_approved: false
- actual_vendor_license_notice_copyright_human_approved: false
- openssl_4_0_3_five_known_nov10_cve_risk_human_disposition_approved: false
- publisher_provenance_security_policy_human_reviewed: false
- private_product_signing_key_purpose_human_approved: false
- actual_designated_customer_private_contract_signed: false
- four_pillar_product_scope_human_approved: false

The owner/reviewer must actually substantiate all separate approvals.
Only a reviewed fixed-wheel or explicit documented restricted 5-CVE
risk-acceptance disposition is accepted:
OFFICIAL_PATCHED_WHEEL_VERIFIED or
HUMAN_ACCEPTED_DOCUMENTED_RESTRICTED_5_LOW_CVE_RISK.
All seven approval booleans must be true to allow signing. The
file SHA256 must ALSO match a separately provided expected SHA.
These human assertions remain owner-controlled and are not
independently validated by code as legal truth. No such approval file
was created by ChatGPT and NO real owner product signature was made.

When and only when approvals exist, an owner interactive invocation
provides the pre-existing private and public key BASENAMES, an
out-of-band approved owner key ID, actual first-party and each vendor
SHA, anonymous recipient-token SHA, human-decision SHA, serial and
the exact typed consent phrase:

OWNER_SIGN_UCIE_C3_EXISTING_KEY_REAL_CUSTOMER_ENTITLEMENT_ONCE

The signer checks the real Ed25519 detached signature against its
PUBLIC trust key before writing two files to a fresh owner-local
ignored directory, with an explicit NOT_REleased receipt. Never
put the signer key, real human approval decision file, customer
contract, customer identifying tokens or signed bundle into public
UCIE GitHub or Slack.

## C4 and C5 (real people/devices, not faked by CI)

C4: owner-approved physically separate Windows x64 CPython3.15
recipient with independently supplied approved PUBLIC fingerprint,
signed customer entitlement and exact 4-wheel package. Perform actual
C0 four-pillar use, local V04, signed A/B update, revoked rollback
denial, accepted rollback, full uninstall and independently signed
owner acceptance receipt. GitHub disposable VM result is not enough.

C5: actual designated customer's signed private proprietary contract,
term/seat/device controls, support obligations, legal/security approval,
bounded pilot and independent customer + owner signoff. No customer
name/price/email/contract text in this public repository.

**Current outcome:** Three real vendor hashes matched, five owner
license texts exported, five embedded OpenSSL CVEs documented,
real C3 existing-owner-key signing code added but NOT USED,
physical owner-controlled C4 NOT DONE, customer C5 NOT DONE.
CUSTOMER DISTRIBUTION REMAINS NO_GO.
