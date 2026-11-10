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

## 2026-11-10 source-linkage read-only phase attribution (second owner test)

The separately bounded, owner-only Windows test `tests/test_ucie_p3_owner_handoff_phase_v01.py` returned **1/1 PASS**, preserving and calling the original Stage10/15 readers, review proposal builder and source-linkage validator. It used one warmup plus two recorded samples. The function-wrappers are process-local and restored immediately; no production implementation or trust gate was replaced.

| Phase from the existing public-only handoff | Median | Maximum |
| --- | ---: | ---: |
| Full source-linked handoff | 105.556 ms | 106.171 ms |
| Entire Stage10/15 source map + reconstruction | 96.438 ms | 97.319 ms |
| Stage10 public candidate reader | 1.841 ms | 1.859 ms |
| **Stage15 public fix-evidence reader** | **89.452 ms** | 90.313 ms |
| Other source-map bookkeeping | 5.145 ms | 5.182 ms |
| Review ledger cross-check + task rendering | 9.118 ms | 9.384 ms |
| Within source-map: review proposal construction (nested) | 4.853 ms | 4.859 ms |

The Stage15 reader took ~84.7% of the measured full handoff duration. This isolates the **first credible optimization investigation target**. The approved public Stage15 reader currently calls `audit_external_evidence_chain(root)` (which reads the Stage13 history and Stage15 fix ledger), then calls `_history(root)` and `_fix(root)` a second time. The repeated reads are visible in the current source, but **we have not independently measured their individual contribution or proven a safe substitute**. Do not skip the cross-ledger audit, immutable identity linkage, opt-in marker check, SQLite identity/schema/quick_check or fail-closed behavior. A future refactor must retain all these validations and demonstrate equivalence under concurrent ledger updates, tampering, missing ledgers, duplicate source rows and owner-host regression testing.

This owner test measured **1,063** source-linked public revision rows, stable across its three reads. The internal untrusted public task-ID digest is `29b550afd19db15378e938dda61009573110e4f53b370c0af28108d05e7c395f`; this is a local consistency marker and not an approval or distribution signature.

**Current decision:** Stage15 is a candidate for a separately reviewed lossless read-path refactor. No performance optimization has yet been applied; V04 presentation, original public reader, runtime SQLite, operating scheduler, C40 and customer release state remain unchanged.

## 2026-11-10 Stage15 repeated-read attribution: one-shot Windows follow-up

An additional **owner-host read-only one-file test** (`tests/test_ucie_p3_owner_stage15_duplicate_read_v01.py`) observed the existing Stage16 auditor and the two source readers exactly as-is. It ran one warmup and two measured samples and returned 1/1 PASS. The original `_history` and `_fix` readers were observed **twice each** in a single Stage15 read (first for audit, then after audit). Wrappers were temporary/pass-through, never a bypass or production change.

| Stage15 public-only phase | Median elapsed |
| --- | ---: |
| Full Stage15 reader | 83.984 ms |
| Initial Stage13 history read inside the audit | 23.912 ms |
| Initial Stage15 fix-evidence read inside the audit | 4.939 ms |
| **Second Stage13 + Stage15 read after the audit** | **28.780 ms** |
| Audit validation plus subsequent row processing | 26.353 ms |

The second Stage13/15 read accounted for ~34.3% of the observed Stage15 duration in this run, representing a **measured read-path duplication candidate**, not a guaranteed savings if removed. Within 925 Stage15 unverified public evidence revisions, the stable same-run source snapshot SHA-256 was `7805952bf29d2523becbe67bbc229dd3d97e53567efb0cd1029f047f99b013bd`. No network requests or operating DB writes were invoked.

**Do not remove any validation now.** A safe Stage15 refactor must share one fully validated immutable snapshot while preserving the exact original Stage13 and Stage15 DB identity, schema, integrity, linkage, row guards, opt-in marker and missing/corrupt-source failure semantics. Prove equivalence against tampering, source changes, missing files and source-revision drift on isolated fixtures and then Windows owner-host exact-source acceptance before any production change. All P3 performance findings remain observations with no speedup guarantee or customer HTTP benchmark.
