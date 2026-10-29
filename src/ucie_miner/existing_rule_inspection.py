"""Single manual UCIE code inspection consumer using EXISTING detectors/packs.

Only caller-supplied Python UTF-8 source via bounded stdin or in-memory
synthetic fixtures. Never executes/analyzes external project files, downloads
source, writes DB, installs hooks, deploys fixes, or promotes P11/P13 leads.

Unsigned detectors are REVIEW-ONLY. Previously owner-signed manual Rulepacks
are recognized only AFTER the original signature/expiry/trust/scope checks
on exact UCIE-local paths. Independent QA and auto-apply stay false.
"""
from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import sys

from .static_concurrency import inspect_python_scandir_source
from .static_asyncio_resource import inspect_asyncio_protocol_factory_source
from .static_mcp_empty_meta import inspect_mcp_empty_meta_source
from .p13_decimal_unbounded_guard import inspect_source as inspect_decimal_source

SCHEMA = "UCIE_EXISTING_RULES_MANUAL_CODE_INSPECTION_V1"
MAX_BYTES = 16384
MAX_CASES = 20
MAX_CASE_BYTES = 65536
MAX_FINDINGS = 100
DEFAULT_GATES = {
    "source_fix_proven": False,
    "independent_qa_completed": False,
    "auto_applied": False,
    "auto_promoted": False,
}
ALLOWED_RULES = frozenset({
    "PY_SCANDIR_SHARED_ITERATOR_RACE",
    "PY_ASYNCIO_PROTOCOL_FACTORY_PRETRANSPORT_LEAK",
    "MCP_JSONRPC_UNCONDITIONAL_EMPTY_META",
    "PY_DECIMAL_UNBOUNDED_PURE_PYTHON_REVIEW",
})


class InspectionError(ValueError):
    pass


def _validate_source(source: str) -> bytes:
    if type(source) is not str:
        raise InspectionError("exact Python source text required")
    try:
        raw = source.encode("utf-8")
    except UnicodeError as exc:
        raise InspectionError("invalid UTF-8 source") from exc
    if not 0 < len(raw) <= MAX_BYTES:
        raise InspectionError("empty/oversized input")
    return raw


