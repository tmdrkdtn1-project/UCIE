"""UCIE Stage 5 static detector calibration on *synthetic*, explicitly labeled text.

All test snippets are caller-provided in memory and parsed inertly with AST.
This is not an independent benchmark, real-world accuracy estimate, or
authorization gate. Never executes, scans files or persists source text.
"""
from __future__ import annotations

import hashlib
import json

from .static_concurrency import inspect_python_scandir_source

MAX_FIXTURES = 32
MAX_TOTAL_BYTES = 262144


class AccuracyInputError(ValueError):
    pass


def measure_python_synthetic_cases(cases: object) -> dict:
    """Measure only fixture-label agreement; cannot claim production quality."""
    if (not isinstance(cases, list) or not 2 <= len(cases) <= MAX_FIXTURES):
        raise AccuracyInputError("bounded labeled synthetic cases required")
    result = []
    seen = set()
    total = 0
    for item in cases:
        if (not isinstance(item, dict)
                or set(item) != {"case_id", "source", "expected_flag"}):
            raise AccuracyInputError("invalid labeled case fields")
        case_id, source, flag = (
            item["case_id"], item["source"], item["expected_flag"])
        if (not isinstance(case_id, str) or not 1 <= len(case_id) <= 64
                or not all(ch.isascii() and (ch.isalnum() or ch in "-_")
                           for ch in case_id)
                or case_id in seen
                or not isinstance(source, str)
                or type(flag) is not bool):
            raise AccuracyInputError("duplicate case or malformed label")
        seen.add(case_id)
        total += len(source.encode("utf-8", "surrogatepass"))
        if total > MAX_TOTAL_BYTES:
            raise AccuracyInputError("cumulative fixture limit exceeded")
        scan = inspect_python_scandir_source(source)
        result.append({
            "case_id": case_id,
            "source_sha256": scan["source_sha256"],
            "expected_flag": flag,
            "observed_flag": scan["finding_count"] > 0,
            "finding_count": scan["finding_count"],
            "label_origin": "UCIE_AUTHORED_SYNTHETIC",
        })
    positive = sum(x["expected_flag"] for x in result)
    negative = len(result) - positive
    if positive == 0 or negative == 0:
        raise AccuracyInputError("positive and negative controls both required")
    tp = sum(x["expected_flag"] and x["observed_flag"] for x in result)
    fp = sum(not x["expected_flag"] and x["observed_flag"] for x in result)
    fn = sum(x["expected_flag"] and not x["observed_flag"] for x in result)
    tn = sum(not x["expected_flag"] and not x["observed_flag"] for x in result)

    def fraction(n, d):
        return None if d == 0 else (n * 1000000) // d

    digest = hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    return {
        "schema": "UCIE_SYNTHETIC_STATIC_ACCURACY_V1",
        "status": "SYNTHETIC_CALIBRATION_ONLY",
        "fixture_count": len(result),
        "positive_controls": positive,
        "negative_controls": negative,
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "precision_ppm": fraction(tp, tp + fp),
        "recall_ppm": fraction(tp, tp + fn),
        "observations": result,
        "fixture_observation_sha256": digest,
        "real_world_accuracy_verified": False,
        "independently_validated_labels": False,
        "rules_promoted": 0,
        "persistent_writes": 0,
        "production_approved": False,
    }
