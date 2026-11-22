# UCIE Library candidate-specific upstream identity and QA packet V1

## Scope / status

**PR #77 source implementation only.** The existing Library assessment,
existing signed review history, and existing Stage 16 local chain audit remain
authoritative for their previously established *limited* evidence contracts.
This change adds two opt-in, candidate-level checks without installing,
executing or trusting upstream patches.

1. `public_library_upstream_recheck.recheck_library_candidate_public_identity`:
   exact-source, single-request public API SHA recheck.
2. `public_library_qa_packet.inspect_library_candidate_qa_packet`:
   authenticated existing signed-claim hash versus actual, separately
   submitted bounded artifact **bytes** and exact public revision.
3. `public_library_runner_ci.recheck_signed_packet_runner_ci`:
   optional one-shot public UCIE GitHub Actions **generic workflow metadata**
   comparison with the signed packet's runner ID and runner commit.

The feature **does not** perform human independent QA, reproduce the
upstream regression, inspect untrusted binary/test artifacts semantically,
certify published-version inclusion, or issue any production/rule release GO.

## Evidence boundary A — live upstream identity

The operator must explicitly opt in with `live=True` and select **one**
validated public Library URL. This routine first checks the *existing* signed
review chain and caller-provided SHA256 head. It then performs exactly one
anonymous HTTPS GET for an exact API route derived from the validated card:

- Approved five repository sources only:
  `python/cpython`, `PowerShell/PowerShell`, `git/git`,
  `modelcontextprotocol/python-sdk`, `actions/runner-images`.
- PR identity: `GET /repos/<approved source>/pulls/<positive ID>`.
  Reuses the existing Stage 17 PR owner/URL/closed/merge SHA validation.
- Direct `git/git` commit:
  `GET /repos/git/git/commits/<40-hex-SHA>`; one-parent commit,
  exact canonical public HTML URL, exact SHA and dated metadata.
- No redirects, no foreign or attacker-supplied URLs, no credentials or
  remote commands, bounded response bytes, duplicate JSON keys rejected,
  and a rate-limit pause when remaining quota is low.

If the public metadata's pinned SHA disagrees, the output is
`PUBLIC_PINNED_REVISION_SHA_MISMATCH_NO_GO`. A matching SHA means **only**
that the public API returned the same revision identity at observation time,
not that the candidate actually fixes the reported bug, is present in an
official released version, or passed independent QA. Mocked API transports
used for CI are explicitly tagged and never marked as live API observations.

There is **no new hourly collector**; the function makes no request unless
the caller explicitly authorizes a single candidate and a live lookup.
No ongoing source polling is introduced.

## Evidence boundary B — signed QA packet and bytes

The existing Ed25519 signed history contains a signed claim for the
candidate's exact public URL, commit/merge SHA and evidence SHA256. This change
exposes the signed `review_evidence_sha256` through the existing read-only
history inspection, **only** for its exact, current, nonrevoked revision.

An operator may supply `inspect_library_candidate_qa_packet` with:

- An exact schema, source URL, pinned SHA, source evidence SHA256 and
  version claimed by the signed history.
- An untrusted UCIE runner reference (repository, positive run ID, 40-hex
  runner commit SHA), a bounded UTC observation timestamp, and the existing
  first-party regression plan identifier. The runner run is **not checked
  against the Actions API at this stage**.
- Six bounded 1–8192-byte artifacts: observed affected behavior, observed
  fixed behavior, security negative case, license review, published release
  review and QA reviewer identity. Their exact SHA256 hashes are in the
  evidence packet. The affected/fixed digests must be distinct.
- The **canonical SHA256 of the entire packet must equal the signed review
  decision's `review_evidence_sha256`**. The existing history independently
  verifies the known owner/QA public keys, signatures, monotonic sequence,
  expiration, revocation and caller-supplied head checkpoint.

If any bytes, digest, revision, trust key, expiration or revocation mismatch,
the validation refuses the packet. The returned
`SIGNED_QA_PACKET_BYTES_BOUND_AUDIT_PENDING_NO_GO` state attests only
byte integrity and the packet-to-**keyholder claim** binding.