def inspect_existing_python(source: str, *, root: Path | None = None,
                            serial4_pack: Path | None = None,
                            owner_public_trust: Path | None = None,
                            serial5_pack: Path | None = None) -> dict:
    """Use existing four source scanners; verify original pack before match."""
    raw = _validate_source(source)
    if root is not None and (
            not isinstance(root, Path) or root.name.casefold() != "ucie"
            or root.is_symlink() or not root.is_dir()):
        raise InspectionError("UCIE-only source inspection root required")
    if (serial4_pack is None) != (owner_public_trust is None):
        raise InspectionError("signed pack and PUBLIC owner trust must be paired")
    if serial5_pack is not None and serial4_pack is None:
        raise InspectionError("fifth rule needs existing fourth rule pack")
    if serial4_pack is not None:
        if (not isinstance(root, Path) or not isinstance(serial4_pack, Path)
                or not isinstance(owner_public_trust, Path)
                or (serial5_pack is not None and not isinstance(serial5_pack, Path))):
            raise InspectionError("explicit UCIE-only Path values required")
        # Verify before scanning any untrusted source and before declaring any
        # matcher output authorized. Original verifiers are intentionally used.
        from .signed_rule_library import inspect_signed_library, SignedLibraryError
        try:
            approved = inspect_signed_library(
                root, serial4_pack=serial4_pack,
                owner_public_trust=owner_public_trust,
                serial5_pack=serial5_pack,
            )
        except (SignedLibraryError, OSError, ValueError) as exc:
            raise InspectionError("existing manual signed pack unverified") from exc
        allowed = {x["rule_id"] for x in approved["items"]}
    else:
        allowed = set()

    expected_digest = sha256(raw).hexdigest()
    # Each existing detector requires a literal identifier in the AST.
    # Fast-reject absent names, but parse once to preserve syntax/size checks.
    # Do NOT skip the original scandir receipt for signed pack matching.
    if "scandir" in source or serial4_pack is not None:
        scandir = inspect_python_scandir_source(source)
    else:
        try:
            tree = ast.parse(source, filename="<ucie-integrated>", mode="exec")
            if sum(1 for _ in ast.walk(tree)) > 10000:
                raise InspectionError("AST complexity limit exceeded")
        except (SyntaxError, RecursionError, ValueError, MemoryError) as exc:
            raise InspectionError("invalid or excessively nested Python source") from exc
        scandir = {"source_sha256": expected_digest, "findings": []}

    # The exact required identifiers are checked before deciding whether a
    # specialized AST detector can possibly emit a candidate. A token inside
    # a string/comment may trigger extra work, never suppress a real finding.
    scans = (
        scandir,
        (inspect_asyncio_protocol_factory_source(source)
         if "protocol_factory" in source
         else {"source_sha256": expected_digest, "candidates": []}),
        (inspect_mcp_empty_meta_source(source)
         if "send_raw_request" in source
         else {"source_sha256": expected_digest, "candidates": []}),
        (inspect_decimal_source(source)
         if "_pydecimal" in source
         else {"source_sha256": expected_digest, "findings": []}),
    )
    if any(record["source_sha256"] != expected_digest for record in scans):
        raise InspectionError("inconsistent first-party scanner source digest")

    signed = []
    if allowed:
        # This call itself re-verifies the original signed owner pack and uses
        # the existing bounded signed static rule matcher.
        from ucie_public.mixed_release import scan_mixed_owner_receipt
        from ucie_public.policy import PolicyError
        try:
            matched = scan_mixed_owner_receipt(
                serial4_pack, owner_public_trust, scans[0])
            if (matched["owner_signature"] != "VALID"
                    or matched["pack_serial"] != 4
                    or matched["source_sha256"] != expected_digest
                    or matched["auto_apply"] is not False):
                raise InspectionError("untrusted owner-signed scan receipt")
            for finding in matched["findings"]:
                if finding["rule_id"] not in allowed:
                    raise InspectionError("outside signed rule pack")
                signed.append({
                    "rule_id": finding["rule_id"], "line": finding["line"],
                    "column": finding["column"],
                    "public_evidence": finding["public_evidence"],
                    "guidance": finding["guidance"],
                    "authorization": "EXISTING_OWNER_SIGNED_MANUAL_ONLY",
                    "manual_review_required": True,
                    "runtime_bug_confirmed_for_input": False,
                })
            if serial5_pack is not None:
                from ucie_public.fifth_owner_addendum import scan_fifth_addendum
                fifth = scan_fifth_addendum(
                    serial5_pack, serial4_pack, owner_public_trust, source)
                if (fifth["owner_signature"] != "VALID"
                        or fifth["rule_id"] not in allowed
                        or fifth["source_sha256"] != expected_digest):
                    raise InspectionError("untrusted fifth signed rule receipt")
                for finding in fifth["findings"]:
                    signed.append({
                        "rule_id": fifth["rule_id"],
                        "line": finding["line"], "column": finding["column"],
                        "public_evidence": finding["public_evidence"],
                        "guidance": finding["suggested_review"],
                        "authorization": "EXISTING_OWNER_SIGNED_MANUAL_ONLY",
                        "manual_review_required": True,
                        "runtime_bug_confirmed_for_input": False,
                    })
        except (PolicyError, OSError, ValueError) as exc:
            raise InspectionError("original signed-rule scanner verification failed") from exc
    signed_keys = {(x["rule_id"], x["line"], x["column"]) for x in signed}
    candidates = []
    for finding in scans[0]["findings"]:
        candidates.append({
            "rule_id": finding["pattern_code"],
            "line": finding["line"], "column": finding["column"],
            "guidance": finding["safe_fix_guidance"],
            "public_evidence": finding["public_evidence"],
        })
    for finding in scans[1]["candidates"]:
        candidates.append({
            "rule_id": finding["rule_id"], "line": finding["line"],
            "column": finding["column"],
            "guidance": finding["suggested_review"],
            "public_evidence": finding["public_evidence"],
        })
    for finding in scans[2]["candidates"]:
        candidates.append({
            "rule_id": finding["rule_id"], "line": finding["line"],
            "column": finding["column"],
            "guidance": finding["safe_guidance"],
            "public_evidence": finding["public_evidence"],
        })
    for finding in scans[3]["findings"]:
        candidates.append({
            "rule_id": "PY_DECIMAL_UNBOUNDED_PURE_PYTHON_REVIEW",
            "line": finding["line"], "column": 0,
            "guidance": (
                "Review _pydecimal MAX_PREC modulo/divmod/floordiv: "
                "an isolated Python 3.15.0 Windows timeout was observed; "
                "use bounded tests and explicit Decimal context."
            ),
            "public_evidence": "https://github.com/python/cpython/pull/160482",
        })
    if len(candidates) > MAX_FINDINGS:
        raise InspectionError("combined findings exceed bound")
    normalized = []
    for item in candidates:
        key = (item["rule_id"], item["line"], item["column"])
        normalized.append({
            **item,
            "authorization": ("EXISTING_OWNER_SIGNED_MANUAL_ONLY" if key in signed_keys
                              else "UNVERIFIED_STATIC_CANDIDATE_ONLY"),
            "manual_review_required": True,
            "runtime_bug_confirmed_for_input": False,
            "source_fix_proven": False,
        })
    normalized.sort(key=lambda x: (x["line"], x["column"], x["rule_id"]))
    if sum(x["authorization"] == "EXISTING_OWNER_SIGNED_MANUAL_ONLY"
           for x in normalized) != len(signed):
        raise InspectionError("signed matcher and normalized findings disagree")
    return {
        "schema": SCHEMA,
        "status": ("MANUAL_CODE_REVIEW_CANDIDATES" if normalized
                   else "NO_PATTERN_FOUND_NOT_A_SAFETY_PASS"),
        "source_sha256": expected_digest,
        "findings": normalized,
        "finding_count": len(normalized),
        "existing_signed_manual_matches": len(signed),
        "unverified_candidate_count": len(normalized) - len(signed),
        "source_executed": False,
        "source_files_read": 0, "network_requests": 0, "database_writes": 0,
        "new_approved_rules": 0,
        **DEFAULT_GATES,
    }


