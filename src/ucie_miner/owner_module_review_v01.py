"""UCIE-only owner-local review cards; never run or publish original code.

Invoked from the exact clean staged Windows checkout. Outputs only numeric
counts to stdout. With explicit --write-private-report, stores names and
static API/test leads ONLY on the owner's machine, outside both Git trees.
Nothing is migrated, executed from original, removed, or auto-approved.
"""
from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re

SCHEMA = "UCIE_OWNER_LOCAL_CONTRACT_REVIEW_V01"
PRIVATE_SCHEMA = "UCIE_OWNER_PRIVATE_MODULE_CONTRACT_PACKET_V01"
LOCAL_PACKET_DIR = "UCIE_OWNER_REVIEW"
MAX_TOTAL_SOURCE_BYTES = 128_000_000
MAX_PRIVATE_PACKET_BYTES = 2_000_000
MAX_API_ITEMS = 120


def _load_trusted_audit():
    """Only the sibling first-party staged source is loaded, NEVER original."""
    path = Path(__file__).resolve().with_name("layout_audit_v01.py")
    spec = importlib.util.spec_from_file_location(
        "_ucie_staged_layout_audit_trusted", path)
    if spec is None or spec.loader is None:
        raise ValueError("trusted UCIE staged audit unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _module_from_src_path(layout, path: str) -> str | None:
    if layout._ucie_code_scope(path) != "src" or not path.endswith(".py"):
        return None
    stem = path[4:-3].replace("/", ".")
    if stem.endswith(".__init__"):
        stem = stem[:-len(".__init__")]
    if stem not in ("ucie_miner", "ucie_public") and not stem.startswith(
            ("ucie_miner.", "ucie_public.")):
        return None
    return stem


def _api_declarations(data: bytes | None, layout) -> dict:
    """Public AST declarations and argument shapes, not behavior/exports."""
    if data is None or len(data) > layout.MAX_LOCAL_AST_BYTES:
        return {"parse_status": "UNAVAILABLE_HOLD", "symbols": [],
                "total": None, "truncated": False}
    try:
        tree = ast.parse(data.decode("utf-8-sig"), filename="<UCIE-owner>")
    except (SyntaxError, UnicodeError, ValueError, RecursionError, MemoryError):
        return {"parse_status": "UNAVAILABLE_HOLD", "symbols": [],
                "total": None, "truncated": False}
    items = []

    def add(node, symbol_name: str, kind: str):
        if (symbol_name.startswith("_") or len(symbol_name) > 140
                or not all(c.isalnum() or c in "._" for c in symbol_name)):
            return
        row = {"name": symbol_name, "kind": kind}
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            row.update({
                "positional": len(args.posonlyargs) + len(args.args),
                "required_positional": (
                    len(args.posonlyargs) + len(args.args) - len(args.defaults)),
                "keyword_only": len(args.kwonlyargs),
                "varargs": bool(args.vararg),
                "kwargs": bool(args.kwarg),
            })
        items.append(row)

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            add(node, node.name, "class")
            for method in node.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add(method, node.name + "." + method.name, "method")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add(node, node.name,
                "async_function" if isinstance(node, ast.AsyncFunctionDef)
                else "function")
    return {
        "parse_status": "STATIC_DECLARATIONS_ONLY",
        "symbols": items[:MAX_API_ITEMS],
        "total": len(items),
        "truncated": len(items) > MAX_API_ITEMS,
    }


def _owner_import_leads(data: bytes, name: str, owner_modules: set[str],
                        layout) -> tuple[set[str], set[str]]:
    """Exact explicit import vs ambiguous root attribute/module names."""
    if not name.endswith(".py") or len(data) > layout.MAX_LOCAL_AST_BYTES:
        return set(), set()
    try:
        tree = ast.parse(data.decode("utf-8-sig"), filename="<UCIE-owner>")
    except (SyntaxError, UnicodeError, ValueError, RecursionError, MemoryError):
        return set(), set()
    direct, root_symbols = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.casefold() in owner_modules:
                    direct.add(alias.name.casefold())
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            mod = (node.module or "").casefold()
            if mod in owner_modules:
                direct.add(mod)
            elif mod in ("ucie_miner", "ucie_public"):
                for alias in node.names:
                    candidate = mod + "." + alias.name.casefold()
                    if alias.name != "*" and candidate in owner_modules:
                        root_symbols.add(candidate)
    return direct, root_symbols


def _build_owner_packet(
    stage: Path, original: Path, staged_paths: set[str],
    changes: list[tuple[str, str]], layout
) -> tuple[dict, dict]:
    """Return private cards + public numeric summary, completely offline."""
    if len(staged_paths) + len(changes) > layout.MAX_LOCAL_CODE_RECORDS:
        raise ValueError("UCIE local source census exceeds safe bound")
    stage_modules = layout._stage_tracked_ucie_python_modules(staged_paths)
    owner_paths = {}
    for _, name in changes:
        if name in staged_paths:
            continue
        module = _module_from_src_path(layout, name)
        if module is None or module in stage_modules:
            continue
        if module in owner_paths:
            raise ValueError("UCIE duplicate original module mapping")
        owner_paths[module] = name
    owner_modules = set(owner_paths)
    if len(owner_modules) > 100:
        raise ValueError("UCIE original module inventory exceeds safe bound")

    # Same broad stage code index as the earlier local review; do not
    # silently count EOL-equivalent or AST-equal files as new candidates.
    stage_data = {}
    exact, eol, syntax = set(), set(), set()
    budget = 0
    for name in sorted(staged_paths):
        if layout._ucie_code_scope(name) is None:
            continue
        data = layout._read_owner_ucie_code_bounded(stage, name)
        if data is None:
            continue
        budget += len(data)
        if budget > MAX_TOTAL_SOURCE_BYTES:
            raise ValueError("UCIE staged source size limit")
        stage_data[name] = data
        exact.add(sha256(data).digest())
        eol.add(sha256(data.replace(b"\r\n", b"\n")).digest())
        digest = layout._code_ast_digest(data, name)
        if digest is not None:
            syntax.add(digest)

    stage_api = {}
    for path, data in stage_data.items():
        if layout._ucie_code_scope(path) != "src" or not path.endswith(".py"):
            continue
        for item in _api_declarations(data, layout)["symbols"]:
            stage_api.setdefault(json.dumps(item, sort_keys=True), set()).add(path)

    source_data = {}
    original_refs: dict[str, dict[str, set[str]]] = {
        name: {"direct": set(), "root_symbol": set()} for name in owner_modules
    }
    original_only_no_match = 0
    for _, name in changes:
        if name in staged_paths or layout._ucie_code_scope(name) is None:
            continue
        data = layout._read_owner_ucie_code_bounded(original, name)
        if data is None:
            continue
        budget += len(data)
        if budget > MAX_TOTAL_SOURCE_BYTES:
            raise ValueError("UCIE original source size limit")
        module = _module_from_src_path(layout, name)
        if module in owner_modules:
            source_data[module] = data
        if (sha256(data).digest() in exact
                or sha256(data.replace(b"\r\n", b"\n")).digest() in eol):
            continue
        digest = layout._code_ast_digest(data, name)
        if digest is not None and digest in syntax:
            continue
        original_only_no_match += 1
        direct, roots = _owner_import_leads(data, name, owner_modules, layout)
        for target in direct:
            original_refs[target]["direct"].add(name)
        for target in roots:
            original_refs[target]["root_symbol"].add(name)

    stage_test_refs: dict[str, set[str]] = {
        name: set() for name in owner_modules
    }
    for name, data in stage_data.items():
        if not name.startswith("tests/") or not name.endswith(".py"):
            continue
        direct, _ = _owner_import_leads(data, name, owner_modules, layout)
        for target in direct:
            stage_test_refs[target].add(name)

    direct_modules = {name for name, ref in original_refs.items()
                      if ref["direct"]}
    root_modules = {name for name, ref in original_refs.items()
                    if ref["root_symbol"]}
    total_api = matched_api = parse_blocked = 0
    cards = []
    for module in sorted(owner_modules, key=lambda m: (
            0 if m in direct_modules else 1 if m in root_modules else 2, m)):
        priority = ("P1_DIRECT_SOURCE_CONTRACT_REVIEW" if module in direct_modules
                    else "P2_ROOT_SYMBOL_AMBIGUITY_HOLD"
                    if module in root_modules else "P3_UNOBSERVED_HOLD")
        api = (_api_declarations(source_data.get(module), layout)
               if module in direct_modules else None)
        suggestions = []
        if api is not None:
            if api["parse_status"] != "STATIC_DECLARATIONS_ONLY":
                parse_blocked += 1
            for symbol in api["symbols"]:
                candidates = sorted(stage_api.get(
                    json.dumps(symbol, sort_keys=True), ()))
                suggestions.append({
                    "original_static_declaration": symbol,
                    "stage_same_name_and_parameter_shape_paths": candidates[:3],
                    "additional_stage_candidates_count": max(0, len(candidates)-3),
                    "behavior_equivalence_verified": False,
                })
                matched_api += bool(candidates)
            total_api += len(api["symbols"])
        refs = original_refs[module]
        cards.append({
            "original_module_name": module,
            "original_relative_src_path": owner_paths[module],
            "priority": priority,
            "original_test_paths_with_direct_import": sorted(
                p for p in refs["direct"] if p.startswith("tests/")),
            "original_script_paths_with_direct_import": sorted(
                p for p in refs["direct"] if p.startswith("scripts/")),
            "original_src_paths_with_direct_import": sorted(
                p for p in refs["direct"] if p.startswith("src/")),
            "original_ambiguous_root_symbol_path_candidates": sorted(
                refs["root_symbol"]),
            "staged_test_paths_with_direct_import": sorted(
                stage_test_refs[module]),
            "public_api": suggestions,
            "public_api_total": api["total"] if api is not None else None,
            "public_api_truncated": api["truncated"] if api is not None else None,
            "parse_status": (api["parse_status"] if api is not None
                             else "NOT_REVIEWED_PRIORITY_HOLD"),
            "functional_equivalence_verified": False,
            "original_tests_executed": False,
            "current_action": "K0_HOLD",
        })
    packet = {
        "schema": PRIVATE_SCHEMA,
        "contains_owner_module_test_and_api_names": True,
        "do_not_upload_or_paste": True,
        "contains_original_code_bodies": False,
        "status": "PRIVATE_LOCAL_REVIEW_ONLY__NO_MIGRATION",
        "module_cards": cards,
    }
    summary = {
        "schema": SCHEMA,
        "status": "OWNER_LOCAL_CONTRACT_CANDIDATES__FUNCTIONAL_PARITY_UNVERIFIED",
        "owner_only_module_paths": len(owner_modules),
        "direct_import_referenced_unique_modules": len(direct_modules),
        "root_symbol_unique_modules": len(root_modules),
        "both_reference_styles": len(direct_modules & root_modules),
        "distinct_referenced_union": len(direct_modules | root_modules),
        "other_modules_held": len(owner_modules - direct_modules - root_modules),
        "direct_module_public_api_items_observed": total_api,
        "direct_public_api_items_with_stage_name_shape_candidate": matched_api,
        "direct_public_api_items_without_stage_name_shape_candidate":
            total_api - matched_api,
        "direct_modules_ast_unavailable": parse_blocked,
        "original_test_files_with_direct_owner_module_ref": len({
            path for m in direct_modules for path in original_refs[m]["direct"]
            if path.startswith("tests/")}),
        "staged_test_files_with_direct_owner_module_ref": len({
            path for m in direct_modules for path in stage_test_refs[m]}),
        "original_only_code_files_without_stage_content_match": original_only_no_match,
        "original_names_paths_api_details_returned": False,
        "original_code_imported_or_executed": False,
        "staged_symbols_prove_functional_equivalence": False,
        "original_files_moved_or_deleted": False,
        "cleanup_or_cutover_authorized": False,
        "all_original_modules": "K0_HOLD",
    }
    return packet, summary


def _write_private_file_exclusive(output: Path, packet: dict) -> None:
    if (not output.parent.is_dir() or output.parent.is_symlink()
            or output.is_symlink() or output.exists()):
        raise ValueError("UCIE private review output path unsafe or exists")
    payload = json.dumps(packet, sort_keys=True, ensure_ascii=True, indent=2)
    if len(payload.encode("utf-8")) > MAX_PRIVATE_PACKET_BYTES:
        raise ValueError("UCIE private packet too large")
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(payload + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_on_owner_host(root: Path, sha: str, packet: dict, layout) -> str:
    if (os.name != "nt" or str(root).casefold() != layout.TARGET_CODE.casefold()
            or not re.fullmatch(r"[0-9a-f]{40}", sha)
            or packet.get("schema") != PRIVATE_SCHEMA):
        raise ValueError("UCIE owner review host identity mismatch")
    parent = Path(layout.TARGET_PARENT)
    if not parent.is_dir() or layout._indirect(parent):
        raise ValueError("UCIE review parent unavailable")
    folder = parent / LOCAL_PACKET_DIR
    if not folder.exists():
        folder.mkdir(mode=0o700)
    if not folder.is_dir() or layout._indirect(folder):
        raise ValueError("UCIE private report folder unsafe")
    filename = "UCIE_OWNER_MODULE_REVIEW_" + sha[:12] + ".json"
    _write_private_file_exclusive(folder / filename, packet)
    return filename


def run_owner_review(*, write_private_report: bool = False) -> dict:
    """Exact Windows staged-root only; no original import, no network."""
    # Reject foreign/unsupported roots BEFORE importing any sibling source.
    stage = Path(__file__).resolve().parents[2]
    original = Path(r"D:\UCIE")
    if (os.name != "nt" or str(stage).casefold() != r"d:\ucie_project\ucie"):
        raise ValueError("UCIE owner reviewer requires exact Windows stage")
    layout = _load_trusted_audit()
    preflight = layout.compare_original_ucie_git_to_stage(
        stage, original, platform=os.name, review_local_code=True)
    if preflight["owner_local_code_content_review"]["status"] != (
            "OWNER_LOCAL_CODE_CONTENT_REVIEW_ONLY__FUNCTIONAL_EQUIVALENCE_UNVERIFIED"):
        raise ValueError("UCIE prior owner-local review did not pass")
    before_stage = layout._git_metadata_bytes(
        stage, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    before_orig = layout._git_metadata_bytes(
        original, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    stage_paths = layout._parse_tracked_git_paths(
        layout._git_metadata_bytes(stage, "ls-files", "-z"))
    changes = layout._parse_original_status_paths(before_orig)
    packet, summary = _build_owner_packet(
        stage, original, stage_paths, changes, layout)
    coverage = preflight["owner_local_code_content_review"][
        "original_only_no_static_match_import_review"][
        "distinct_owner_module_coverage"]
    expected = (
        ("owner_only_module_paths", "original_only_src_module_path_candidates"),
        ("direct_import_referenced_unique_modules",
         "distinct_modules_named_by_explicit_imports"),
        ("root_symbol_unique_modules",
         "distinct_modules_named_by_root_symbol_candidates"),
        ("both_reference_styles", "distinct_modules_named_by_both"),
        ("distinct_referenced_union", "distinct_modules_named_by_either_style"),
        ("other_modules_held",
         "original_only_modules_without_observed_explicit_or_root_symbol_lead"),
    )
    if (any(summary[a] != coverage[b] for a, b in expected)
            or summary["original_only_code_files_without_stage_content_match"]
            != preflight["owner_local_code_content_review"][
                "original_only_no_static_match_import_review"][
                "code_paths_without_content_match_reviewed"]):
        raise ValueError("UCIE local module review disagrees with pinned audit")
    after_orig = layout._git_metadata_bytes(
        original, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    after_stage = layout._git_metadata_bytes(
        stage, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if (after_orig != before_orig or after_stage != before_stage
            or (after_stage and not layout._verified_crlf_only_staged_worktree(
                stage, after_stage))):
        raise ValueError("UCIE source status changed during review")
    sha = layout._git_metadata_bytes(stage, "rev-parse", "HEAD").decode(
        "ascii").strip().casefold()
    summary["private_report_written_on_owner_pc"] = False
    if write_private_report:
        filename = _write_on_owner_host(stage, sha, packet, layout)
        summary["private_report_written_on_owner_pc"] = True
        summary["private_report_filename_no_owner_source_names"] = filename
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=(
        "UCIE owner-local module/test/API candidate review; never execute source"))
    parser.add_argument("--write-private-report", action="store_true",
                        help="Opt in to non-overwriting local owner-only JSON packet")
    args = parser.parse_args()
    try:
        report = run_owner_review(write_private_report=args.write_private_report)
        print(json.dumps(report, sort_keys=True))
        return 0
    except (ValueError, OSError, UnicodeError, RuntimeError) as exc:
        # Errors are fixed and scrubbed; owner source/path/AST is never printed.
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_OWNER_MODULE_REVIEW_FAIL_CLOSED",
            "failure_type": "OWNER_LOCAL_REVIEW_BLOCKED",
            "owner_names_or_contents_returned": False,
            "original_code_executed": False,
            "cutover_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