**Explicitly not proved:** that the six artifact contents came from the named
runner, that the runner executed any test, that the QA reviewer was truly
organizationally independent, that a release contains the fix, that license
approval is legally sufficient, or that the vulnerability was safely
reproduced. All of those gates remain `false`.

Do not assume a source-provided signature or a matching digest is by itself
an independent truth attestation. The expected signed-history head must be
retained under a separately authenticated mechanism; the UCIE SQLite file
cannot supply rollback protection for itself.

## Evidence boundary C — actual UCIE runner identity

The operator may separately call `recheck_signed_packet_runner_ci(...,
live=True)` after the exact signed packet and all six evidence artifact
bytes have passed the preexisting ledger and byte-integrity gate.

- Makes **one** anonymous, no-redirect, bounded metadata GET to the exact
  first-party UCIE endpoint
  `https://api.github.com/repos/tmdrkdtn1-project/UCIE/actions/runs/<ID>`.
  The run ID comes solely from the authenticated signed packet.
- Checks exact run ID, `repository.full_name`, canonical public run URL,
  UCIE's `.github/workflows/stage1-offline-tests.yml` workflow path,
  recorded runner commit SHA, workflow completed/conclusion state,
  and bounded UTC timestamp.
- Rejects foreign CI repositories and workflow paths, future timestamps,
  malformed JSON/duplicate fields, unexpected redirects, and wrong SHA.
- Respects rate-limit pause. In tests, injected mock transports have their
  own `SYNTHETIC_..._NOT_LIVE_NO_GO` state and **zero** actual HTTP GETs.

Even an authentic **general UCIE workflow SUCCESS** reports
`UCIE_GENERAL_CI_METADATA_OBSERVED_CANDIDATE_QA_PENDING_NO_GO`.
It cannot establish that the specific upstream candidate revision was
checked out in the runner, that the attached packet artifacts were actually
produced by the workflow, or that negative regressions were independently
reproduced. Individual jobs/steps, attested provenance, release inclusion,
license and reviewer identity remain separate explicit evidence gates.

## Validation and safety tests

- `tests/test_ucie_public_library_upstream_recheck.py`: the API transport is
  always synthetic. Tests single endpoint, exact PR and git/git SHA matching,
  rate pause, foreign URL/owner, forged metadata, no live opt-in, disallowed
  transport envelope, mismatched SHA and revocation preservation.
- `tests/test_ucie_public_library_qa_packet.py`: ephemeral synthetic
  owner/QA keys and isolated test-only UCIE ledger. Tests exact artifact bytes,
  tampering, missing/invalid packet signature digest, owner revocation,
  expiration, stale source SHA, wrong head and other project paths. Also tests
  the one-shot UCIE runner metadata path with injected mock transport:
  correct run ID / SHA and workflow path, non-success CI, bad workflow repo,
  future time, foreign URL, revocation, and no unauthorised fetch.

Offline CI Python 3.13/3.15 on Windows and Ubuntu exercises these boundaries;
**CI synthetic PASS is not the same as independent upstream regression PASS**.

## Remaining proof required before any rule approval

1. A separately authorized, isolated test runner must reproducibly exercise
   **affected and fixed** versions and record negative security cases.
2. Verify that the runner's completed run ID, exact code revision, job outputs
   and independently retained artifact digests match the submitted packet,
   using read-only authoritative evidence; do not trust caller assertions.
3. Independently confirm version inclusion, license status, security
   applicability and reviewer's identity, with source/version-specific
   evidence beyond a bare PR or checksum.
4. Authenticate owner release risk acceptance and independent QA under a
   separate gated review step, preserving owner revocation and durable
   anti-rollback checkpoint.

**Automatic promotion, signed Rulepack creation, skill installation,
recipient-project access, model-weight training, and database changes on the
operating Windows host remain OFF.** PR #77 remains Draft until explicit
owner review and approval.
