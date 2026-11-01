# UCIE V1.1 — source-pinned release ancestry, safe guard regression and review bundle

Date: 2026-11-01. UCIE project ONLY. No cross-project or private source.
Owner reported successful PUBLIC_OBSERVATION_STORED_NOT_FIX_VERIFIED
for exact candidate 267bb1def59a243526e63a64c40f7c421ae640a69d04beb593873668837814ea
and receipt 050b1af00a937edab9aa9409139ba8f929046cf88a49784d3ed074566489d419.
V1.0 Windows observation receipt *replay* was not independently confirmed
in conversation and remains an acceptance item.

## Combined milestone

1. **Actual GitHub published release-tag history observation.** After
   checking the current UCIE Stage10/12/15 source-linked candidate and an
   existing V1.0 successful public identity receipt, the owner explicitly
   chooses a published release tag. Calls at most two anonymous GitHub REST
   endpoints within the same approved upstream repository:
   /releases/tags/{exact-tag} and /compare/{exact-merge-sha}...{exact-tag}.
   Require non-draft published release metadata plus actual compared base
   SHA and merge-base SHA equal to the pinned upstream commit, with
   behind_by=0 and ahead/identical comparison. Reject redirects, proxies,
   unknown repos, query strings, bad tags, unexpected content type or
   oversized replies. All remote JSON is untrusted; commands, HTML and
   upstream code are neither executed nor stored.
2. **Precise meaning:** a release-tag ancestor observation establishes
   only a sampled Git history relationship. It does NOT establish that
   a particular binary or installed tool contains the fix, that the
   upstream behavior is correct, that an official release ships/endorses
   it, that the license permits reuse, or a secure deployment approval.
   No new rule can be promoted from this observation.
3. **Actual UCIE safety regression + human review packet.** Run six
   UCIE-owned deterministic offline guards from V1.0, combine the current
   source audit, immutable-by-tool observation receipt replay, fixed
   safe review questions and seven independent upstream proof requirements.
   PASS for these tests means only UCIE's own input boundaries passed.
   No external upstream before/after test runs. Exact source-linked
   candidate, observed receipt, reproducible bundle SHA and 0 approvals
   are displayed. Every upstream gate explicitly remains NOT_VERIFIED,
   NOT_PERFORMED or NOT_APPROVED. No executable rule generated.
4. **V1.1 owner localhost UI** inherits the V1.0 candidate list (including
   candidates with zero receipts), audit, search, comparison, selected
   search return and observation receipt browser. Per-candidate audit
   adds the offline **독립 회귀시험·릴리스 검토 준비표** link. The
   manual release ancestry probe stays a separate explicit PowerShell
   command; browser page loads never fetch public metadata.

## Test and install

Only these seven NEW files after PR is merged and each SHA is checked:
- src/ucie_miner/library_release_ancestry_v11.py
- src/ucie_miner/library_upstream_review_v11.py
- src/ucie_miner/library_browser_v11.py
- scripts/ucie_release_ancestry_v11.ps1
- scripts/ucie_library_browser_v11.ps1
- scripts/ucie_upstream_review_v11.ps1
- tests/test_ucie_release_review_v11.py
- docs/UCIE_V11_RELEASE_REGRESSION_REVIEW_20261101.md

There are **eight** new paths including the documentation file. Keep
previous V0.1–V1.0 code and local review/source data unchanged.
Do not use git reset --hard, git clean, broad checkout or blanket git pull.

On owner Windows, first run synthetic offline tests:

    $env:PYTHONPATH = 'D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_release_review_v11.py' -v

Then launch the local browser:

    & 'D:\UCIE\scripts\ucie_library_browser_v11.ps1'

Open the printed http://127.0.0.1:PORT/ on the same machine,
choose an exact public candidate, inspect its public observation receipt
(should be present for a previously recorded candidate) and the new
independent proof checklist. The local page MUST show UCIE guard 6/6
and upstream independent tests 0/0, no approved rules.

Optional explicit published release tag observation (the tag must be an
actual release of the candidate's *approved source repository*):

    & 'D:\UCIE\scripts\ucie_release_ancestry_v11.ps1' -ItemId 'ACTUAL64HEX' -ReleaseTag 'EXACT_REPO_TAG'

Do NOT fabricate an exact tag, claim universal "latest", or interpret a
not-found/missing-tag/no-matching-graph result as PASS. A large GitHub
comparison could be refused by size bounds; this means NO_GO.

Current V1.1 does not record release-tag ancestry on disk: its output
is a transient, SHA-digested observation. Future owner-gated review must
separately bind a reviewed safe reproduction recipe, actual target tool
version, real before/after independent test, license and human signoff.
No automatic promotion or scheduled tasks. GitHub CI verifies synthetic
code paths, not the real release of an upstream source.
