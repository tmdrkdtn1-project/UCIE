# UCIE V1.0 — public source observation receipts and review readiness

Date: 2026-11-01. UCIE ONLY. Owner-accepted V0.9 + PR #168 preserved.
One integrated development milestone; no change to existing collector or DB.

## Capabilities

1. **Real source observation, explicit owner action only**: V0.9 bounded
   anonymous approved public metadata and official-document HTTP response
   SHA checker executes for one exact source-linked candidate SHA ID.
   It does not execute third-party source or PR bodies, import packages,
   follow redirects, access private repositories or mix project data.
2. **Immutable-by-tool observation receipt**: single-candidate source-bound
   V0.9 results are rechecked, reduced to fixed status/identity metadata,
   SHA-256 hashed, and written to
   D:\UCIE\runtime\public_observations_v10\receipts
   using a lock and atomic rename. Repeated identical observations
   deduplicate. Unknown files, symlinks, changed source linkage,
   tampered integrity hashes and forged approvals fail closed.
   SHA self-hashes are not authenticated third-party signatures.
3. **Source replay**: after verifying the current Stage10/12/15 source
   handoff, the read-only view checks stored observations against
   public source identity, current revision and receipt integrity.
   Source metadata identity match is NOT upstream fix validation.
4. **Actual UCIE-owned regressions**: six fixed safe offline test
   cases verify repo allowlisting, loopback prohibition, unsafe citations,
   duplicate audit parameters, forged approvals and acceptance of genuine
   unverified observation structure. Their PASS means only UCIE's
   guard controls passed; none prove third-party fixes work.
5. **Review readiness report**: combines existing source audit,
   observation replay, offline guard results and safe fixed domain-specific
   review questions, with missing official release inclusion, independent
   upstream regression recipe, license and owner signature explicitly
   NOT_VERIFIED.
6. **Read-only local browser**: inherits V0.9 audit/candidate selection,
   search, comparison, back navigation and explicit public source check.
   Adds all-observation and per-candidate receipt views. No implicit network
   access or write on observation/health/search pages.

## What V1.0 does NOT claim

- Independent regression of an upstream bug fix: NOT PERFORMED.
- Release version applicability: NOT VERIFIED.
- License legal review: NOT PERFORMED.
- Security or owner signoff: NOT PERFORMED.
- Executable signed or automatically promoted Rulepack: ZERO.
- New scheduled tasks, cross-project source reads or operating DB writes:
  ZERO.
- SHA-256 checksums are integrity checks, not external attestation.
- GitHub CI proves UCIE software behavior with synthetic external responses.
  Actual owner Windows public fetch and receipt replay are separate checks.

## Owner exact-file installation

Install only these **nine new paths** after tested SHA-pinned merge, and
preserve ALL prior V0.1-V0.9 modules and local owner worktree changes:

- src/ucie_miner/library_observation_receipts_v10.py
- src/ucie_miner/library_browser_v10.py
- src/ucie_miner/library_safety_regression_v10.py
- src/ucie_miner/library_review_readiness_v10.py
- scripts/ucie_public_observation_record_v10.ps1
- scripts/ucie_library_browser_v10.ps1
- scripts/ucie_review_readiness_v10.ps1
- tests/test_ucie_observations_v10.py
- docs/UCIE_V10_OBSERVATION_REPLAY_READINESS_20261101.md

Never run blanket Git pull, reset --hard or clean in the owner repository.

## Owner Windows smoke and independent verification boundary

1. Safe offline synthetic tests (no external network):
   D:\UCIE\.venv\Scripts\python.exe -B -m unittest discover -s D:\UCIE\tests -p test_ucie_observations_v10.py -v
2. Run the combined source readiness and UCIE guard report (no network):
   D:\UCIE\scripts\ucie_review_readiness_v10.ps1
3. Run the V1.0 read-only browser (no automatic public source checks):
   D:\UCIE\scripts\ucie_library_browser_v10.ps1
4. From the browser, audit -> all candidates -> exact candidate:
   verify "이 후보의 공개 원본 관측 영수증 확인" shows 0 receipts.
5. Only with deliberate owner intent, the following command initiates
   approved limited public GET and saves a single observation:
   D:\UCIE\scripts\ucie_public_observation_record_v10.ps1 -ItemId EXACT64HEX
   The exact 64-hex ID must be copied from an eligible UCIE public candidate.
6. Reopen the candidate's observation page and verify one source-bound
   receipt, source revision SHA, observation status and NOT_VERIFIED.
7. Source-drift/tamper/forged approval always fails closed; no automatic
   candidate or rule promotion.

## Next real upstream regression gate

Actual independent upstream fix reproduction requires a separately reviewed
and source-committed **safe recipe per exact upstream change**, pinned to
the approved public source SHA and supported release, accompanied by
release note and licensing checks, reproducible independent before/after
test observations and explicit owner review. This milestone prepares the
chain of custody, it does not invent those results.
