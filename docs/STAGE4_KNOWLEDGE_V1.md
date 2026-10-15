# UCIE Stage 4 Knowledge V1 — isolated, candidate-only

Stage 4 adds `runtime/knowledge.sqlite3` independently of the active
`runtime/public_miner.sqlite3`; the running Windows scheduled collector is not
modified. It does not fetch external data or copy raw upstream code.

Run only after the PR is reviewed/merged, in the existing `D:\UCIE` checkout:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe .\scripts\local_db_preflight.py
.\.venv\Scripts\python.exe .\scripts\knowledge_import_once.py
```

The import opens the existing miner DB read-only, validates all imported
records against the two miner-approved source identities and canonical URLs,
and inserts only SHA256 digests and metadata with `INSERT OR IGNORE`.
Repeated imports do not duplicate rows. Source candidate metadata remains
unverified. This does not independently validate original PR licenses,
security advisories or claim a fix has been reproduced.

The separate `rule_candidates` table holds only manual hash-only proposals.
Its SQL CHECK forbids `VERIFIED` status; no auto-promotion or learning
retraining is implemented. Distinct dispositions allow explicit quarantine
and retraction in a later reviewed workflow; automatic delete/opt-out
processing is not yet operational.

The `backup_knowledge` API makes an SQLite-consistent snapshot within
`runtime/` without replacing an existing backup. Restore was tested from a
snapshot in offline unit tests, but a production disaster-recovery procedure
and off-device backup destination remain unapproved.

Safety: no registration of any new Windows task, no modification of the
existing collector, no migration/rewriting of the original 11 candidate
records or 4 run records, no access to other projects, no automated rule
promotion. The on-disk Knowledge V1 schema only covers the two previously
approved miner sources; expanded approved sources need separate code review.
