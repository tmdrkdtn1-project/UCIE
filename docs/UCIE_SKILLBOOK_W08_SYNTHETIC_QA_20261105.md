# UCIE W08 — SkillBook 001 first-party synthetic QA receipt, 2026-11-05

Status: first-party experiment only, **NOT independent QA, security certification,
license signoff, owner release approval, or portable package publication**.

This follows SkillBook 001's fixed Python \`os.scandir\` recipe and the read-only
two-shelf virtual library. It does not change W04 searches, approved source
allowlists, SQLite, the hourly miner, C40, or any other UCIE service.

## What actually runs

\`ucie_miner.skillbook_scandir_qa_v01.evaluate_skillbook_scandir()\` invokes the
existing **UCIE-authored** \`bounded_regular_file_names\` only on newly created
temporary synthetic directories; it never accepts a caller's real directory.
Nine bounded probes cover sorted nonrecursive filenames, empty directories,
inclusive entry limits, counting of directory entries, input rejection,
**mocked** symlink preflight, iterator close on overflow, iterator close on
metadata failure, and fail-closed \`scandir\` opening errors.

All synthetic fixtures are cleaned when the function returns. The report
includes the current recipe source SHA-256, the official-document digest
**previously pinned** to \`python/cpython\`, the Python runtime, each observed
probe result, and a reproducible canonical JSON receipt SHA-256. Source
identity and approval flags must remain unchanged. A failed probe makes the
receipt \`SYNTHETIC_REGRESSION_FAILED_NO_GO\`; it cannot be promoted.

No input path, project telemetry, private source, external code, raw stacktrace,
network request or running UCIE database is read by the experiment.
The runner does write small disposable synthetic test files in the OS temp
location; this is not an operating database mutation.

## Owner-local run

Run in the existing Windows owner's UCIE checkout, one shot:

    & 'D:\UCIE\scripts\ucie_skillbook_scandir_qa_v01.ps1'

Expected output is a single JSON object. \`case_count=9\` and
\`passed_count=9\` may mean **first-party synthetic pass only**. It never sets
\`independent_qa_verified\`, \`security_review_approved\`,
\`license_redistribution_approved\`, \`signed\`, or \`export_allowed\` to true.

In development/CI, test exactly:

    python -m unittest tests.test_ucie_skillbook_scandir_qa_v01

## Explicitly not proved

- An independent tester rerunning the implementation and verifying evidence
- Real symlink/junction permissions on all OS configurations
- TOCTOU races, security sandboxing, permissions, public workload performance
- Rights to publish/package, compatibility with arbitrary consumer projects
- Python version support beyond actually observed CI environments

No automated learning/model training, export, release, or scheduling is performed.
