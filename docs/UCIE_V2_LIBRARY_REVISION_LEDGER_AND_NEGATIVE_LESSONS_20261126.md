# UCIE V2 Virtual Library bounded revision ledger and reusable negative lessons

PROJECT=UCIE ONLY. Isolated Draft stacked after PR #366 head abfe2285d3c9f04723d9fe5c924554aa7e1ddd56.

Previously: B4/B5 authored bundles and B3 revision dispositions were deterministic but memory-only. Now a **bounded review-only ledger** can keep up to 32 full bundles, preserving old original chapters, their two source SHA pins, engine/test contracts, accepted synthetic control facts, counterexample and source-change HOLD review disposition, while never pretending these facts are independent QA.

Functions:
- `new_review_history`: create an empty versioned review ledger.
- `append_review_bundle`: validate original bundle content hash, nested original chapter hash, source identity, rights/QA flags and append a chained review entry. Duplicate exact hash returns the original ledger; capacity is fail-closed, never silently prunes. This is review provenance, not tamper-proof signed storage.
- `validate_review_history`: reject broken event order, chain, content hash, fabricated rights, unsupported source, removed/reordered events, duplicate digest.
- `review_negative_lessons`: list rejected output-privacy overgeneralization and candidate-source/incomplete-study HOLD cases for subsequent review. A negative lesson is NOT a validated positive rule.
- `read_review_store` / `write_review_store`: **optional**, caller-designated isolated `ucie_v2_review_store` directory with exact marker `.ucie_v2_review_store`. Default is read-only preview; explicit `approve_write=True` plus expected previous SHA is required for a bounded atomic JSON update. The file uses a cap, strict path/marker checks, appends only. No silent directory initialization or owner Windows deployment.

Warnings: the hash chain detects local accidental corruption but cannot authenticate source independently or resist a malicious actor who rewrites the whole unsigned ledger. CAS protects stale sequential writes but is NOT a cross-process lock; concurrent writes require separate OS locking. Review mode never writes operating SQLite, task scheduler, customer code, current source registry, signed rulepacks, V04, or network. Its full JSON payload includes first-party authored text only. In-memory assembly does not imply operator configured the optional disk store. Customer release and actual human validation remain HOLD.

Tests are isolated first-party cases, including 32-entry capacity, mutation/reorder, forged approvals, source injection, duplicate SHA, prior evidence retention, preview-only store, explicit temporary store persistence and symlink denial. ACG Draft base skip + one exact-head full suite after ready.
