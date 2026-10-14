# Stage 2 evidence-candidate gate (offline extension)

This extension is deliberately **not connected to the network collector**. The existing miner only collects two pinned sources, stores metadata digests, and treats all candidates as unverified. The new `ucie_miner.evidence.evaluate` function consumes bounded caller-supplied snapshots for five specifically approved *public* upstream repositories.

## Boundaries

- No arbitrary repository, URL, personal GitHub connection, user project or local-project input.
- No code execution, patch application, network requests, scheduler setup, model training, database promotion or rulepack creation.
- Validate a strictly shaped PR snapshot; reject invalid source, URL, timestamp, file count, patch size, secret markers and selected prompt-injection patterns.
- Return only generic pattern and regression-test **candidates**, not copied patches.
- Exact source ownership and license strings in the result are reference labels or caller-provided claims. They are **not authoritative independent checks**. GitHub PR metadata, merged commit and license must be independently resolved and checked before any promotion.
- The stage-1 curated rulepack and legacy stage-2 miner are unchanged.

## Suggested next integration gate

Before wiring the current collector to this extension, independently fetch PR detail, exact merge commit and repository license at the pinned commit using strict allowlisted public endpoints; implement pagination and evidence provenance receipt, require license/source attestation and merge consistency, handle truncated patches and opt-outs, and extend migration-safe storage. Do not broaden polling scope merely because five source names are available for offline review.

## Tests

The existing CI offline matrix uses Python 3.13 and 3.15 on Windows and Ubuntu. It runs `python -m unittest discover -s tests -v`, which includes `tests/test_ucie_evidence.py`.

This PR is **candidate-only**, not a production deployment, training result, or local Windows execution pass.

## October 14 follow-up: provenance cross-check and Stage 3 gate

The read-only `public_provenance.crosscheck_pr_metadata` helper retrieves PR detail
from an exact pinned GitHub API route and compares PR number, merged flag,
public URL, merged timestamp and 40-character merge commit SHA. Its default
fetch uses anonymous GET only. This is an independently fetched **PR metadata
consistency check**, not a source license verification, a patch-test pass, or
complete author/date/commit provenance. It is now opt-in for the collector through `crosscheck_origin=True` and enabled
by the official Stage 3 worker entrypoint. The existing collector still reports
unverified candidates and does not grant license or fix verification.

The official `scripts/public_miner_cycle.py` now opts into an hourly schedule
gate. Corrupt prior receipts fail closed; receipts persist failure counters
and allow bounded retry. The source collector's outbound API routes are
now exact allowlisted paths. The CI tests use synthetic fixtures.

**Operational release gate remains HOLD:** complete pinned-commit license
lookup and opt-out handling, independently review data retention and quotas,
verify Windows scheduled task execution/recovery, and obtain approval for
any broader corpus. A successful CI matrix is not a live Windows operation
receipt. Do not deploy a scheduler or promote learning data on this evidence.
