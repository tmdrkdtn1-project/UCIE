# UCIE Stage 9 — Public Intelligence, Adaptive Triage and Skill Profiles

**New development axis:** Improve what UCIE *discovers and can help with*,
rather than only adding internal release gates.

## Approved sources and real public evidence

The discovery adapter now supports all **five** specifically approved public
independent repositories:

| Public GitHub source | Reusable UCIE skill lane |
| --- | --- |
| python/cpython | Python runtime safety |
| PowerShell/PowerShell | PowerShell safe calls |
| git/git | Git workflow prevention |
| modelcontextprotocol/python-sdk | MCP/API compatibility |
| actions/runner-images | GitHub Actions runner environment drift |

Six manually spot-checked PRs from the five actual public repositories and
their merged commit SHA/timestamp were recorded in
`docs/evidence/stage9_approved_public_spotcheck_20261014.json`.
These are real, public PR *metadata* observations, not synthetic PR
identities or an assertion that the automatic collector ran on Windows.

Key change in usefulness: MCP SDK error-parameter contracts and
Python 3.15 support, plus runner image compatibility, can now appear as
candidate research tasks, whereas the prior 2-repo miner could not even
see them. Git's old translation typo fix is recognized as stale, not
mistaken for a new technical finding; PowerShell changelog metadata is
not treated as an independently tested bug fix.

This sample is deliberately nonexhaustive, and real PR merge metadata
alone does **not** prove severity, applicability, license clearance or
independent regression reproduction.

## 1. Public data collection — one-shot, hash-only

`ucie_miner.public_discovery` requests only exact anonymous GET URLs
against those five GitHub public pull-list endpoints, one 20-record page
per source. It allows **no arbitrary URL, token, redirect, patch download,
code execution, private repository expansion or extra paging**.

It emits canonical source/PR/merge metadata, the public PR title SHA-256,
bounded error-family tags and a time window of 90 days. It never stores
raw PR titles, bodies, code or PR diffs; uninteresting PRs and old matches
can be dropped. Zero valid new leads is an acceptable result.

**This new collector is opt-in.** Existing `scripts/public_miner_cycle.py`
and its two-source hourly Windows worker are unchanged, to avoid a
surprise operating authorization or schedule migration.

## 2. Adaptive triage — without permanent learning

`ucie_miner.adaptive_priority` ranks bounded public-only leads using
relevance tags, recency and **explicit, transient** reviewer feedback.
It applies source/PR opt-outs, deduplicates against the existing UCIE
miner's candidate IDs through SQLite read-only mode, and round-robins
five source categories to reduce dominance by one repository.

No user-project data, past private conversations, model weights, or
persistent feedback store are used. The rankings are deterministic,
reversible and explainable. Feedback marked SKIP suppresses its candidate;
an opted-out source is **not fetched at all**.

Only an already authorized human review can create or approve a rule.
A high priority score is never a security PASS or a production approval.

## 3. Real reusable UCIE skills

`ucie_miner.skill_profiles` routes each selected lead to one of five
domain-specific questions and safe next steps, such as:

- Python: validate an iterator/concurrency fix on a reviewed isolated build.
- PowerShell: compare command metadata/path contract against version.
- Git: reproduce proposed error corrections in throwaway repositories.
- MCP/API: check public SDK version and declared argument/error schemas.
- Runner: verify the exact hosted image/tool version drift.

The reusable repo playbook at
`skills/ucie-public-intelligence/SKILL.md` captures discovery,
deduplication, adaptive selection and manual independent review.
It is committed source **not an installed ChatGPT skill**.

## Read-only entrypoints

In an independently reviewed UCIE checkout:

```powershell
# Anonymous public API metadata reads; one-shot, max 5 feed GETs.
.\.venv\Scripts\python.exe -m ucie_miner discover-public --live

# One approved source only:
.\.venv\Scripts\python.exe -m ucie_miner discover-public --live --source modelcontextprotocol/python-sdk

# An explicit opt-out is honored BEFORE making a request:
.\.venv\Scripts\python.exe -m ucie_miner discover-public --live --skip-source git/git

# Offline synthetic/public JSON discovery receipt through stdin; no network:
# python -m ucie_miner preview-intelligence-stdin
```

A bare `discover-public` without `--live` fails closed. These commands
**do not migrate**, import or persist candidates or change a scheduler.

## Acceptance boundaries

- Development CI uses only bounded UCIE-authored synthetic fixtures.
- Public spot-checks were performed separately on exactly approved
  public upstream repositories.
- A source PR's mere existence, SHA or title is not verified learning.
- Current priorities/skill tasks are **UNVERIFIED_RESEARCH_AGENDA**.
- Existing Stage 4–8 independent approval and operational `NO_GO`
  remain intact.
- No `main` merge, permanent DB write/import, owner-PC run,
  scheduler registration, auto promotion, independent Rulepack signing,
  package publishing or ChatGPT skill installation.

**Next evolution (not claimed here):** official release/advisory source
adapters; controlled opt-in read-only deployment to `D:/UCIE` after
independent review; explicit version applicability, provenance and
compliance checks for new public skills.
