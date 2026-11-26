# UCIE ACG Draft Zero CI + Recovery, 2026-11-26
PROJECT=UCIE; repository=tmdrkdtn1-project/UCIE. REVIEW ONLY until exact-head full CI.

Recovery before gate: acg-recovery/ucie-main-pre-draft-zero-20261126 -> 98a3b5b08b466c2f0ae897c039df0719f94f98d6
Recovery before V2 change: acg-recovery/ucie-v2-b5-pre-gate-20261126 -> 0de08c7870b0911f25c2cff53b927cc9ca3cb40c.
These are remote GitHub committed code references, NOT owner-local snapshots, uncommitted-file backups, SQLite backups, or passed CI evidence.

Ordinary Draft PR opened/reopened/synchronize: Stage1 job skipped (no Runner), NOT a PASS.
Fresh explicit ucie-full-ci labeled event on Draft: full original four jobs, subject to actual success.
Ready-for-review or non-Draft source update: four actual jobs even with no label.
Main push: original four actual jobs; old PR-only concurrency, not main cancellation.
Label persistence during Draft synchronize does not retrigger paid suite; unlabeled no trigger.
All specialist/native workflows are preserved; long-lived V2 branches may still use old YAML.

Snapshot helper scripts/ucie_acg_snapshot_guard_v01.py is dormant. On clean owner-approved repo only, it creates new refs/acg/snapshots/UCIE/<id> from committed HEAD with explicit approve-write, never resets or captures dirty files.
Missing branch protection: main reports protected=false and rulesets=[]. GitHub skipped jobs can display green. Before any merge, operator MUST inspect exact-head real four-job GitHub runner receipts plus scoped native test gates. This is NOT server-enforced until independent owner-configured branch protection is established.
Frozen V04, owner Windows dirty tree, operating SQLite, Windows tasks, C40/Tunnel, source allowlist, other projects, signed rulepacks and releases untouched.
Measured charges still UNKNOWN; do not claim 100 percent global Actions savings.
