"""Manual-only CLI. No scheduled jobs, external network, project connectors or installation."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .policy import PolicyError
from .rulepack import generate_keys, publish_demo, verify_demo
from .prevention_rulepack import (
    publish_prevention_review, verify_prevention_review,
)
from .production_release import publish_production, verify_production
from .owner_release import publish_owner_risk_release, verify_owner_risk_release
from .multi_review import publish_multi_review, verify_multi_review, scan_multi_review_receipt
from .multi_owner_release import (
    publish_two_rule_owner_release, verify_two_rule_owner_release,
    scan_two_rule_owner_receipt,
)
from .selected_release import (
    publish_selected_owner_release, verify_selected_owner_release,
    scan_selected_owner_receipt,
)
from .mixed_release import (
    publish_mixed_owner_release, verify_mixed_owner_release,
    scan_mixed_owner_receipt,
)
from .rule_admission import reconcile_mixed_signed_candidates

ROOT = Path(__file__).resolve().parents[2]


def _strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PolicyError("duplicate scanner receipt JSON key")
        result[key] = value
    return result



def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="ucie-public-demo", description="UCIE stage-1 OFFLINE public-only prototype")
    sub = p.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("keygen-demo", help="Generate nonproduction example keypair in a NEW directory")
    gen.add_argument("--out", required=True, type=Path)
    pub = sub.add_parser("publish-demo", help="Build signed demo-only public-only Rulepack")
    pub.add_argument("--private-key", required=True, type=Path)
    pub.add_argument("--serial", default=1, type=int)
    pub.add_argument("--output", default=ROOT / "build" / "demo_rulepack.zip", type=Path)
    ver = sub.add_parser("verify-demo", help="Verify signature, integrity, source policies and probes")
    ver.add_argument("--pack", required=True, type=Path)
    ver.add_argument("--trust", required=True, type=Path)
    ver.add_argument("--min-serial", default=1, type=int)
    prvkey = sub.add_parser("keygen-prevention-review",
                            help="Create separate review-only signing keypair")
    prvkey.add_argument("--out", required=True, type=Path)
    pack = sub.add_parser("publish-prevention-review",
                          help="Explicit manually signed first-rule portable review pack")
    pack.add_argument("--private-key", required=True, type=Path)
    pack.add_argument("--output", required=True, type=Path)
    pack.add_argument("--serial", type=int, required=True)
    pack.add_argument("--confirm", required=True)
    chk = sub.add_parser("verify-prevention-review",
                         help="Offline recipient signature, scope, expiry, rollback checks")
    chk.add_argument("--pack", type=Path, required=True)
    chk.add_argument("--trust", type=Path, required=True)
    chk.add_argument("--min-serial", type=int, default=1)
    prodkey = sub.add_parser("keygen-production",
                             help="Generate SEPARATE owner production signing keys, manually")
    prodkey.add_argument("--out", required=True, type=Path)
    prod = sub.add_parser("publish-production",
                          help="Requires independent QA signature AND explicit owner authorization")
    prod.add_argument("--owner-private", required=True, type=Path)
    prod.add_argument("--qa-claim", required=True, type=Path)
    prod.add_argument("--qa-signature", required=True, type=Path)
    prod.add_argument("--qa-trust", required=True, type=Path)
    prod.add_argument("--output", required=True, type=Path)
    prod.add_argument("--serial", required=True, type=int)
    prod.add_argument("--confirm", required=True)
    checkprod = sub.add_parser("verify-production",
                               help="Recipient checks independent QA and owner signatures")
    checkprod.add_argument("--pack", required=True, type=Path)
    checkprod.add_argument("--owner-trust", required=True, type=Path)
    checkprod.add_argument("--qa-trust", required=True, type=Path)
    checkprod.add_argument("--min-serial", default=1, type=int)
    owner_release = sub.add_parser(
        "publish-owner-risk-release",
        help="Owner explicitly accepts missing independent QA; requires live public GitHub CI")
    owner_release.add_argument("--owner-private", type=Path, required=True)
    owner_release.add_argument("--output", type=Path, required=True)
    owner_release.add_argument("--run-id", type=int, required=True)
    owner_release.add_argument("--serial", type=int, required=True)
    owner_release.add_argument("--confirm", required=True)
    owner_release.add_argument("--accept-risk", required=True)
    owner_verify = sub.add_parser(
        "verify-owner-risk-release",
        help="Offline owner-signed public-only release verification; no human QA claim")
    owner_verify.add_argument("--pack", type=Path, required=True)
    owner_verify.add_argument("--owner-trust", type=Path, required=True)
    owner_verify.add_argument("--min-serial", type=int, default=1)
    two = sub.add_parser("publish-two-rule-review",
                         help="Explicit signed two-rule REVIEW ONLY pack, never production")
    two.add_argument("--private-key", type=Path, required=True)
    two.add_argument("--output", type=Path, required=True)
    two.add_argument("--serial", type=int, required=True)
    two.add_argument("--confirm", required=True)
    two_ver = sub.add_parser("verify-two-rule-review",
                             help="Offline signed two-rule review validation; never production")
    two_ver.add_argument("--pack", type=Path, required=True)
    two_ver.add_argument("--trust", type=Path, required=True)
    two_ver.add_argument("--min-serial", type=int, default=1)
    two_scan = sub.add_parser("scan-two-rule-review-json-stdin",
                              help="Review-only inert multi-rule scanner receipt, 128KiB max")
    two_scan.add_argument("--pack", type=Path, required=True)
    two_scan.add_argument("--trust", type=Path, required=True)
    two_scan.add_argument("--min-serial", type=int, default=1)

    multi_prod = sub.add_parser(
        "publish-two-rule-owner-risk-release",
        help="EXPLICIT two-rule PUBLIC_ONLY manual owner-risk release, never automated")
    multi_prod.add_argument("--owner-private", type=Path, required=True)
    multi_prod.add_argument("--output", type=Path, required=True)
    multi_prod.add_argument("--run-id", type=int, required=True)
    multi_prod.add_argument("--serial", type=int, required=True)
    multi_prod.add_argument("--confirm", required=True)
    multi_prod.add_argument("--accept-risk", required=True)
    multi_prod.add_argument("--accept-second-risk", required=True)
    multi_ver = sub.add_parser("verify-two-rule-owner-risk-release",
                               help="Offline authenticated two-rule owner-risk release")
    multi_ver.add_argument("--pack", type=Path, required=True)
    multi_ver.add_argument("--owner-trust", type=Path, required=True)
    multi_ver.add_argument("--min-serial", type=int, default=1)
    multi_scan = sub.add_parser("scan-two-rule-owner-receipt-stdin",
                               help="Review manually supplied inert PowerShell scanner JSON")
    multi_scan.add_argument("--pack", type=Path, required=True)
    multi_scan.add_argument("--owner-trust", type=Path, required=True)
    multi_scan.add_argument("--min-serial", type=int, default=1)
    selected_pub = sub.add_parser(
        "publish-selected-owner-risk-release",
        help="Explicitly select already verified public rules; per-rule owner consent required")
    selected_pub.add_argument("--owner-private", type=Path, required=True)
    selected_pub.add_argument("--output", type=Path, required=True)
    selected_pub.add_argument("--run-id", type=int, required=True)
    selected_pub.add_argument("--serial", type=int, required=True)
    selected_pub.add_argument("--rule-id", action="append", required=True)
    selected_pub.add_argument("--accept-risk", action="append", required=True)
    selected_pub.add_argument("--confirm", required=True)
    selected_ver = sub.add_parser(
        "verify-selected-owner-risk-release",
        help="Verify signed selected rules and individually pinned QA evidence")
    selected_ver.add_argument("--pack", type=Path, required=True)
    selected_ver.add_argument("--owner-trust", type=Path, required=True)
    selected_ver.add_argument("--min-serial", type=int, default=3)
    selected_scan = sub.add_parser(
        "scan-selected-owner-receipt-stdin",
        help="Filter only selected signed rules from inert PowerShell scanner JSON")
    selected_scan.add_argument("--pack", type=Path, required=True)
    selected_scan.add_argument("--owner-trust", type=Path, required=True)
    selected_scan.add_argument("--min-serial", type=int, default=3)
    mixed_pub = sub.add_parser(
        "publish-mixed-owner-risk-release",
        help="Explicit owner consent for each selected Python/PowerShell rule in V2 pack")
    mixed_pub.add_argument("--owner-private", type=Path, required=True)
    mixed_pub.add_argument("--output", type=Path, required=True)
    mixed_pub.add_argument("--run-id", type=int, required=True)
    mixed_pub.add_argument("--serial", type=int, required=True)
    mixed_pub.add_argument("--rule-id", action="append", required=True)
    mixed_pub.add_argument("--accept-risk", action="append", required=True)
    mixed_pub.add_argument("--confirm", required=True)
    mixed_ver = sub.add_parser(
        "verify-mixed-owner-risk-release",
        help="Offline signature and exact per-rule source/QA evidence receiver")
    mixed_ver.add_argument("--pack", type=Path, required=True)
    mixed_ver.add_argument("--owner-trust", type=Path, required=True)
    mixed_ver.add_argument("--min-serial", type=int, default=4)
    mixed_scan = sub.add_parser(
        "scan-mixed-owner-receipt-stdin",
        help="Inert Python or PowerShell static receipt against signed V2 rule selection")
    mixed_scan.add_argument("--pack", type=Path, required=True)
    mixed_scan.add_argument("--owner-trust", type=Path, required=True)
    mixed_scan.add_argument("--min-serial", type=int, default=4)
    reconcile = sub.add_parser(
        "reconcile-signed-public-candidates",
        help="Read-only owner-signed mixed Rulepack vs re-derived public miner queue; never approve new candidates")
    reconcile.add_argument("--pack", type=Path, required=True)
    reconcile.add_argument("--owner-trust", type=Path, required=True)
    reconcile.add_argument("--min-serial", type=int, default=4)
    args = p.parse_args(argv)
    try:
        if args.command == "keygen-demo":
            expected = (ROOT / ".build_keys").absolute()
            if args.out.absolute() != expected:
                raise PolicyError("demo key generation is limited to the dedicated UCIE directory")
            priv, pubkey = generate_keys(expected)
            result = {"result": "CREATED_DEMO_ONLY", "private": str(priv), "public": str(pubkey)}
        elif args.command == "publish-demo":
            if args.private_key.absolute() != (ROOT / ".build_keys" / "private_demo.pem").absolute():
                raise PolicyError("private key path outside isolated demo key directory")
            path = publish_demo(ROOT, args.private_key, args.output, serial=args.serial)
            result = {"result": "DEMO_PACKAGE_CREATED", "path": str(path), "production_approved": False}
        elif args.command == "verify-demo":
            if args.trust.absolute() != (ROOT / ".build_keys" / "public_demo.pem").absolute():
                raise PolicyError("trust anchor path outside isolated demo key directory")
            if args.pack.absolute() != (ROOT / "build" / "demo_rulepack.zip").absolute():
                raise PolicyError("rulepack path outside isolated demo build directory")
            result = verify_demo(args.pack, args.trust, min_serial=args.min_serial)
        elif args.command == "keygen-prevention-review":
            approved_dir = ROOT / ".build_keys" / "prevention"
            if args.out.absolute() != approved_dir.absolute():
                raise PolicyError("prevention key creation outside dedicated UCIE key directory")
            private, public = generate_keys(approved_dir, purpose="prevention")
            result = {"result": "REVIEW_ONLY_KEYS_CREATED",
                      "private_key_stays_local": True, "public_key": str(public),
                      "production_approved": False}
        elif args.command == "publish-prevention-review":
            allowed_key = ROOT / ".build_keys" / "prevention" / "private_prevention.pem"
            if args.private_key.absolute() != allowed_key.absolute():
                raise PolicyError("prevention signing key outside dedicated UCIE key directory")
            path = publish_prevention_review(
                ROOT, args.private_key, args.output,
                serial=args.serial, confirmation=args.confirm)
            result = {"result": "MANUAL_SIGNED_REVIEW_PACK_CREATED",
                      "path": str(path), "production_approved": False,
                      "deploy_allowed": False}
        elif args.command == "verify-prevention-review":
            result = verify_prevention_review(
                args.pack, args.trust, min_serial=args.min_serial)
        elif args.command == "keygen-production":
            directory = ROOT / ".build_keys" / "production"
            if args.out.absolute() != directory.absolute():
                raise PolicyError("production key path outside fixed UCIE key directory")
            private, public = generate_keys(directory, purpose="production")
            result = {"result": "OWNER_PRODUCTION_KEYS_CREATED",
                      "private_key_stays_local": True, "public_key": str(public),
                      "production_approved": False, "package_published": False}
        elif args.command == "publish-production":
            allowed_private = ROOT / ".build_keys" / "production" / "private_production.pem"
            if args.owner_private.absolute() != allowed_private.absolute():
                raise PolicyError("production signing key path not authorized")
            output = publish_production(
                ROOT, args.owner_private, args.qa_claim, args.qa_signature,
                args.qa_trust, args.output, serial=args.serial,
                confirmation=args.confirm)
            result = {"result": "DUAL_SIGNED_PUBLIC_PRODUCTION_PACKAGE_CREATED",
                      "path": str(output), "scope": "PUBLIC_ONLY_MANUAL_STATIC_SCAN",
                      "automated_deployment": False}
        elif args.command == "verify-production":
            result = verify_production(args.pack, args.owner_trust,
                                       args.qa_trust, min_serial=args.min_serial)
        elif args.command == "publish-owner-risk-release":
            allowed = ROOT / ".build_keys" / "production" / "private_production.pem"
            if args.owner_private.absolute() != allowed.absolute():
                raise PolicyError("owner risk release signer must use dedicated production key")
            output = publish_owner_risk_release(
                ROOT, args.owner_private, args.output,
                run_id=args.run_id, serial=args.serial,
                confirmation=args.confirm, risk_acceptance=args.accept_risk)
            result = {"result": "OWNER_RISK_ACCEPTED_PUBLIC_RELEASE_SIGNED",
                      "path": str(output),
                      "independent_human_qa_approved": False,
                      "scope": "PUBLIC_ONLY_MANUAL_STATIC_SCAN",
                      "automated_deployment": False}
        elif args.command == "verify-owner-risk-release":
            result = verify_owner_risk_release(
                args.pack, args.owner_trust, min_serial=args.min_serial)
        elif args.command == "publish-two-rule-review":
            allowed = ROOT / ".build_keys" / "prevention" / "private_prevention.pem"
            if args.private_key.absolute() != allowed.absolute():
                raise PolicyError("review signing key outside UCIE prevention key directory")
            out = publish_multi_review(
                ROOT, args.private_key, args.output, serial=args.serial,
                confirmation=args.confirm)
            result = {"result": "TWO_RULE_SIGNED_REVIEW_ONLY_CREATED",
                      "path": str(out), "production_approved": False,
                      "deploy_allowed": False}
        elif args.command == "verify-two-rule-review":
            result = verify_multi_review(
                args.pack, args.trust, min_serial=args.min_serial)
        elif args.command == "scan-two-rule-review-json-stdin":
            raw = sys.stdin.read(131073)
            if len(raw.encode("utf-8")) > 131072:
                raise PolicyError("oversized inert scanner receipt")
            scan = json.loads(raw, object_pairs_hook=_strict_pairs)
            result = scan_multi_review_receipt(
                args.pack, args.trust, scan, min_serial=args.min_serial)

        elif args.command == "publish-two-rule-owner-risk-release":
            allowed = ROOT / ".build_keys" / "production" / "private_production.pem"
            if args.owner_private.absolute() != allowed.absolute():
                raise PolicyError("owner production key outside dedicated UCIE key location")
            output = publish_two_rule_owner_release(
                ROOT, args.owner_private, args.output, run_id=args.run_id,
                serial=args.serial, confirmation=args.confirm,
                risk_acceptance=args.accept_risk,
                second_risk_acceptance=args.accept_second_risk)
            result = {"result": "EXPLICIT_TWO_RULE_OWNER_RISK_RELEASE_SIGNED",
                      "output": str(output), "scope": "PUBLIC_ONLY_MANUAL_STATIC_SCAN",
                      "automated_distribution": False, "auto_apply": False}
        elif args.command == "verify-two-rule-owner-risk-release":
            result = verify_two_rule_owner_release(
                args.pack, args.owner_trust, min_serial=args.min_serial)
        elif args.command == "scan-two-rule-owner-receipt-stdin":
            raw = sys.stdin.read(131073)
            if len(raw.encode("utf-8")) > 131072:
                raise PolicyError("oversized inert scan receipt")
            receipt = json.loads(raw, object_pairs_hook=_strict_pairs)
            result = scan_two_rule_owner_receipt(
                args.pack, args.owner_trust, receipt,
                min_serial=args.min_serial)
        elif args.command == "publish-selected-owner-risk-release":
            allowed = ROOT / ".build_keys" / "production" / "private_production.pem"
            if args.owner_private.absolute() != allowed.absolute():
                raise PolicyError("owner signing key must remain in UCIE key location")
            if len(args.rule_id) != len(args.accept_risk):
                raise PolicyError("each requested rule needs its own owner risk phrase")
            target = publish_selected_owner_release(
                ROOT, args.owner_private, args.output, run_id=args.run_id,
                serial=args.serial, rule_ids=args.rule_id,
                confirmation=args.confirm,
                risk_acceptances=dict(zip(args.rule_id, args.accept_risk, strict=True)))
            result = {
                "result": "SELECTED_OWNER_PUBLIC_RELEASE_SIGNED",
                "path": str(target), "rule_count": len(args.rule_id),
                "scope": "PUBLIC_ONLY_MANUAL_STATIC_SCAN",
                "auto_apply": False, "automated_distribution": False,
            }
        elif args.command == "verify-selected-owner-risk-release":
            result = verify_selected_owner_release(
                args.pack, args.owner_trust, min_serial=args.min_serial)
        elif args.command == "scan-selected-owner-receipt-stdin":
            raw = sys.stdin.read(131073)
            if len(raw.encode("utf-8")) > 131072:
                raise PolicyError("oversized public-only inert receipt")
            receipt = json.loads(raw, object_pairs_hook=_strict_pairs)
            result = scan_selected_owner_receipt(
                args.pack, args.owner_trust, receipt,
                min_serial=args.min_serial)
        elif args.command == "publish-mixed-owner-risk-release":
            allowed = ROOT / ".build_keys" / "production" / "private_production.pem"
            if args.owner_private.absolute() != allowed.absolute():
                raise PolicyError("mixed signing key must stay in dedicated UCIE directory")
            if len(args.rule_id) != len(args.accept_risk):
                raise PolicyError("each selected rule requires its own owner risk acceptance")
            target = publish_mixed_owner_release(
                ROOT, args.owner_private, args.output, run_id=args.run_id,
                serial=args.serial, rule_ids=args.rule_id,
                confirmation=args.confirm,
                risk_acceptances=dict(zip(args.rule_id, args.accept_risk, strict=True)))
            result = {
                "result": "MIXED_OWNER_PUBLIC_RULEPACK_SIGNED",
                "path": str(target), "rule_count": len(args.rule_id),
                "scope": "PUBLIC_ONLY_MANUAL_STATIC_SCAN",
                "auto_apply": False, "automated_distribution": False,
            }
        elif args.command == "verify-mixed-owner-risk-release":
            result = verify_mixed_owner_release(
                args.pack, args.owner_trust, min_serial=args.min_serial)
        elif args.command == "scan-mixed-owner-receipt-stdin":
            raw = sys.stdin.read(131073)
            if len(raw.encode("utf-8")) > 131072:
                raise PolicyError("oversized inert mixed-language receipt")
            receipt = json.loads(raw, object_pairs_hook=_strict_pairs)
            result = scan_mixed_owner_receipt(
                args.pack, args.owner_trust, receipt,
                min_serial=args.min_serial)
        elif args.command == "reconcile-signed-public-candidates":
            result = reconcile_mixed_signed_candidates(
                ROOT, args.pack, args.owner_trust,
                min_serial=args.min_serial)
        else:
            raise AssertionError("unreachable")
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (PolicyError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"result": "FAIL_CLOSED", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
