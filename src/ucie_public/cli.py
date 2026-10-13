"""Manual-only CLI. No scheduled jobs, external network, project connectors or installation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .policy import PolicyError
from .rulepack import generate_keys, publish_demo, verify_demo

ROOT = Path(__file__).resolve().parents[2]


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
        else:
            raise AssertionError("unreachable")
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (PolicyError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"result": "FAIL_CLOSED", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
