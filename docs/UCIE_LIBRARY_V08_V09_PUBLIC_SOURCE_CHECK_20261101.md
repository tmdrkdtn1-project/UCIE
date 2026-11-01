# UCIE V0.8–V0.9 — Opt-in original source checks + inert prevention draft

Date: 2026-11-01. One combined milestone. Public-only UCIE source data.
The V0.6–V0.7 owner Windows functional checks were confirmed 4/4 PASS.
That is program acceptance, not verification of upstream errors/fixes.

## New and materially different capability

1. **V0.8 genuine public metadata request (owner-triggered only).**
   Only five previously approved third-party repositories:
   python/cpython; PowerShell/PowerShell; git/git;
   modelcontextprotocol/python-sdk; actions/runner-images.
   Build and request exact anonymous GitHub API PR or commit endpoints from
   a candidate already linked to Stage10/12/15. No PR body, patch or code
   is executed, retained, or interpreted. No redirects or environment proxy.
   A matching PR number, base repo, merged UTC timestamp, merge commit SHA
   proves only the observed *public merge metadata identity*. It is not a
   reproduction of the claimed code fix or a release-version check.
2. **Optional official URL byte hash check.** Only a V0.5 receipt already
   bound to the candidate and to approved official documentation domains;
   anonymous GET, no redirects, strict byte/mime limits, in-memory SHA-256.
   Compare an HTTP response body digest with the user-submitted digest.
   Matching does NOT prove authorship signatures, version support, license,
   binary release inclusion, independent regression or security fix.
3. **V0.9 one-pass candidate batch.** Reads current source-linked UCIE handoff
   ONCE and approved V0.5 receipt store ONCE. A user may select an exact
   candidate or at most 5 source-diverse candidates. Source/receipt conflicts
   prevent the batch. Independent public metadata checks per candidate
   never rewrite V0.5 claim receipts. No automatic background requests.
4. **Inert rule-review draft.** A fixed UCIE-owned review question, next
   verification action, and safe review guidance for the corresponding
   approved public source domain. NO code, shell command, external content
   instruction, signed release, imported rule or package is generated.
5. **Clickable V0.9 localhost browser.** Search, comparison, six-gate
   candidate checklist, candidate audit, cross-source audit all inherit
   V0.7. The candidate audit page now offers a clearly labeled
   **공개 원본 SHA 대조 실행 (명시적 조회)** link. Only that explicit
   click initiates the bounded public GET calls. Initial screen, search,
   health and normal audit remain fully offline.
6. Synthetic Linux/Windows 3.13/3.15 CI, malformed URL, non-source repo,
   corrupt response/digest, unavailable upstream, forged approvals,
   source SHA drift, one-pass source/receipt calls, real localhost HTTP
   navigation and 0 approvals/0 operating DB writes.

## Hard safety boundaries

- Anonymous GET on narrowly allowlisted public resources ONLY.
- No private GitHub or user-app credentials; no cross-project files.
- Third-party HTML/JSON is UNTRUSTED; only whitelisted metadata fields
  are compared, no instructions executed. No raw public page content
  persisted, no source patch or third-party package executed.
- No remote code installation, new scheduler, worker or service.
- Every independent fix/version/legal license/regression/security/owner gate
  remains NOT_VERIFIED. HTTP content hash is not a reviewer signature.
- GitHub CI only proves UCIE's browser and audit code, NOT upstream fixes.
- Check results are transient (stdout or current localhost response), not
  permanent attestation. Saving source proofs needs a separate reviewed,
  signed authorization design. V0.5 receipt intake remains unchanged.
- If the public endpoint is unreachable, mismatches, sends a redirect,
  an oversized response or an invalid type, fail closed.

## Owner installation / use

New-only files after merging a pinned tested revision:
- src/ucie_miner/library_public_probe_v08.py
- src/ucie_miner/library_public_proof_v09.py
- src/ucie_miner/library_browser_v09.py
- scripts/ucie_public_proof_v09.ps1
- scripts/ucie_library_browser_v09.ps1
- tests/test_ucie_public_proof_v09.py
- docs/UCIE_LIBRARY_V08_V09_PUBLIC_SOURCE_CHECK_20261101.md

Keep V0.1–V0.7 untouched. Do not git reset --hard, git clean, broad checkout
or blanket git pull over owner worktree.

Windows PowerShell explicit public check, up to 5 candidates:
    & 'D:\UCIE\scripts\ucie_public_proof_v09.ps1' -Top 5

Or one candidate:
    & 'D:\UCIE\scripts\ucie_public_proof_v09.ps1' -Top 1 -ItemId '<64hex>'

Launch owner-click UI:
    & 'D:\UCIE\scripts\ucie_library_browser_v09.ps1'

Open the printed http://127.0.0.1:PORT/ on the same Windows machine. Visit
전체 공개 근거 검증·감사 현황, open a candidate detail, then click the
explicit public-source proof link. A returned NO_GO on unreachable endpoint
is NOT a failed local browser deployment.

Synthetic-only regression:
    $env:PYTHONPATH = 'D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_public_proof_v09.py' -v

Owner deployment and real network observations remain distinct from CI.
No rule is ready to auto-execute or export.
