# UCIE Stage 4-8 Candidate-Only Integration V1

This draft integrates the existing Stage 4 review manifest and Knowledge V1
ledger with Stages 5-8 on an **isolated Git development branch**. It does
not merge into `main`, import a live database, run upstream code, enroll
a scheduler, sign a Rulepack or deploy anything.

## Read-only pipeline

1. The existing Stage 4 miner stores *unverified* public PR metadata.
2. A **separately authorized manual** Knowledge V1 import may copy hash-only
   metadata to `runtime/knowledge.sqlite3`. **This PR does not run it.**
3. `ucie_miner.integration.preview_knowledge_rules(root)` requires an
   **already existing** Knowledge DB and checks it, read-only, against
   `runtime/public_miner.sqlite3` and the pinned Stage 4 review manifest.
4. `group_patterns` unifies curated canonical PR families without accepting
   arbitrary unapproved sources, mismatching hashes or inconsistent mappings.
5. `candidate_rulepack` emits safe *guidance and synthetic regression plans*
   for the pinned eight PR families; it never emits executable commands or
   a production signature.
6. `approval_gate` remains NO-GO. Stage 8 remains a side-effect-free
   checklist, **not** an operational approval action.

## Preview command (after integration review and manual Knowledge import)

```powershell
.\.venv\Scripts\python.exe -m ucie_miner preview-chain
```

The command never imports or creates a Knowledge database. It refuses absent,
symlinked, stale, mismatching, quarantined or malformed evidence. Unmapped PRs
remain unverified and are not silently assigned a rule. PRs marked QUARANTINED
or RETRACTED are excluded; a missing canonical record denies a partial group.

Only `python/cpython` and `PowerShell/PowerShell` are supported by the
current Stage 4 Knowledge and curated PR review *implementation*, although
the overall UCIE public research policy also permits `git/git`,
`modelcontextprotocol/python-sdk` and `actions/runner-images`. Expanding
the Knowledge import or curated release verification requires separate
review, not an implicit allowlist change.

All integration tests use disposable synthetic SQLite fixtures and cannot
mutate the operating miner or Knowledge databases. Existing PRs #4/#6 and
#7/#8/#9 retain their own review and CI provenance. Integration CI is a
distinct gate. Human signoff, independently reproduced regressions, license
and security review, authenticated ownership, final signature and actual
Windows host validation remain **NOT VERIFIED**.

### Proposed acceptance gates

- Full Python 3.13/3.15 Windows and Ubuntu test matrix on this exact branch
- No side effects to active collection or scheduled tasks
- Knowledge-to-miner source/URL/timestamp/SHA agreement
- Quarantine, retraction, stale import, missing canonical and unknown pattern
  synthetic regression tests
- Independent approval and signed Rulepack *only via a future separately
  approved and verified procedure*

**Status:** DEVELOPMENT_CANDIDATE_ONLY / NO_PROMOTION / NO_DEPLOYMENT.