def evaluate_labeled_feedback(cases: object) -> dict:
    """Synthetic labels measure detector errors; NEVER auto-teach/approve rules."""
    if type(cases) is not list or not 2 <= len(cases) <= MAX_CASES:
        raise InspectionError("bounded labeled synthetic cases required")
    used = set()
    volume = 0
    per_case = []
    for case in cases:
        if type(case) is not dict or set(case) != {"case_id", "source", "expected_rule_ids"}:
            raise InspectionError("strict synthetic feedback case shape required")
        case_id = case["case_id"]
        expected = case["expected_rule_ids"]
        if (type(case_id) is not str or not 1 <= len(case_id) <= 48
                or not all(c.isascii() and (c.isalnum() or c in "_-")
                           for c in case_id)
                or case_id in used
                or type(expected) is not list
                or any(type(e) is not str or e not in ALLOWED_RULES
                       for e in expected)
                or len(expected) != len(set(expected))):
            raise InspectionError("unknown/duplicated feedback label")
        used.add(case_id)
        try:
            source_bytes = _validate_source(case["source"])
        except InspectionError as exc:
            raise InspectionError("FEEDBACK_CASE_SOURCE_INVALID") from exc
        volume += len(source_bytes)
        if volume > MAX_CASE_BYTES:
            raise InspectionError("cumulative feedback size exceeded")
        try:
            observed_result = inspect_existing_python(case["source"])
        except (ValueError, SyntaxError, RecursionError, MemoryError) as exc:
            raise InspectionError("FEEDBACK_CASE_SOURCE_PARSE_REJECTED") from exc
        observed = {row["rule_id"] for row in observed_result["findings"]}
        positives = set(expected)
        per_case.append({
            "case_id": case_id,
            "source_sha256": observed_result["source_sha256"],
            "expected_rule_ids": sorted(positives),
            "observed_rule_ids": sorted(observed),
            "false_positive_rule_ids": sorted(observed - positives),
            "false_negative_rule_ids": sorted(positives - observed),
            "label_origin": "UCIE_SYNTHETIC_HUMAN_LABEL_ONLY",
        })
    if not any(item["expected_rule_ids"] for item in per_case):
        raise InspectionError("at least one positive expected pattern required")
    if not any(not item["expected_rule_ids"] for item in per_case):
        raise InspectionError("at least one negative control required")
    tp = sum(len(set(c["observed_rule_ids"]) & set(c["expected_rule_ids"]))
             for c in per_case)
    fp = sum(len(c["false_positive_rule_ids"]) for c in per_case)
    fn = sum(len(c["false_negative_rule_ids"]) for c in per_case)
    # Number of no-pattern controls recognized as clean is a separate metric.
    neg = [c for c in per_case if not c["expected_rule_ids"]]
    tn = sum(not c["observed_rule_ids"] for c in neg)
    review_needed = {}
    for case in per_case:
        for kind, key in (("fp", "false_positive_rule_ids"),
                          ("fn", "false_negative_rule_ids")):
            for rule_id in case[key]:
                entry = review_needed.setdefault(rule_id, {"fp": 0, "fn": 0})
                entry[kind] += 1
    priority = [
        {"rule_id": rule_id,
         "false_positives": row["fp"],
         "false_negatives": row["fn"],
         "status": "HUMAN_REVIEW_ONLY_NO_AUTOMATIC_RULE_CHANGE"}
        for rule_id, row in sorted(
            review_needed.items(),
            key=lambda x: (-x[1]["fn"], -x[1]["fp"], x[0]),
        )
    ]
    payload = {
        "schema": "UCIE_MANUAL_INSPECTION_SYNTHETIC_FEEDBACK_V1",
        "status": "FIRST_PARTY_SYNTHETIC_CALIBRATION_ONLY",
        "case_count": len(per_case),
        "true_positive_rules": tp, "false_positive_rules": fp,
        "false_negative_rules": fn,
        "negative_control_cases": len(neg),
        "clean_negative_control_cases": tn,
        "precision_ppm": None if tp+fp == 0 else tp*1000000//(tp+fp),
        "recall_ppm": None if tp+fn == 0 else tp*1000000//(tp+fn),
        "next_review_priority": priority,
        "cases": per_case,
        "automatic_rule_updates": 0, "production_quality_claim": False,
        "new_approved_rules": 0,
        "source_executed": False,
        "network_requests": 0, "database_writes": 0,
        **DEFAULT_GATES,
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UCIE manual existing-rule Python inspector, explicit stdin only")
    parser.add_argument("--ucie-root", required=True, type=Path)
    parser.add_argument("--serial4-pack", type=Path)
    parser.add_argument("--owner-public-trust", type=Path)
    parser.add_argument("--serial5-pack", type=Path)
    parser.add_argument("--feedback-synthetic", action="store_true",
                        help="Evaluate bounded first-party synthetic labels; no writes")
    args = parser.parse_args()
    try:
        if (args.ucie_root.name.casefold() != "ucie"
                or args.ucie_root.is_symlink()
                or not args.ucie_root.is_dir()):
            raise InspectionError("only explicit UCIE checkout is allowed")
        if args.feedback_synthetic:
            if (args.serial4_pack or args.owner_public_trust
                    or args.serial5_pack):
                raise InspectionError("feedback cannot consume signed pack flags")
            raw = sys.stdin.buffer.read(81921)
            if not raw:
                raise InspectionError("EMPTY_FEEDBACK_STDIN")
            if len(raw) > 81920:
                raise InspectionError("OVERSIZED_FEEDBACK_STDIN")

            def no_duplicate_json_keys(pairs):
                values = {}
                for key, value in pairs:
                    if key in values:
                        raise InspectionError("duplicate feedback JSON property")
                    values[key] = value
                return values

            cases = json.loads(raw.decode("utf-8-sig", errors="strict"),
                               object_pairs_hook=no_duplicate_json_keys)
            result = evaluate_labeled_feedback(cases)
        else:
            raw = sys.stdin.buffer.read(MAX_BYTES+1)
            if not raw:
                raise InspectionError("EMPTY_SOURCE_STDIN")
            if len(raw) > MAX_BYTES:
                raise InspectionError("OVERSIZED_SOURCE_STDIN")
            result = inspect_existing_python(
                raw.decode("utf-8-sig", errors="strict"),
                root=args.ucie_root, serial4_pack=args.serial4_pack,
                owner_public_trust=args.owner_public_trust,
                serial5_pack=args.serial5_pack,
            )
    except (InspectionError, UnicodeError, SyntaxError, ValueError) as exc:
        # Only fixed, non-sensitive reason codes: never echo user source.
        reason_map = {
            "EMPTY_SOURCE_STDIN": "EMPTY_SOURCE_STDIN",
            "EMPTY_FEEDBACK_STDIN": "EMPTY_FEEDBACK_STDIN",
            "OVERSIZED_SOURCE_STDIN": "OVERSIZED_SOURCE_STDIN",
            "OVERSIZED_FEEDBACK_STDIN": "OVERSIZED_FEEDBACK_STDIN",
            "bounded labeled synthetic cases required": "FEEDBACK_CASE_ARRAY_REQUIRED",
            "strict synthetic feedback case shape required": "FEEDBACK_CASE_FIELDS_INVALID",
            "unknown/duplicated feedback label": "FEEDBACK_LABEL_INVALID",
            "FEEDBACK_CASE_SOURCE_INVALID": "FEEDBACK_CASE_SOURCE_INVALID",
            "FEEDBACK_CASE_SOURCE_PARSE_REJECTED": "FEEDBACK_CASE_PYTHON_INVALID",
            "cumulative feedback size exceeded": "FEEDBACK_CASES_OVERSIZED",
            "at least one positive expected pattern required": "FEEDBACK_POSITIVE_CASE_REQUIRED",
            "at least one negative control required": "FEEDBACK_NEGATIVE_CASE_REQUIRED",
            "duplicate feedback JSON property": "FEEDBACK_DUPLICATE_JSON_KEY",
            "only explicit UCIE checkout is allowed": "UCIE_ROOT_INVALID",
            "feedback cannot consume signed pack flags": "FEEDBACK_SIGNED_FLAGS_NOT_ALLOWED",
        }
        if isinstance(exc, json.JSONDecodeError):
            reason = "FEEDBACK_JSON_INVALID" if args.feedback_synthetic else "INVALID_SOURCE_INPUT"
        elif isinstance(exc, UnicodeError):
            reason = "INPUT_ENCODING_INVALID"
        else:
            reason = (reason_map.get(str(exc), "INVALID_INPUT_OR_CONFIGURATION")
                      if type(exc) is InspectionError else "INVALID_INPUT_OR_CONFIGURATION")
        result = {
            "schema": SCHEMA, "status": "UCIE_CODE_INSPECTION_FAIL_CLOSED",
            "error_type": type(exc).__name__, "reason_code": reason,
            "auto_promoted": False, "database_writes": 0,
            "source_executed": False,
        }
    print(json.dumps(result, sort_keys=True))
    return 2 if result["status"] == "UCIE_CODE_INSPECTION_FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
