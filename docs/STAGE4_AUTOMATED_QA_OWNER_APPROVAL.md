# UCIE Stage 4 — Automated QA + Owner Risk Acceptance (public/manual only)

## Master-approved policy revision (2026-10-18)

An **external human reviewer is OPTIONAL**, not mandatory for the
narrow **PUBLIC_ONLY_MANUAL_STATIC_SCAN** owner-risk release channel.
The original `INDEPENDENT_QA_AND_OWNER_SIGNED` channel and its two
independent signatures remain available without bypass or downgrade.

The alternate channel is **AUTOMATED_QA_OWNER_RISK_ACCEPTED**. It
**does not claim** an independent human security audit or legal license
signoff. The owner must explicitly accept these limitations in a
separate signing action.

### What actually happens automatically

At owner signing time, `publish-owner-risk-release` **reads only two
bounded anonymous official GitHub API responses** for the specified
UCIE workflow run (run and jobs), refuses redirects and failed/ambiguous
runs, and requires:

1. UCIE repository `tmdrkdtn1-project/UCIE`, exact workflow
   `.github/workflows/stage1-offline-tests.yml`, `push` on `main`,
   status completed, overall result success.
2. Exactly four unique Windows/Linux × Python 3.13/3.15 jobs, all
   completed successfully.
3. Python 3.15 runtime behavioral probe successful on **both** Windows
   and Ubuntu; PowerShell 5.1 signed-review consumer and Stage4
   synthetic dual-key consumer successful on both Windows matrix jobs.
4. Workflow HEAD SHA must exactly match the clean, checked-out
   `D:\UCIE` `main` commit (read through fixed local Git queries).
5. The owner explicitly invokes the command with BOTH the dedicated
   production signing key and two different confirmation strings.

All verification is **fail-closed**. The unattended hourly miner cannot
generate any key, claim, package, signing action or distribution. Public
API evidence is normalized and included inside the owner-signed ZIP,
alongside a fixed one-rule payload. The ZIP is immutable, bounded, valid
seven days, serial-checked, not overwritable, never executes source and
never auto-applies fixes.

### What automated QA does not prove

- It cannot replace a real independent human security reviewer.
- It does not certify legal license rights or all future Python versions.
- It is not a verified upstream before/after C binary regression.
- It does not prove a source text snippet is permitted for scanning.
  Operators must supply ONLY permitted PUBLIC/synthetic text.
- GitHub's public API is consulted at **owner signing time**, but the
  **offline recipient** validates the **owner's signed claim** about
  that API result; this is not a separate GitHub cryptographic
  attestation. The recipient can independently view the public CI URL
  and verify the commit, if network is available.
- It does not provide cross-recipient persistent serial storage,
  license-legal approval, automatic task registration, auto-promotion,
  auto-fix or private-project integrations.

### Manual owner action — ONLY after merge and postmerge CI PASS

The owner must first compare the approved `main` commit and the actual
postmerge public GitHub workflow run ID independently. **Do not run
these commands with an arbitrary/invented run ID.**

```powershell
$root = 'D:\UCIE'
$py = "$root\.venv\Scripts\python.exe"
# Existing key generation is a one-time operation. It refuses overwrite.
$env:PYTHONPATH = "$root\src"
& $py -B -m ucie_public.cli keygen-production --out "$root\.build_keys\production"
```

This only creates a new **owner-only** production keypair; the private
key must remain on the owner PC. Its fingerprint should be distributed
to each recipient via an independently verified channel. **Never**
reuse the already-generated REVIEW_ONLY private key.

The user must separately decide to sign/issue and accepts the risks
by explicitly invoking this command, using the REAL verified run ID:

```powershell
& $py -B -m ucie_public.cli publish-owner-risk-release `
  --owner-private "$root\.build_keys\production\private_production.pem" `
  --output "$root\build\UCIE_First_Owner_Risk_Public_v1.zip" `
  --run-id <ACTUAL_POSTMERGE_MAIN_RUN_ID> --serial 1 `
  --confirm AUTHORIZE_UCIE_PUBLIC_MANUAL_OWNER_RISK_RELEASE `
  --accept-risk I_ACCEPT_NO_INDEPENDENT_HUMAN_QA_AND_NO_LEGAL_LICENSE_SIGNOFF

& $py -B -m ucie_public.cli verify-owner-risk-release `
  --pack "$root\build\UCIE_First_Owner_Risk_Public_v1.zip" `
  --owner-trust "$root\.build_keys\production\public_production.pem" `
  --min-serial 1
```

The owner should read the output and authorize any manual, public-only
distribution separately. A valid owner-risk pack is not an independent
QA-signed pack and cannot be fed to `verify-production` or
`ucie_signed_production_scan.ps1`.

The permitted manual consumer is
`scripts/ucie_signed_owner_risk_scan.ps1`, taking an explicit inert
`-SourceText` and only the first public approved rule. It never
executes its source text, reads projects or applies a change.

## Actual current status

This policy and implementation change can be merged only after complete
Windows/Linux CI succeeds. The operational pack has **not** been
issued from CI or by this conversation. Owner-key generation,
risk acceptance, signing, distribution and recipient operation are
all **manual owner decisions** after the code has been reviewed.

Record all release evidence as `AUTOMATED_QA_OWNER_RISK_ACCEPTED`,
not `INDEPENDENT_QA_APPROVED`. The historical independent-QA release
gate remains available for a later separately reviewed distribution.
