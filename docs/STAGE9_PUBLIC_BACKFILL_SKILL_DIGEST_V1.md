# UCIE Stage 9.9 — Public source backfill + cross-run skill knowledge digest

## What changed beyond Stage 9.7–9.8

Previous integration selected from only the most recently updated 20 closed
PRs per source. It also stopped reviewing candidates after an unpinned PR,
leaving enrichment slots empty even when an alternative was available.

This increment adds **controlled public source depth and reusable knowledge
comparisons**, not an additional operating permission gate:

1. Exactly five approved public repositories. On explicit request, fetch
   up to 3 GitHub API pages per source (20 closed PR records/page). Stop on
   the first short page. One batch can inspect up to 300 public PR metadata
   records (60/source). Canonical GitHub URLs, source/target identity and
   merge timestamps remain strictly checked.
2. Ranking can consider up to 12 source-diverse, unreviewed candidates to
   fill **up to three actual enrichment slots**, skipping missing merge
   commit SHA without wasting a slot. Evidence enrichment stays at a
   maximum of four exact public GET endpoints per PR.
3. Maximum request budget with 3 pages and 3 enrichments:
   **15 metadata + 12 code/doc/release/advisory = 27 GETs.**
   The default remains one metadata page/source and two enrichments.
4. The candidate queue now exposes a fixed, safe-call guidance from the
   first-party five-skill profiles, a pinned merge SHA, bounded error-family
   tags, and changed public test-file count, **never raw patch/code**.
5. `compare_public_skill_batches(current, previous=None)` builds a
   read-only digest grouped by Python, PowerShell, Git, MCP/API and Runner.
   It distinguishes NEW, EVIDENCE_CHANGED, MERGE_IDENTITY_CHANGED and
   UNCHANGED candidates within *this bounded selection*. Candidates not
   included this run are `NOT_IN_THIS_BOUNDED_SELECTION_NOT_DELETED`.
   Source-code absence, release inclusion and reviewer approval cannot
   be inferred from the digest. The digest never learns model weights,
   imports a Knowledge ledger, records private user details or registers
   alerts.
6. An unchanged digest sets `notify_if_manually_scheduled=false` as a
   suggestion only. The system does not schedule, send or subscribe to
   monitoring automatically.

## Actual new approved-public metadata evidence

`docs/evidence/stage9_public_recent_delta_20261014.json` records
three *actually checked public* merged PRs and file lists:

- `python/cpython#159397` — runtime compatibility for FreeBSD readlink;
- `modelcontextprotocol/python-sdk#3679` — MCP Apps results from
  notifications;
- `actions/runner-images#14911` — Python 3.15 toolset entries for Ubuntu
  runner images.

GitHub PR merged_at/merge SHA are public metadata. These examples are
unverified review candidates; no upstream code has been executed, no
version/binary inclusion is asserted, and no license audit is claimed.
They are not evidence that the owner's Windows PC ran this new collector.

## Manual, opt-in, read-only usage after review

On a trusted UCIE development checkout:

```powershell
# Default remains 1 PR-list page per source, max 2 enrichments:
python -m ucie_miner batch-public-evidence --live --limit 2

# Explicitly deepen to 3 pages per approved public source:
python -m ucie_miner batch-public-evidence --live --backfill-pages 3 --limit 2

# Review a bounded JSON pair supplied on stdin:
# {"current": <one unapproved public batch>, "previous": <earlier one or null>}
# python -m ucie_miner preview-public-skill-digest-stdin

# Existing UCIE host observation remains separate and always NO_GO:
python -m ucie_miner preflight-public-batch-host
```

Both read-only CLI commands reject duplicate JSON input keys. Live
network collection still requires explicit `--live` and is never
registered with the old Windows hourly miner. Source/PR opt-outs remain
effective before public fetches and enrichment. There is no automatic
rule promotion, persistent learning, model weight tuning, operating
SQLite write or installation of a ChatGPT skill.

## Verification boundary

CI regression uses only UCIE-authored inert public API fixtures. A
passing synthetic API mock neither verifies actual API rate limits nor
proves the Windows operating task works or that fixes work in production.

**Go/no-go: DEVELOPMENT CI only. Rulepack/host/learning/production remain
NO_GO until separate human approval and independent evidence.**
