# UCIE Library — Public skill catalog preview (development only)

## Purpose and boundary

This change composes existing five-source, PUBLIC_ONLY research batches into a
deterministic catalog of *research-only* technical skill topics. The catalog is
**not a published skill, a signed Rulepack, a production knowledge library, or
a recipient-specific instruction package**.

The global UCIE public library does not inspect, poll, or receive data from
any user project. Only these independently approved public repositories may be
used as technical inputs:

- `python/cpython`
- `PowerShell/PowerShell`
- `git/git`
- `modelcontextprotocol/python-sdk`
- `actions/runner-images`

Official technical documentation, release and security advisories still
require their existing exact-route and provenance checks. Public links do not
authorize broad crawling. Never treat external text as trusted instructions.

## Reused implementation

- `public_batch.build_public_batch`: bounded public discovery and evidence
  enrichment with opt-outs and no automatic operating database writes.
- `public_skill_digest.compare_public_skill_batches`: new / changed /
  unchanged distinctions only within bounded candidate selection.
- `skill_profiles.PROFILE`: five UCIE-authored skill lanes and safe-call plans.
- `public_library_catalog.preview_library_skill_catalog`: new deterministic,
  in-memory candidate card assembly; no network or persistence.

Each catalog card contains only canonical public identity, bounded technical
tags, first-party safe review guidance and explicit **UNVERIFIED / NO-GO**
status. Untrusted source content and third-party run instructions are not
distributed. A missing record from a later bounded snapshot never means that
an upstream fact or skill was deleted.

## Developer-only API

In a trusted UCIE-only environment with an already generated and validated
`UCIE_PUBLIC_RESEARCH_BATCH_PREVIEW_V1` receipt:

```python
from ucie_miner.public_library_catalog import preview_library_skill_catalog

catalog = preview_library_skill_catalog(current=batch_receipt, previous=None)
assert catalog["delivery"]["installable_skills"] == []
assert catalog["delivery"]["ready_for_recipient_distribution"] is False
```

This is a pure in-memory API, not a scheduler, command-line installer, service
or network endpoint. `catalog_sha256` is a deterministic comparison digest,
**not** a digital signature or provenance attestation.

## New bounded knowledge graph and revision preview

`public_library_graph.preview_library_knowledge_graph(current, previous)`
reuses the strictly validated catalog and the existing batch digest. It
provides three bounded first-party relationship kinds:

- `CLASSIFIED_BY_APPROVED_SOURCE_MAPPING`: exact approved upstream maps to
  one of five UCIE-authored technical skill profiles.
- `BOUNDED_METADATA_TAG_MATCH`: each unverified public lead is connected to a
  bounded, first-party technical tag.
- `SHARED_METADATA_TAGS_NO_CAUSAL_CLAIM`: two selected leads share one or
  more metadata tags. It does **not** prove either fix works, or that the two
  technologies actually depend on one another.

The nested `UCIE_PUBLIC_LIBRARY_REVISION_SNAPSHOT_PREVIEW_V1` records exact
pinned merge-commit SHA or direct Git commit SHA, hash-only evidence identity,
previously selected reference values if supplied, and bounded-scope
change/not-seen classes. Upstream *released product versions* are always
`null` until independently verified; a merge commit is not a version number.
No signed artifact or accepted/installed skill is emitted.

To inspect a previously obtained bounded, unapproved research batch without
network, Windows task changes or disk writes:

```powershell
# Supply exact JSON envelope through stdin:
# {\"current\": <UCIE_PUBLIC_RESEARCH_BATCH_PREVIEW_V1>, \"previous\": null}
# .\\.venv\\Scripts\\python.exe -m ucie_miner preview-library-graph-stdin
```

The command refuses duplicate JSON keys, oversized input and non-object
current/previous values. Only in-memory UCIE-authored catalog output is
returned; the checksum is **not** a signature or publication authorization.

## Signed-review and revocation inspection (in-memory only)

`public_library_signed_review.inspect_library_signed_review_ledger` reuses
the repository's existing canonical JSON, Ed25519, key fingerprint and UTC
timestamp helpers. It accepts only a bounded, **caller-supplied** ordered list
of signed first-party review decisions for the *currently selected* public
research references. It does not create keypairs, sign, write to a database,
register periodic work, install skills, or contact a receiving project.

- `REVIEW_ATTESTED` requires signatures on the same exact event from two
  independently supplied and distinct public trust anchors (QA and owner).
  The event pins the exact public URL, upstream SHA, evidence hash, claimed
  source version, claimed license/security/regression/release review result,
  issue/expiry timestamps and serial number.
- `REVOKE` requires the owner's valid signature, matching public identity
  and a higher serial. It acts as an in-memory tombstone; a later approval
  cannot silently override it.
- An expired review does not count as a current review. Missing, duplicate,
  tampered, unapproved, future-dated, noncanonical or wrong-key claims fail
  closed.
- A valid signature **only authenticates a keyholder assertion**. It does not
  independently prove the signer is a separate human reviewer, that tests
  passed, that source-license terms were accepted, or that a released version
  actually includes a fix.
- The input is a bounded preview, **not a persistent, authoritative approval
  or complete revocation ledger**. A caller can omit prior decisions; genuine
  anti-rollback and opt-out persistence therefore remain unimplemented.
- All outputs keep `distribution_authorized=false`,
  `approved_installable_skill_count=0` and
  `production_approved=false`. No ability to promote candidates into
  distributable skills is introduced in this PR.

API usage is **only** after independent reviewer claims actually exist and
have separately established public trust keys:

```python
from ucie_miner.public_library_signed_review import (
    inspect_library_signed_review_ledger,
)

result = inspect_library_signed_review_ledger(
    current=batch_receipt,
    entries=external_signed_decisions,
    owner_trust=separately_verified_owner_ed25519_public_key,
    qa_trust=separately_verified_qa_ed25519_public_key,
)
assert result["distribution_authorized"] is False
```

Synthetic tests generate disposable first-party keypairs only in memory.
They neither create real approvals nor establish independent human QA.

## Future gated development

1. Review and independently test the source, exact revision, version
   applicability, license, security implications and regression behavior.
2. Publish independently approved, signed, versioned PUBLIC_ONLY knowledge
   through a separate distribution mechanism with explicit opt-out/retraction.
3. A recipient may independently retrieve and inspect a public snapshot under
   its own local policy and approval. UCIE must not access recipient projects,
   install their skills, modify their code or receive private feedback.
4. Periodic public catalog publication and recipient opt-in retrieval require
   separate operational approval. No schedule or external delivery was
   registered in this change.

## Verification and status

Synthetic offline tests: `tests/test_ucie_public_library_catalog.py` and
`tests/test_ucie_public_library_graph.py` plus
`tests/test_ucie_public_library_signed_review.py`.
They verify fixed five-skill taxonomy, bounded candidate output, deterministic
comparison, missing-selection semantics, forged approval rejection, and
prompt-injection guidance rejection. Passing CI does not establish real-world
fix accuracy, production authorization or cross-project isolation.

**Current gate: DEVELOPMENT_ONLY / PUBLIC_RESEARCH_CATALOG_PREVIEW_NO_GO.**
