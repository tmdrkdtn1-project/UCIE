# UCIE V3 C0/C1: first-party whole-component census and isolated lifecycle drill

**2026-11-11 KST | UCIE ONLY | Source + staging QA | NOT a customer product.**

Canonical owner roadmap: https://github.com/tmdrkdtn1-project/UCIE/issues/199

## Why this increment exists

The earlier `customer_offline_capsule_v01.py` already checks a wheel's
RECORD and one UCIE-authored four-pillar synthetic execution receipt.
Its own NO-GO statement says a wheel is **not** the entire Local V1
product: the browser UI, operator scripts, policy and documentation,
dependency wheels, signing, rights, approved books and recipient update/
rollback were not attested. This increment **does not repeat** wheel
validation. It creates a separate fixed **23-path first-party census**
and exercises file-content tamper checks, copy, candidate generation
switch, rollback and uninstall entirely under an automatically created
UCIE-specific temporary directory.

## Source-anchored C0 component matrix

The exact fixed repository file paths, sizes and SHA-256 hashes are
returned by `inspect_component_census(root)`. No customer code, user
file paths, SQLite, secrets, private repository, arbitrary global search
or external HTTP is an input. All paths remain within one UCIE Git
checkout, with symlink/path/budget rejection.

| Product area | Included in 23-file census | Current C0 exit judgement |
| --- | --- | --- |
| Error prevention | rule candidates, regression plans, guarded iterator | code present only; independence/rights/customer approval NOT inferred |
| Development engines and skills | capability trials and positive discovery | code present only; independent customer usage NOT accepted |
| Virtual Library and SkillBooks | catalogue, MCP/Python human guides + source-pinned playbook | drafts remain unapproved/export forbidden |
| Evidence-backed evolution | experience evolution + P11 closed loop | no customer update/rollback/canonical promotion acceptance |
| Local product UI | V04 owner app and V04 design | source included; not a portable new recipient service |
| Owner-only launch | Windows start/status/autostart scripts | **hard-coded D:\\UCIE owner paths, NOT customer-portable** |
| Product CLI preview | staging CLI and existing CLI | preview only, not signed commercial distribution |
| Docs/config/security | pyproject, SECURITY and canonical release notes | legal/security evidence still missing |

These 23 **selected** paths are not a transitive package closure.
Other importable modules, optional features, platform dependencies, a
compatible `cryptography` wheelhouse, real recipient configurations,
UI launch policy, genuine approved SkillBooks, NOTICE, full SBOM, and
customer license/keys need separate closure and review.

## C1 staging engine mechanics

`exercise_disposable_lifecycle(root)`:
1. Inspect exact first-party files, reject missing/zero/oversized/
   symlinked paths and compute a deterministic aggregate fingerprint
   from exact file SHA-256 + byte lengths. **This aggregate is not a
   Git commit, signed attestation, or the deployed product hash.**
2. Copy the source bytes and manifest into newly created disposable
   `generation_a`; independently verify every file and no extras.
3. Copy the same source bytes into `generation_b`, intentionally
   corrupt only one disposable copied file, reject activation on
   mismatch, and recheck the still-unmodified `generation_a`.
4. Recreate and verify `generation_b`, simulate the active-generation
   switch, then roll back the simulated selection to `generation_a`.
5. Remove the two generated slots and verify the temporary directory
   is empty. Python automatically deletes the entire scratch directory
   at completion.

**Important:** both generations contain identical actual source bytes.
The simulated update is an integrity/lifecycle control exercise, **not
a real software version upgrade**, installed customer package or
platform integration. No recipient, owner service, TaskScheduler task,
PublicMiner DB, C40, Cloudflare, user repository or customer directory
is modified. Do not copy this preview snapshot to customers.

## Developer-only commands on exact UCIE checkout

```powershell
$env:PYTHONPATH='D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_component_lifecycle_v01 --ucie-root 'D:\UCIE'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_component_lifecycle_v01 --ucie-root 'D:\UCIE' --disposable-lifecycle
```

A zero CLI exit means **this bounded developer-only operation completed
without integrity failure**, not customer readiness or source approval.
A failure prints a closed NO-GO status with exit 2 and no file contents.

## C0–C5 actual remaining gates (never silently waived)

- **C0**: four approved, non-draft customer-grade user journeys, with
  independent version/behavior/rights tests for each; this census alone
  does not attest them.
- **C1**: every imported module plus UI, portable startup, CLI, docs,
  correct pinned dependency wheelhouse, actual install/update/rollback/
  uninstall into a second clean Windows recipient. The 23-file subset
  and same-bytes generations are insufficient.
- **C2**: owner/rightsholder review, per-component SPDX/notice and
  dependency SBOM, security review and platform QA.
- **C3**: genuine signer custody and customer-specific entitlement in a
  protected private distribution channel, never the public UCIE GitHub
  repo. No key/license/customer identity generated here.
- **C4**: isolated real version A-to-B recipient lifecycle rehearsal,
  full non-draft four-pillar functional and negative tests.
- **C5**: expressly approved designated customer contract, accepted
  signed bundle and same-digest pilot receipt; separate final owner GO.

Overall verdict remains `UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_NO_GO`.
The 09:00 report stays paused; hourly approved public miner remains
independent and unchanged.

Acceptance tests: `tests/test_ucie_customer_component_lifecycle_v01.py`
(synthetic corruption/symlink/size/path failures and exact owner/clean
checkout census+disposable source-copy smoke). This does NOT require or
authorize a resident Local V1 restart.
