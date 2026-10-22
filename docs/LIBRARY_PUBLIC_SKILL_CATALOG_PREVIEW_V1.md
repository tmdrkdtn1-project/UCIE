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

Synthetic offline tests: `tests/test_ucie_public_library_catalog.py`.
They verify fixed five-skill taxonomy, bounded candidate output, deterministic
comparison, missing-selection semantics, forged approval rejection, and
prompt-injection guidance rejection. Passing CI does not establish real-world
fix accuracy, production authorization or cross-project isolation.

**Current gate: DEVELOPMENT_ONLY / PUBLIC_RESEARCH_CATALOG_PREVIEW_NO_GO.**
