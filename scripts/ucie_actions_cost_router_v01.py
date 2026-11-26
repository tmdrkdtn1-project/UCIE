"""UCIE-only source-agnostic GitHub Actions cost router. Never executes or attests tests."""
from __future__ import annotations
import json

SCHEMA = "UCIE_ACTIONS_COST_ROUTER_V01"
MODES = ("PR_ITERATION", "MERGE_CANDIDATE", "MANUAL_SPECIALIZED")
SPECIAL = {
    "BROWSER": ("ucie_v2_beginner_preview", "ucie_v2_first_use_linked", "ucie-v2-g3-", "ucie-v2-g4-", "test_ucie_v2_g3_"),
    "POWERSHELL": ("ucie_v2_b4_powershell", "ucie_v2_b4_powershell_native_", "ucie-v2-b4-heldout-"),
    "MCP": ("mcp_", "ucie_mcp_", "ucie-mcp-"),
}
HIGH_RISK = ("core.py", "worker.py", "source_registry", "public_miner_cycle", "shared_core_quota",
             "local_v1_app_v01", "ucie_v2_capsule", "ucie_v2_revision_impact",
             "customer_", "runtime_", "requirements.txt", "pyproject.toml", "AGENTS.md")


def classify(paths: object, mode: str = "PR_ITERATION") -> dict:
    if type(mode) is not str or mode not in MODES:
        raise ValueError("unknown Actions execution mode")
    if type(paths) not in (tuple, list) or not 1 <= len(paths) <= 200:
        raise ValueError("invalid change list")
    if any(type(p) is not str or not 1 <= len(p) <= 240
           or p.startswith(("/", "~")) or "\\" in p or ":" in p
           or any(part in ("", ".", "..") for part in p.split("/"))
           for p in paths) or len(set(paths)) != len(paths):
        raise ValueError("unsafe or duplicate changed path")
    names = tuple(sorted(paths))
    allowed_prefixes = ("docs/", "tests/", "scripts/", "src/ucie_miner/", ".github/workflows/")
    allowed_files = ("AGENTS.md", "requirements.txt", "pyproject.toml")
    suites = sorted(label for label, keys in SPECIAL.items()
                    if any(any(k in p for k in keys) for p in names))
    unknown = any(not p.startswith(allowed_prefixes) and p not in allowed_files for p in names)
    risky = (unknown or bool(suites) or
             any(p.startswith(".github/workflows/") or
                 any(key in p for key in HIGH_RISK) for p in names))
    four = ("WINDOWS_PY313", "WINDOWS_PY315", "UBUNTU_PY313", "UBUNTU_PY315")
    if mode == "MANUAL_SPECIALIZED":
        if not suites:
            raise ValueError("no authorized specialized suite matches")
        tier = "REVIEW_SPECIALIZED_ONLY"
        checks = tuple("NATIVE_" + s for s in suites)
    elif mode == "MERGE_CANDIDATE" or risky:
        tier = "FOUR_PLATFORM_FULL_REQUIRED"
        checks = four + tuple("NATIVE_" + s for s in suites)
    else:
        tier = "FAST_ONLY_NOT_A_MERGE_PASS"
        checks = ("FAST_PY315",)
    return {
        "schema": SCHEMA, "mode": mode, "tier": tier,
        "changed_paths": list(names), "specialized_suites": suites,
        "high_risk_or_unknown": risky, "checks_required": list(checks),
        "final_merge_gate": "EXACT_HEAD_FOUR_PLATFORM_AND_RELEVANT_NATIVE",
        "source_or_customer_code_executed": False, "github_checks_run": False,
        "native_browser_or_owner_qa_pass": False, "auto_promoted": False,
        "owner_activation_approved": False, "release_authorized": False,
        "required_check_skipped_as_pass": False, "operating_database_written": False,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=MODES, default="PR_ITERATION")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    print(json.dumps(classify(args.paths, args.mode), sort_keys=True))
