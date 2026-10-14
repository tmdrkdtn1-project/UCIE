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
    args = parser.parse_args(argv)
    try:
        if args.action == "mine-once":
            result = mine_once(ROOT, sources=(args.source,) if args.source else PUBLIC_SOURCES,
                               max_new_per_source=args.limit)
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
