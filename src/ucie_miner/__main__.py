"""UCIE public-only miner and offline-first review CLI.

Review never auto-promotes, deploys, signs or runs untrusted upstream code.
"""
import argparse
import json
from pathlib import Path
import sqlite3

from .core import MiningError, PUBLIC_SOURCES, mine_once, report
from .review import ReviewError, _read_candidates, analyze, review_and_store
from .provenance_review import inspect_public_prs
from .license_review import inspect_pinned_licenses
from .regression_plans import create_regression_matrix
from .acceptance_bundle import build_readonly_acceptance_preview
from .merge_snapshot import compare_merge_snapshot
import os
import sys
from .integration import preview_knowledge_rules
from .static_concurrency import MAX_SOURCE_BYTES, inspect_python_scandir_source
from .static_rule_bridge import preview_static_rule_candidates
from .review_docket import prepare_independent_review_docket
from .public_discovery import SOURCES as DISCOVERY_SOURCES, public_feed_get
from .public_intelligence import discover_and_prioritize_live, public_intelligence_preview
from .public_knowledge_pipeline import collect_public_knowledge_candidate, preview_public_knowledge_receipt
from .public_batch import build_public_batch, review_batch_preview
from .public_batch_host import inspect_public_batch_host
from .public_skill_digest import compare_public_skill_batches
from .public_candidate_staging import stage_public_candidates, inspect_staged_candidates

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None):
    parser = argparse.ArgumentParser(description="UCIE unverified PUBLIC_ONLY candidate miner")
    sub = parser.add_subparsers(dest="action", required=True)
    mine = sub.add_parser("mine-once", help="GET limited public PR fixes, store UNVERIFIED candidates")
    mine.add_argument("--source", choices=PUBLIC_SOURCES)
    mine.add_argument("--limit", type=int, default=2)
    sub.add_parser("report", help="Create a local candidate-count report")
    review = sub.add_parser("review", help="Deduplicate PR families, stage unapproved candidate review")
    review.add_argument("--preview", action="store_true", help="Read-only: do not write review DB or receipt")
    review.add_argument("--verify-live", action="store_true",
                        help="Explicit anonymous reads of allowlisted public PRs and pinned release tag files")
    sub.add_parser("preview-chain", help="Read-only Stage 4-7 preview; no import, verification or deployment")
    provenance = sub.add_parser("audit-provenance", help="Bounded, metadata-only, read-only provenance review")
    provenance.add_argument("--verify-live", action="store_true",
                            help="Explicit anonymous GitHub API GETs; no patch or license approval")
    lic = sub.add_parser("audit-license", help="Pinned public license markers only; no approvals")
    lic.add_argument("--verify-live", action="store_true",
                     help="Explicit anonymous GET of pinned official upstream license documents")
    sub.add_parser("preview-regressions", help="Generate nonexecuting regression test plans")
    sub.add_parser("preview-acceptance", help="Read-only NO-GO host and evidence observation")
    pin = sub.add_parser("audit-merge-snapshot", help="Compare pinned public PR merge SHA, without DB writes")
    pin.add_argument("--verify-live", action="store_true",
                     help="Explicit anonymous public PR metadata GETs and pinned SHA checks")
    pyscan = sub.add_parser("scan-python-stdin", help="Parse only explicitly supplied approved public/synthetic Python text from stdin; no code execution or file scans")
    pyscan.add_argument("--preview-candidates", action="store_true",
                        help="Link heuristic findings to unverified Stage 6 proposals; no DB writes")
    sub.add_parser("preview-static-json-stdin", help="Link explicitly supplied untrusted static-scan JSON to nonexecuting rule/plan candidates")
    sub.add_parser("preview-review-docket-stdin", help="Offline structural review agenda for two supplied candidate receipts, never approval")
    discover = sub.add_parser("discover-public", help="Explicit one-shot public 5-repo metadata discovery and adaptive review; no writes")
    discover.add_argument("--live", action="store_true",
                          help="Required opt-in anonymous metadata GET against the approved public 5 repositories")
    discover.add_argument("--source", choices=DISCOVERY_SOURCES)
    discover.add_argument("--skip-source", action="append", choices=DISCOVERY_SOURCES, default=[])
    discover.add_argument("--limit", type=int, default=12)
    sub.add_parser("preview-intelligence-stdin", help="Offline JSON public metadata leads to 5-skill agenda; no network or code execution")
    collect = sub.add_parser("collect-public-evidence", help="Opt-in four-route public diff/doc/release/advisory evidence for one approved PR; no writes")
    collect.add_argument("--live", action="store_true", help="Explicitly allow bounded anonymous public GET requests")
    collect.add_argument("--source", required=True, choices=DISCOVERY_SOURCES)
    collect.add_argument("--pr", type=int, required=True)
    collect.add_argument("--merge-sha", required=True)
    collect.add_argument("--skip-doc", action="store_true")
    collect.add_argument("--skip-advisory", action="store_true")
    sub.add_parser("preview-public-evidence-stdin", help="Bounded offline untrusted public evidence receipt review; no network or writes")
    batch = sub.add_parser(
        "batch-public-evidence",
        help="Explicit one-shot five-source discovery, dedupe, 1-3 PR enrichments and skill tasks; never write")
    batch.add_argument("--live", action="store_true",
                       help="Required approval for bounded anonymous public metadata and evidence GETs")
    batch.add_argument("--source", choices=DISCOVERY_SOURCES)
    batch.add_argument("--skip-source", action="append",
                       choices=DISCOVERY_SOURCES, default=[])
    batch.add_argument("--skip-pr", action="append", default=[],
                       help="Approved public owner/repo#PR explicit opt-out")
    batch.add_argument("--limit", type=int, default=2)
    batch.add_argument("--backfill-pages", type=int, choices=(1, 2, 3), default=1,
                       help="Bounded public PR backfill pages per source; max 3")
    batch.add_argument("--skip-doc", action="store_true")
    batch.add_argument("--skip-advisory", action="store_true")
    sub.add_parser("preview-public-batch-stdin",
                   help="Review bounded offline public-only batch receipt, never sign or auto-promote")
    sub.add_parser("preview-public-skill-digest-stdin",
                   help="Compare two bounded public-only batches and report new/changed skill leads; no writes")
    sub.add_parser("preflight-public-batch-host", help="UCIE-local Windows 3.15/SQLite read-only acceptance preview; always NO-GO")
    stage = sub.add_parser(
        "stage-public-candidates-stdin",
        help="Validate and stage up to 3 UNVERIFIED public candidates, ephemeral unless disk explicitly permitted")
    stage.add_argument("--write-separate-ledger", action="store_true",
                       help="Explicit write to dedicated UCIE Stage 10 candidate-only DB, never to miner/Knowledge")
    sub.add_parser("inspect-public-candidate-ledger",
                   help="Read-only inspection of separate Stage 10 candidate staging; no file creation")
    args = parser.parse_args(argv)
    try:
        if args.action == "mine-once":
            result = mine_once(ROOT, sources=(args.source,) if args.source else PUBLIC_SOURCES,
                               max_new_per_source=args.limit)
        elif args.action == "scan-python-stdin":
            data = sys.stdin.buffer.read(MAX_SOURCE_BYTES + 1)
            if len(data) > MAX_SOURCE_BYTES:
                raise ValueError("input is oversized")
            scan = inspect_python_scandir_source(data.decode("utf-8", errors="strict"))
            result = (preview_static_rule_candidates(ROOT, scan)
                      if args.preview_candidates else scan)
        elif args.action == "preview-static-json-stdin":
            data = sys.stdin.buffer.read(MAX_SOURCE_BYTES + 1)
            if len(data) > MAX_SOURCE_BYTES:
                raise ValueError("input is oversized")
            def unique_fields(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("duplicate untrusted JSON property")
                    result[key] = value
                return result
            scan = json.loads(data.decode("utf-8", errors="strict"),
                              object_pairs_hook=unique_fields)
            result = preview_static_rule_candidates(ROOT, scan)
        elif args.action == "preview-review-docket-stdin":
            data = sys.stdin.buffer.read(MAX_SOURCE_BYTES + 1)
            if len(data) > MAX_SOURCE_BYTES:
                raise ValueError("input is oversized")
            def unique_docket_fields(pairs):
                unique = {}
                for key, value in pairs:
                    if key in unique:
                        raise ValueError("duplicate receipt property")
                    unique[key] = value
                return unique
            inputs = json.loads(data.decode("utf-8", errors="strict"),
                                object_pairs_hook=unique_docket_fields)
            if not isinstance(inputs, dict) or set(inputs) != {
                    "static_preview", "external_review"}:
                raise ValueError("two bounded untrusted receipts required")
            result = prepare_independent_review_docket(
                inputs["static_preview"], inputs["external_review"])
        elif args.action == "discover-public":
            if not args.live:
                raise ValueError("public live reads require explicit opt-in")
            result = discover_and_prioritize_live(
                fetch=public_feed_get, root=ROOT,
                sources=(args.source,) if args.source else DISCOVERY_SOURCES,
                opted_out_sources=tuple(args.skip_source),
                limit=args.limit,
            )
        elif args.action == "collect-public-evidence":
            if not args.live:
                raise ValueError("public code/document/release API reads require --live")
            result = collect_public_knowledge_candidate(
                args.source, args.pr, merge_sha=args.merge_sha,
                include_doc=not args.skip_doc,
                include_advisory=not args.skip_advisory,
            )
        elif args.action == "preview-public-evidence-stdin":
            data = sys.stdin.buffer.read(262145)
            if len(data) > 262144:
                raise ValueError("oversized public evidence receipt")
            def unique_evidence_fields(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("duplicate untrusted evidence field")
                    result[key] = value
                return result
            payload = json.loads(data.decode("utf-8", "strict"),
                                 object_pairs_hook=unique_evidence_fields)
            result = preview_public_knowledge_receipt(payload)
        elif args.action == "batch-public-evidence":
            if not args.live:
                raise ValueError("public batch reads require explicit --live")
            def public_optout(key):
                if not isinstance(key, str) or key.count("#") != 1:
                    raise ValueError("invalid public opt-out PR")
                source, number = key.split("#")
                if source not in DISCOVERY_SOURCES or not number.isascii() or not number.isdigit():
                    raise ValueError("unapproved public PR opt-out")
                return (source, int(number))
            opted_prs = tuple(public_optout(key) for key in args.skip_pr)
            result = build_public_batch(
                sources=(args.source,) if args.source else DISCOVERY_SOURCES,
                root=ROOT,
                opted_out_sources=tuple(args.skip_source),
                opted_out_prs=opted_prs,
                max_enrich=args.limit,
                backfill_pages=args.backfill_pages,
                include_docs=not args.skip_doc,
                include_advisories=not args.skip_advisory,
            )
        elif args.action == "stage-public-candidates-stdin":
            data = sys.stdin.buffer.read(262145)
            if len(data) > 262144:
                raise ValueError("oversized untrusted public batch for staging")
            def unique_stage_keys(pairs):
                output = {}
                for key, value in pairs:
                    if key in output:
                        raise ValueError("duplicate staging receipt property")
                    output[key] = value
                return output
            receipt = json.loads(data.decode("utf-8", "strict"),
                                 object_pairs_hook=unique_stage_keys)
            result = stage_public_candidates(
                receipt,
                root=ROOT if args.write_separate_ledger else None,
                allow_disk_write=args.write_separate_ledger,
            )
        elif args.action == "inspect-public-candidate-ledger":
            result = inspect_staged_candidates(ROOT)
        elif args.action == "preflight-public-batch-host":
            result = inspect_public_batch_host(
                ROOT, is_windows=os.name == "nt",
                python_version=tuple(sys.version_info[:2]))
        elif args.action == "preview-public-skill-digest-stdin":
            data = sys.stdin.buffer.read(262145)
            if len(data) > 262144:
                raise ValueError("oversized public skill digest input")
            def no_duplicates(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("duplicate untrusted public digest property")
                    result[key] = value
                return result
            envelope = json.loads(data.decode("utf-8", errors="strict"),
                                  object_pairs_hook=no_duplicates)
            if (not isinstance(envelope, dict)
                    or set(envelope) != {"current", "previous"}):
                raise ValueError("public current/previous receipts required")
            result = compare_public_skill_batches(
                envelope["current"], envelope["previous"])
        elif args.action == "preview-public-batch-stdin":
            data = sys.stdin.buffer.read(262145)
            if len(data) > 262144:
                raise ValueError("oversized untrusted public batch")
            def unique_batch_fields(pairs):
                obj = {}
                for key, val in pairs:
                    if key in obj:
                        raise ValueError("duplicate public batch property")
                    obj[key] = val
                return obj
            raw = json.loads(data.decode("utf-8", "strict"),
                             object_pairs_hook=unique_batch_fields)
            result = review_batch_preview(raw)
        elif args.action == "preview-intelligence-stdin":
            data = sys.stdin.buffer.read(262145)
            if len(data) > 262144:
                raise ValueError("public candidate JSON input too large")
            def unique_public_properties(pairs):
                o = {}
                for key, value in pairs:
                    if key in o:
                        raise ValueError("duplicate public receipt key")
                    o[key] = value
                return o
            raw = json.loads(data.decode("utf-8", "strict"),
                             object_pairs_hook=unique_public_properties)
            result = public_intelligence_preview(raw)
        elif args.action == "report":
            path = report(ROOT)
            result = {"status": "LOCAL_REPORT_WRITTEN", "path": str(path)}
        elif args.action == "audit-merge-snapshot":
            local_rows = _read_candidates(ROOT)
            remote = inspect_public_prs(local_rows, verify_live=args.verify_live)
            result = compare_merge_snapshot(ROOT, local_rows, remote)
        elif args.action == "audit-license":
            result = inspect_pinned_licenses(ROOT, verify_live=args.verify_live)
        elif args.action == "preview-regressions":
            result = create_regression_matrix(preview_knowledge_rules(ROOT)["rulepack_preview"])
        elif args.action == "preview-acceptance":
            result = build_readonly_acceptance_preview(
                ROOT, is_windows=os.name == "nt",
                python_version=tuple(sys.version_info[:2]))
        elif args.action == "audit-provenance":
            result = inspect_public_prs(_read_candidates(ROOT), verify_live=args.verify_live)
        elif args.action == "preview-chain":
            result = preview_knowledge_rules(ROOT)
        elif args.preview:
            result = analyze(ROOT, verify_live=args.verify_live)
        else:
            result = review_and_store(ROOT, verify_live=args.verify_live)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (MiningError, ReviewError, OSError, ValueError, sqlite3.DatabaseError) as exc:
        # Never print remote error messages which might contain untrusted content.
        print(json.dumps({"status": "FAIL_CLOSED", "reason_type": type(exc).__name__}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
