# UCIE W09 SkillBook 001 — release readiness (NO_GO), 2026-11-05

PROJECT=UCIE ONLY
LIFECYCLE=FIRST_PARTY_DRAFT_NOT_APPROVED
BROWSER=W09_RELEASE_GATE_PLAN_ONLY_NO_RECEIPT

## Purpose

Validate that the existing W08 first-party **synthetic** nine-case receipt
matches the exact current UCIE-authored \`skillbook_scandir_recipe_v01.py\`
source and Python documentation pin, while explicitly keeping independent QA,
rights, security review, owner approval, signing, release and all exports
**disabled**.

This is a **readiness/denial gate**, not a ZIP/package implementation,
source-code review certificate or authorization. The canonical JSON SHA-256
means a record is unchanged against its declared digest, NOT that a
third party independently proved test execution.

## Fixed checks

- All W08 fields and booleans must match a known bounded contract; extra
  approval flags, missing fields and noncanonical inputs are rejected.
- Recompute the receipt SHA-256 over canonical W08 JSON, excluding
  \`receipt_sha256\`.
- Check nine precisely ordered \`PASS\` synthetic case IDs; no skipped
  tests, bool-as-int counts, or changed test identities accepted.
- Check exact UCIE first-party recipe file SHA-256 against receipt. The verifier
  reads **only that fixed module source file**, not caller paths or private data.
- Verify official documentation digest, source registry, W08 fixed SkillBook
  ID and unapproved product state. A documentation pin is *not* proof of
  future release applicability or whole-system behavior.
- The verifier never accepts user-supplied file paths, never writes a ZIP,
  creates no signing keys, publishes nothing, and cannot self-approve.

## Blockers always stay open

1. Exact-head full 4-environment CI independently confirmed
2. Independent external repeat/functional verification
3. Security review and OS/platform threat-model confirmation
4. Ownership, licensing and redistribution rights
5. Explicit owner release authorization
6. Package signature and publication authorization

Even when receipt verification succeeds, the machine status is
\`FIRST_PARTY_RECEIPT_REPRODUCED_RELEASE_NO_GO\`, not \`APPROVED\`.
\`package_created=false\`, \`export_allowed=false\` and
\`portable_package_bytes_produced=0\` remain immutable.

## Manual on owner Windows PC

Default only displays blocked gates without executing W08:

    & 'D:\UCIE\scripts\ucie_skillbook_w09_preflight_v01.ps1'

Explicitly repeat W08 synthetic test and verify its receipt in memory:

    & 'D:\UCIE\scripts\ucie_skillbook_w09_preflight_v01.ps1' -RunSynthetic

The second command writes and deletes bounded test-only fixtures in the
system temporary directory; it does not scan real user folders or modify
the UCIE operating database. It prints a machine-readable QA provenance
report containing a report SHA-256.

Browse \`/skillbooks/release-gates\` (and \`.json\`) to view the **static**
blocker plan. Browser GET never executes a test or loads an owner receipt;
a browser page must not claim latest local W08/W09 PASS.

## Separate CI issue (must not hide)

The exact PR #177 W08 HEAD \`189fadd4874434cb10ca44480498415178d23d3a\`
failed Windows Python 3.13 CI twice due HTTP POST ConnectionAbortedError
\`WinError 10053\` in two different existing V02/V07 browser tests. W08
synthetic nine probes passed in those logs. The origin of the Windows
HTTP interruption remains unproven. CI complete-matrix signoff stays NO_GO.

No C40, scheduling, public miner, database or non-UCIE project changes.
