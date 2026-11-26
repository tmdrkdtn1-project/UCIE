"""Exact-HEAD guarded UCIE Actions selection. No customer input or release."""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess

PATTERN = re.compile(r"[0-9a-f]{40}\Z")
MATRIX = [{"os": os_, "py": py} for os_ in ("ubuntu-latest", "windows-latest") for py in ("3.13", "3.15")]
SPECIAL = {
    "BROWSER": ("ucie_v2_beginner_preview", "ucie_v2_first_use_linked", "test_ucie_v2_g3_", "ucie-v2-g3-", "ucie-v2-g4-"),
    "POWERSHELL": ("ucie_v2_b4_powershell", "ucie_v2_b4_powershell_native", "ucie-v2-b4-heldout"),
    "MCP": ("mcp_", "ucie_mcp_", "ucie-mcp-"),
}
def classify(paths, mode):
    if mode not in ("PR_ITERATION", "MERGE_CANDIDATE") or type(mode) is not str:
        raise ValueError("invalid mode")
    if type(paths) not in (list, tuple) or not 1 <= len(paths) <= 200:
        raise ValueError("invalid changed paths")
    if any(type(p) is not str or not 1 <= len(p) <= 240 or p.startswith(("/", "~", "-"))
           or "\\" in p or ":" in p or "\x00" in p
           or any(part in ("", ".", "..") for part in p.split("/")) for p in paths):
        raise ValueError("untrusted path")
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate changed path")
    names = sorted(paths)
    native = sorted(k for k, patterns in SPECIAL.items()
                    if any(any(s in p for s in patterns) for p in names))
    approved = ("docs/", "tests/", "scripts/", "src/ucie_miner/", ".github/workflows/")
    unknown = any(not p.startswith(approved) and p not in ("AGENTS.md", "requirements.txt", "pyproject.toml") for p in names)
    high = unknown or bool(native) or any(p.startswith(("src/", "scripts/", ".github/")) or
        p in ("AGENTS.md", "requirements.txt", "pyproject.toml") or
        any(s in p for s in ("core.py", "worker.py", "source_registry", "runtime_", "public_miner_cycle", "customer_")) for p in names)
    full = mode == "MERGE_CANDIDATE" or high
    return {"schema": "UCIE_ACTIONS_EXACT_HEAD_GATE_V01", "changed_paths": names,
            "mode": mode, "risk_high": bool(high), "unknown": bool(unknown),
            "tier": "FOUR_PLATFORM" if full else "FAST_NOT_MERGE",
            "matrix": MATRIX if full else [{"os": "ubuntu-latest", "py": "3.15"}],
            "native_required": native, "merge_accepted": False,
            "owner_host_accepted": False, "release_authorized": False}

def run(base, head, mode, repo="."):
    if any(type(s) is not str or not PATTERN.fullmatch(s) for s in (base, head)) or base == head:
        raise ValueError("invalid commit SHA")
    def git(*args):
        return subprocess.check_output(["git", "-C", repo, *args], stderr=subprocess.DEVNULL, timeout=20)
    if git("rev-parse", "HEAD").decode().strip() != head:
        raise ValueError("checked-out HEAD mismatch")
    git("merge-base", "--is-ancestor", base, head)
    raw = git("diff", "--name-only", "-z", base, head)
    if not raw or not raw.endswith(b"\0"):
        raise ValueError("no valid changes")
    paths = [p.decode("utf-8", "strict") for p in raw[:-1].split(b"\0")]
    result = classify(paths, mode)
    result["base_sha"] = base
    result["head_sha"] = head
    return result

if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--base", required=True)
    a.add_argument("--head", required=True)
    a.add_argument("--mode", choices=("PR_ITERATION", "MERGE_CANDIDATE"), required=True)
    args = a.parse_args()
    r = run(args.base, args.head, args.mode)
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("matrix=" + json.dumps({"include": r["matrix"]}, separators=(",", ":")) + "\n")
            f.write("tier=" + r["tier"] + "\n")
            f.write("native_required=" + str(bool(r["native_required"])).lower() + "\n")
    print(json.dumps(r, ensure_ascii=False, sort_keys=True))
