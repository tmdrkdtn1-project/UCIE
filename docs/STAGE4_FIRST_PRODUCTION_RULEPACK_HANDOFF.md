# Stage 4 — first public prevention Rulepack handoff and release gate

## What is really complete vs. forbidden to call complete

The operator verified the first REVIEW_ONLY signed Rulepack (serial 1) on
Windows, SHA256 scanner compatibility was corrected for PowerShell 5.1, and
Windows/Linux CI independently observed the CPython 3.15.0 flag behavior.
**A verified review-only signature is not a production authorization.**

The new first-rule production contract has two **separate** signing
authorities:

1. **Independent security/QA reviewer**: after real examination of the
   *first-party UCIE scanner*, applicable public sources, licensing and
   independent behavioral/regression evidence, signs the exact canonical
   `UCIE_STAGE4_INDEPENDENT_QA_ATTESTATION_V1` JSON with a **QA-owned key**.
   This act MUST NOT be performed by the UCIE developer, scheduled miner,
   CI fixture key, or owner acting as their own independent reviewer.
2. **UCIE owner**: checks QA identity and key fingerprint through an
   out-of-band verified channel; signs a new release with a **distinct
   production private key** only after explicitly authorizing production.

A recipient supplies **two independently established public trust anchors**:
the owner production public key and the QA public key. Both signatures,
scope, rule digest, source/merge reference, time limit and minimum serial
must pass. A signature proves possession of a key, **not** human
independence, reviewer competence, sufficient tests or legal authorization.
Real independent QA remains **NO-GO** until those actions actually happen.

## Exact acceptance criteria for this first, limited release

- **Scope:** `PUBLIC_ONLY_MANUAL_STATIC_SCAN`. No private source, connected
  apps, user files, project integrations, filesystem traversal, executables
  from external repositories, auto-fix, automatic promotion or OS scheduler.
- **Rule:** only `PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO` and immutable
  upstream `python/cpython#159014` merge
  `91248026c8a41910098032dd23f9a05ad2d9b513`.
- **Evidence checked by real human reviewer:** first-party
  Windows/Linux CPython 3.15.0 flag results, first-party Windows PowerShell
  5.1/7 static scanner + consumer tests, source ownership and the actual
  relevant licensing obligations. No upstream C code is redistributed.
  Green CI alone does **not** grant approval.
- **Independent QA attestation fields:** exact `EXPECTED_QA` in
  `src/ucie_public/production_release.py`, plus `reviewed_utc` (UTC
  ISO-8601 with Z) and `qa_key_id` (SHA256 fingerprint of raw QA
  Ed25519 public key, first 32 lowercase hexadecimal characters).
  The four reviews must be `PASS`, human decision `APPROVED`.
  The reviewer signs **canonical UTF-8 JSON bytes** with a detached raw
  Ed25519 signature exactly 64 bytes. The attestation expires after 30 days.
- **No false PASS:** developer/owner must not fill in QA PASS themselves.
  Neither test fixtures nor our code certify the reviewer independently.
- **Owner action:** independent `production` key (never reuse
  `private_prevention.pem`), manually invoke signed-release command using
  the QA signature, QA trust and an explicit confirmation; no background
  signing. The package lasts at most seven days; no overwrite.
- **Recipient:** verify both keys out of band and use
  `verify-production --min-serial <trusted minimum>`. The consumer
  `ucie_signed_production_scan.ps1` parses only operator-supplied
  **public/synthetic** PowerShell text and never executes it.

## Independent reviewer handoff

The owner provides only public UCIE repository references, publicly
approved CPython evidence and CI run links. **Do not send** the owner's
private key, local project files, runtime databases, personal information
or unrelated projects.

The independent reviewer independently acquires the public UCIE Python
utilities in their own environment and, **after** a genuine PASS review,
creates a separate QA Ed25519 key and signed claim. A possible first-party
signing flow executed **only by the independent QA** is:

```python
from pathlib import Path
from datetime import datetime, timezone
from ucie_public.rulepack import (
    canonical_json, generate_keys, _private_key, key_id,
)
from ucie_public.production_release import EXPECTED_QA

# Run ONLY on an independent QA-owned machine after actual QA signoff.
qa_private, qa_public = generate_keys(
    Path("qa_keys"), purpose="qa")
secret = _private_key(qa_private)
claim = dict(EXPECTED_QA)
claim["qa_key_id"] = key_id(secret.public_key())
claim["reviewed_utc"] = datetime.now(timezone.utc).replace(
    microsecond=0).isoformat().replace("+00:00", "Z")
raw = canonical_json(claim)
Path("qa_attestation.json").write_bytes(raw)
Path("qa_attestation.sig").write_bytes(secret.sign(raw))
# Transfer ONLY signed JSON + detached signature + qa PUBLIC key.
```

QA should not execute this until the independent check is genuinely
complete. QA private key stays with QA; authenticate the QA public-key
fingerprint through a separate channel.

## Owner-run commands after legitimate QA approval (not yet executed)

From `D:\UCIE`, with `PYTHONPATH=D:\UCIE\src` and only after this
branch is merged and independently reviewed:

```powershell
$py = 'D:\UCIE\.venv\Scripts\python.exe'
& $py -B -m ucie_public.cli keygen-production --out 'D:\UCIE\.build_keys\production'
& $py -B -m ucie_public.cli publish-production `
  --owner-private 'D:\UCIE\.build_keys\production\private_production.pem' `
  --qa-claim '<independently supplied QA attestation JSON path>' `
  --qa-signature '<independently supplied QA detached signature path>' `
  --qa-trust '<QA public key independently verified path>' `
  --output 'D:\UCIE\build\UCIE_First_Public_Production_v1.zip' `
  --serial 1 --confirm AUTHORIZE_UCIE_FIRST_RULE_PRODUCTION_SIGNING
& $py -B -m ucie_public.cli verify-production `
  --pack 'D:\UCIE\build\UCIE_First_Public_Production_v1.zip' `
  --owner-trust 'D:\UCIE\.build_keys\production\public_production.pem' `
  --qa-trust '<QA public key independently verified path>' `
  --min-serial 1
```

Never invent or submit fake QA approval. Recipient must preserve its own
highest trusted serial outside this package; passing `--min-serial 1`
does not provide cross-device rollback tracking. Key revocation and
automatic project distribution are **not** implemented or implied by this
limited, offline, manually distributed public-only release.

**Current release status: NO-GO until genuine independent QA and owner
authorization.** CI synthetic two-key fixtures confirm protocol behavior,
not an actual independent security verdict or published package.
