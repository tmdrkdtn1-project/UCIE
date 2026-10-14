# UCIE Stage 9.7-9.8 — public evidence batch and UCIE Windows read-only handover

## Capability delivered

A first-party on-demand batch now connects the previously independent
Stage 9 metadata and code/document/release/advisory modules:

**approved 5-source metadata → adaptive ranking → existing UCIE SQLite
read-only duplicate check → source/PR opt-outs → 1-3 bounded public PR
evidence enrichments → skill-specific human review queue → NO_GO verdict**.

The batch calls only existing approved GitHub public APIs and previously
pinned exact official documents. No user-provided URL, redirects,
credentials, unrelated project accesses or untrusted program execution.

One run is hard-capped at 5 public metadata reads and 12 code/docs/release/
advisory requests, for a total maximum of **17** HTTP GETs. Defaults:
2 ranked new PR enrichments, at most 3. Upstream missing/invalid evidence
is recorded, not silently treated as a test PASS. An unpinned PR merge
SHA is **never** enriched. An absent feed means zero new candidates,
not a fabricated alert.

### Existing public-miner deduplication

`read_prior_miner_ids` opens only the dedicated UCIE
`runtime/public_miner.sqlite3` in `mode=ro` with `PRAGMA query_only`.
It does not modify the SQLite schema or PR rows, import Knowledge,
register a task, or rewrite any report.

Caller-expressed source opt-outs are applied before metadata fetching,
and PR-level opt-outs and already reviewed public PR identifiers are
removed before evidence enrichment. Feedback in Stage 9 ranking remains
transient, deterministic and non-training.

### Data and skill contracts

The returned queue provides source/PR URL, pinned public merge SHA
binding, domain skill, priority, change-evidence SHA, explicitly missing
documentation/advisory evidence and next independent review plan.
External source text is never included in this queue. Candidate queue
SHA256 is a dedup/change hint **not a signature**. It is not an
approved Rulepack, permanent memory, or a deployment artifact.

`review_batch_preview` requires structurally valid unapproved receipts
and refuses forged PASS fields, human approvals and altered checksums.
Review output remains `MANUAL_CANDIDATE_REVIEW_PENDING`.

### Command entrypoints

From an explicitly reviewed isolated UCIE checkout:

```powershell
# Opt-in PUBLIC ONLY, a single bounded batch, no DB writes
.\.venv\Scripts\python.exe -m ucie_miner batch-public-evidence --live --limit 2

# Limit public source and disable an advisory GET (incomplete evidence)
.\.venv\Scripts\python.exe -m ucie_miner batch-public-evidence --live --source modelcontextprotocol/python-sdk --limit 1 --skip-advisory

# Opt-out is effective before HTTP GET
.\.venv\Scripts\python.exe -m ucie_miner batch-public-evidence --live --skip-source git/git --skip-pr python/cpython#159311

# Without network: review bounded supplied receipt through stdin
# python -m ucie_miner preview-public-batch-stdin

# Host-local only, read-only status; never returns production GO
.\.venv\Scripts\python.exe -m ucie_miner preflight-public-batch-host
```

The command **without --live fails closed**. A host preflight prints
`READ_ONLY_PRECHECK_NO_GO` even if SQLite integrity and Python version
are valid. GitHub CI fixtures are synthetic and never prove that the
owner's `D:/UCIE` host, Windows task identity, tunnel, local scheduler
or operational 5-source batch is correctly configured.

### Release boundaries

This remains a **Draft** PR, based on unmerged Stage 9 work. It is
neither a patch to the existing hourly two-source `public_miner_cycle.py`
nor a request to start additional automatic collection.

- Main branch: unchanged; no release/package publication.
- Operating SQLite/Knowledge: never written or imported.
- Windows OS scheduler: not inspected or changed.
- External code: never executed, stored wholesale or republished.
- Model weights / permanent learning: unchanged.
- Rulepack signing, automatic rule promotion: forbidden / not performed.
- Upstream fix before/after testing, license clearance, security review
  and independent reviewer approval: NOT VERIFIED.

The next separate administrative step, **only after review**, is a manual
read-only host trial that checks actual data access, network failures,
elapsed runtime and scheduler coexistence with the existing miner.
A development CI green result is not a host acceptance PASS.
