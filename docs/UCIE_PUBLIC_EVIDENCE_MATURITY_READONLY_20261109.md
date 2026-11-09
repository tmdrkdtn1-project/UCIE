# UCIE read-only public evidence maturity review V01 (2026-11-09)

Scope: UCIE-only, existing source-linked Stage10/opted-in Stage15/Stage12 metadata. No external fetch, writes, scheduler changes, trust promotion, rule signing, customer distribution or cross-project access.

## Why this follows PR #215

PR #215 restored 1,008 source-linked UNVERIFIED review revisions by aligning three consumers with the canonical 10,000-row boundary. A restored source-linked ledger is not evidence of a real reproduced fix, safe recipe, accurate version range or license clearance. The next release blocker is **evidence maturity**, not candidate volume.

## First bounded implementation

`src/ucie_miner/public_evidence_maturity_v01.py` reuses `prepare_verification_handoff` and `_checked_handoff` before deriving any data. Thus source SQLite remains opened only through existing `mode=ro` / `query_only=ON` readers with schema, source-identity and fingerprint checks. No new raw SQLite or network consumer is introduced.

Output is a closed, deterministic, JSON-serializable summary:
- source-linked **evidence revision** count, and distinct *public identity* count;
- counts per previously approved public repo, PR/fix-PR/git commit identity;
- multiple evidence revisions under the same public identity, **not** automatically labelled duplicate, false-positive or verified fix;
- number of existing non-executable Stage6 template *candidates*;
- explicit report-only gaps: per-revision license not attested **here**, affected version not validated **here**, independent regression not performed **here**;
- bounded manual review targets without raw source code, logs or untrusted text.

An absent, pending or source-mismatched handoff cannot turn into a maturity score or display source targets. All approval, signature, external reproduction, customer release and automatic promotion flags remain false. The output is NOT a confidence score or clearance verdict; unrelated evidence systems may carry separately approved facts and are not overwritten by this read-only report.

## Usage: explicit owner-only audit, never scheduled

From the existing UCIE-only Python environment:

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.public_evidence_maturity_v01 --root 'D:\UCIE' --limit 8
```

Synthetic regression on branch:

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s 'D:\UCIE\tests' -p 'test_ucie_public_evidence_maturity_v01.py' -v
```

## Acceptance and non-acceptance

- Code + synthetic CI can establish bounded field calculation and fail-closed behavior, but cannot validate actual owner 1,008-row figures.
- Real owner report must remain pending until the exact new files are safely deployed with SHA-aware backup, without overwriting 15 pre-existing dirty tracked files.
- This report does not fix source license gaps or independently reproduce any upstream behavior.
- `ONLINE_RELEASE_AUTHORIZED=false`, `CUSTOMER_DISTRIBUTION_AUTHORIZED=false`, candidate automatic promotion disabled.

Next meaningful bundle: record actual owner report; investigate top review identities with approved source/version/rights documents and UCIE-authored isolated positive/negative reproduction. Distinguish **metadata completeness**, **independent correctness**, and **release permission**, and only then propose a human review gate.

Product owner: https://github.com/tmdrkdtn1-project/UCIE/issues/199
