# UCIE Stage 9.1–9.6: Public code, official documents, releases, advisories

## Approved evidence ingestion

Exactly five approved independent public upstreams: python/cpython, PowerShell/PowerShell, git/git, modelcontextprotocol/python-sdk, actions/runner-images. Every source and endpoint is allowlisted. No arbitrary URL, credentials, redirects, source checkout, code execution or file traversal.

### A. Code and script fixes

The anonymous endpoint GET /repos/{approved_source}/pulls/{pr_number}/files?per_page=30 is limited to one explicitly selected PR. Its output is treated as untrusted. Changes are summarized as: file-path SHA-256, filename extension, patch SHA-256, test-file marker, bounded changed-line counts and error-family tags. The original source lines and filenames are not retained or redistributed. Exactly 30 files yield TRUNCATED_PAGINATION_POSSIBLE, never complete-coverage PASS. No binary patch absence is interpreted as a successful test.

### B. Official documentation

Only these precise official public documents are configured:
- https://docs.python.org/3/library/os.html
- https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/resolve-path?view=powershell-7.6
- https://git-scm.com/docs/git
- https://modelcontextprotocol.io/specification/2025-11-25
- https://docs.github.com/en/actions/reference/runners

An in-memory bounded HTML parser emits a document SHA-256 and whether an expected topic marker appeared. It stores no HTML and executes no scripts. Redirect/404/oversize results are explicitly missing; document presence is not proof of version applicability or license approval.

### C. Releases and security advisories

Exact public GitHub GET routes: /repos/{approved_source}/releases?per_page=10 and /repos/{approved_source}/security-advisories?per_page=10. Tags and GHSA identifiers are treated as reference metadata only. An unavailable advisory feed is not evidence of no vulnerabilities; a release tag is not proof that an upstream PR shipped in that build.

### D. Source-specific learning and reusable skills

The public_knowledge_pipeline combines the 2–4 public evidence types, pinned merge SHA and Stage 9 reusable skill profiles. It emits a hash-addressed, non-executable correction question, conservative safe-call guidance, and isolated regression review plan. Status remains UNVERIFIED_CANDIDATE_ONLY or INCOMPLETE_PUBLIC_EVIDENCE. Offline preview yields MANUAL_REVIEW_ONLY_NO_GO.

### E. Commands and operating boundary

From an independently reviewed UCIE development checkout, a manually requested one-shot read is available via:

    python -m ucie_miner collect-public-evidence --live --source modelcontextprotocol/python-sdk --pr 3696 --merge-sha 754254c08fe1c3eda18b69da3d336106fe8d72d6

Use --skip-doc or --skip-advisory to omit that request (omission is not a successful evidence check). Offline read-only: python -m ucie_miner preview-public-evidence-stdin, taking bounded untrusted JSON stdin.

Bare collect-public-evidence without --live fails closed. Existing UCIE hourly Windows miner, runtime DB, scheduling, signed Rulepack, source allowlist, main branch and production environment are never changed by this Draft. There is no automatic learning/promotion or operating approval. Explicit upstream source/PR opt-outs must be honored by the Stage 9 lead selector before invoking per-PR intake.

Actual upstream before/after reproduction, version inclusion, file-level license compliance, security review and human signoff remain NOT VERIFIED. CI tests are first-party synthetic only.
