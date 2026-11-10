# UCIE P3 W04 and public catalog engine read-only latency baseline — 2026-11-10

PROJECT=UCIE ONLY. STATUS=DRAFT_OBSERVATION_NOT_OWNER_HOST_VERIFIED.
Priority: retain customer V04 premium dark UI unchanged, especially /local and /local/evolution. Local product first. Customer release NO_GO.

## Measurement implementation

- New module: src/ucie_miner/p3_readonly_latency_v01.py
- Existing functions used: prepare_verification_handoff, search_linked_public_candidates, benchmark_linked_public_catalog.
- Separate elapsed timings: (1) public-only source-linked handoff load, (2) W04 substring search for python/git/empty on that same loaded handoff, (3) P8 exact-key engine including index build.
- Default: one warmup plus three measured samples; fixed 24 exact-key queries and two engine inner repetitions. Limits: samples 1..5, warmups 0..2.
- Aggregate only: median, nearest-rank p95, max milliseconds, counts and SHA256 source-linked catalog fingerprint. No raw evidence rows, local paths or sensitive content printed.
- Strict status/safety flags, stable snapshot and counts, and exact engine-result equivalence required. Any failed gate emits sanitized FAIL_CLOSED_NO_MEASUREMENT.

## Owner command AFTER source review and safe UCIE-only deployment

PowerShell: set PYTHONPATH=D:\UCIE\src
Run: & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.p3_readonly_latency_v01 --ucie-root 'D:\UCIE' --samples 3 --warmups 1

Do not overwrite existing dirty/untracked owner files. This is NOT an automated/scheduled job. No C40 restart, task control, public API requests, new index, SQLite writes, changed customer UI or other-project access.

## Meaning and limits

- Timings report in-process read/validation, in-memory W04 query, and P8 exact-key algorithm separately; these workloads are NOT equivalent.
- No HTTP or customer UI response-time benchmarking. No proof of Windows host speed, root cause, SLO or production performance gain.
- Larger observed latency is a candidate for investigation, not permission to optimize. A verified host baseline and source SHA review must precede any proposed change.
- A first-party synthetic test pass is separate from independent QA and owner-host measurement.
- All candidates remain unverified; no approval, auto promotion, signing, export, or product release. SkillBook003 stays draft, 09:00 report stays on hold.

## Regression scope

tests/test_ucie_p3_readonly_latency_v01.py checks bounded inputs, stable snapshot, incomplete-source and fake approval rejection, mismatched engine responses, monotonic timing, sanitized errors, and zero output side-effect claims. Only the three new P3 files belong to this change.

NEXT_OWNER=UCIE integrated development workroom / owner Windows read-only acceptance.
RELEASE=NO_GO.
