# UCIE W10 v03 — Git commit ancestry and owner archive gate (READ-ONLY)

Date: 2026-11-16 KST
Scope: UCIE ONLY; isolated reviewer feature, no operating restore or customer release.

## Inherited source
- W10 v01 PR #296 main `a8be4639ca38eb6ff03d3b90d2e6ad86a14abf20`, W10 v02 PR #297 main `96691586bd02dd4ead1906176e2de814db2b094d`.
- Independently observed exact first-party source `src/ucie_miner/library_exact_index.py`: SHA-256 `6e27de83192b066f73b9574d2a591607bcc1bef9512b97f94c5bdd3af528ee7e`, Git blob SHA-1 `0f92ed46b68685e0edb98f4fc09c3846b5b8d2c6`. These are unchanged existing bytes, not evidence that they were previously deployed and backed up.

## New standalone function
`ucie_miner.w10_prechange_archive_attestation_v03.assess_prechange_archive`:
- Only two original W10 source basenames; strict owner UCIE Git root and 40-character immutable commit SHA.
- Uses read-only local Git ancestry (`merge-base --is-ancestor`), the exact commit tree entry (`ls-tree` mode 100644), its SHA-1 blob ID (`rev-parse`), bounded binary Git object bytes (`cat-file -s/blob`) and caller-pinned SHA-256.
- Reads **only** the conventional UCIE path `runtime/w10_owner_restoration_archive/<exact-basename>.prechange.bin`, if already present. No API/scheduler/DB/other-project reads or file creation in owner root, no automatic backup acquisition.
- If no owner archive, returns explicit `W10_OWNER_PRECHANGE_ARCHIVE_MISSING_NO_GO`. If archive bytes disagree with the pinned local Git source, raises fail-closed. A matching archive allows *temporary* v02 byte-roundtrip only if current committed code differs from historical commit bytes.
- Distinguishes local Git tree/blob verification from Git remote/signer authenticity, owner backup's capture time, actual prior deployment, approved candidate, functional and security regression, real W09 signed consumer QA and owner authorization. All latter approval flags remain false even for a matching archive.
- Fixed read-only Git subprocess commands and no candidate import/exec, network calls, Git checkouts/updates, task actions, rule promotion, signing, packaging or customer release.

## QA
- New synthetic UCIE-only Git fixtures with distinct prior/current commits and optional disposable archive, including commit ancestry, malicious/missing paths, SHA alterations, corrupted/oversized backup, CRLF checkout, no candidate delta, source-size denial, and exact real UCIE HEAD blob check.
- Any local/CI PASS is only first-party synthetic offline source/byte review, never independent human QA.
- GitHub Windows+Ubuntu Python3.13+3.15 CI on exact HEAD required before merge.

## Still required
1. Authenticated owner-held PRECHANGE archive from a truly deployed earlier source version, with exact immutable origin, backup timestamp and independent signed provenance; current code is not a replacement.
2. Independently reviewed source-linked proposal and changed code, version/license/negative security regression, behavioral acceptance, independent human QA.
3. Owner-controlled rollback authorization, disposable postrestore behavioral/W09 acceptance, and only then a separately approved operating procedure.
4. P11 network job6 REVIEW_REQUIRED 5/5 and base PublicMiner HTTP403 owner HOLD remain untouched. Automatic rule promotion, customer V1 release NO-GO.

STATUS=W10_V03_GIT_TREE_AND_OWNER_ARCHIVE_REVIEW_ONLY__HISTORICAL_DEPLOYMENT_NOT_ATTESTED__REAL_ROLLBACK_NO_GO__P11_HOLD__CUSTOMER_NO_GO

- Hardened Git scope: `.git` must be an in-root directory (external gitdir files/worktrees rejected). Git subprocess calls discard inherited `GIT_*` environment variables to deny `GIT_DIR`/`GIT_WORK_TREE`/Git config redirects. Additional synthetic negative tests check these boundaries.

## Independent CI regression correction

Initial GitHub Actions #43824211477: Ubuntu Python3.13/3.15 PASS; Windows Python3.13/3.15 failed four synthetic temp-root checks each because the first implementation compared `Path.resolve()` against `Path.absolute()` as if Windows' canonical path and displayed temporary path were identical. The check was stricter than the intended safety property. In commit `4abfd3bbc5bfcf3acc1bd62a4274b751a3994410`, only that nonportable spelling comparison was removed; exact UCIE root name, explicit root symlink rejection, in-root `.git` directory, Git-reported top-level match, allowed source path, immutable object bytes, and injected Git-environment rejection remain mandatory. Original failures remain recorded and are not reported as PASS. Re-run full CI on the corrected HEAD.
