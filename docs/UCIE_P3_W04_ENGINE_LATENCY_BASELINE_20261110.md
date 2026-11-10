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

## 2026-11-10 Windows owner one-file read-only acceptance

A separately approved UCIE-only test at the exact `D:/UCIE` Windows owner checkout ran `tests/test_ucie_p3_owner_readonly_latency_v01.py` **once**, with one warmup plus two measurements. The owner run completed 1/1 PASS in Python 3.15.0 and reported only aggregate public UCIE metadata; the synthetic unit suite separately passed 11/11.

| Stage (different workloads) | Median | Max | Bound |
| --- | ---: | ---: | --- |
| Existing Stage10/12/15 handoff load + linkage validation | 102.290 ms | 104.190 ms | 2 measured samples |
| W04 substring `python`, loaded handoff only | 21.030 ms | 21.416 ms | 649 matches |
| W04 substring `git`, loaded handoff only | 20.107 ms | 20.302 ms | 129 matches |
| W04 empty query, loaded handoff only | 21.196 ms | 21.350 ms | 1,063 matches |
| P8 exact-key public catalog full call (24 queries, 2 internal repeats) | 23.872 ms | 24.012 ms | 2 measured samples |
| P8 internal linear scan, same exact-key work | 1.476 ms | 1.503 ms | internal median per call |
| P8 internal ephemeral index INCLUDING build | 0.165 ms | 0.166 ms | internal median per call |

Observed linked public review rows: **1,063**. This is a count of source-linked review revisions, not 1,063 distinct upstream PRs or approved SkillBooks. Stable, same-run public catalog SHA-256: `da434686551b810708e5f9b6d04a1a697387e4964953889a0dc7cf7ce253aaf1`. Receipt status: `OBSERVATIONAL_BASELINE_ONLY_NO_OPTIMIZATION`; owner host scope `EXACT_D_UCIE_WINDOWS_SINGLE_TEST_FILE`. Owner test returned `exit_code=0`; no network requests, operating DB writes, index persistence, rule promotion or UI changes reported.

**Diagnostic interpretation:** source load/validation appears ~4.9x slower than a single already-loaded W04 substring query on this tiny observation set. This identifies the first *inspection target*, not a proven root cause, user HTTP latency, reproducible speedup, or an SLO violation. The P8 exact-key inner timings describe a different workload and do not license a W04 index swap. Next stage: targeted breakdown of the existing validation pipeline, source SHA/owner safeguards, and a separate regression-backed optimization proposal *only if* additional equivalent-workload evidence warrants it.

**Release:** exact new HEAD CI remains to be verified; PR stays DRAFT. Commercial/customer online release, SkillBook promotion, signing and redistribution remain NO_GO.
