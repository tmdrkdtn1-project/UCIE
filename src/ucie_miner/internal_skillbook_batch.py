"""Offline UCIE SkillBook metadata batch engine; no API, model or operator project access.

This is a bounded first-party stage for P10-compatible independent workers.
It does NOT register jobs, create a scheduler, read files, or perform semantic
synthesis. Future production task wiring requires a separate reviewed change.
"""
from __future__ import annotations

import hashlib
import json

from .skillbook_blueprint import compose_blueprint, SkillBookBlueprintError

SCHEMA = "UCIE_INTERNAL_SKILLBOOK_METADATA_BATCH_V1"
MAX_TASKS = 8
MAX_TOTAL_CANDIDATES = 80
MAX_INPUT_BYTES = 65536
TASK_FIELDS = frozenset({"topic", "candidates"})


class InternalSkillBookEngineError(ValueError):
    """Invalid, untrusted, or over-budget UCIE metadata batch."""


def process_metadata_batch(tasks: list[dict]) -> dict:
    """Execute bounded, deterministic composition locally without external AI APIs.

    Reuses exact duplicate task results in this invocation. Job scheduling
    and process concurrency remain with existing P10; this function does not
    spawn threads/processes or import private project content.
    """
    if type(tasks) is not list or not 1 <= len(tasks) <= MAX_TASKS:
        raise InternalSkillBookEngineError("invalid bounded task list")
    total = 0
    canonical_tasks = []
    for task in tasks:
        if type(task) is not dict or set(task) != TASK_FIELDS:
            raise InternalSkillBookEngineError("invalid or untrusted task fields")
        candidates = task["candidates"]
        if type(candidates) is not list:
            raise InternalSkillBookEngineError("invalid candidate collection")
        total += len(candidates)
        if total > MAX_TOTAL_CANDIDATES:
            raise InternalSkillBookEngineError("candidate budget exceeded")
        # Hash canonical task identity; never persist or echo arbitrary input.
        try:
            canonical = json.dumps(task, sort_keys=True, ensure_ascii=True,
                                   separators=(",", ":"), allow_nan=False)
        except (ValueError, TypeError, OverflowError) as exc:
            raise InternalSkillBookEngineError("unsafe non-JSON candidate data") from exc
        if len(canonical.encode("utf-8")) > MAX_INPUT_BYTES:
            raise InternalSkillBookEngineError("task input limit exceeded")
        canonical_tasks.append((task, canonical))
    compiled = {}
    results = []
    cache_hits = 0
    for task, canonical in canonical_tasks:
        key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if key in compiled:
            cache_hits += 1
        else:
            try:
                compiled[key] = compose_blueprint(task["topic"], task["candidates"])
            except SkillBookBlueprintError as exc:
                # The error is sanitized; no source text or arbitrary task content.
                raise InternalSkillBookEngineError("public evidence validation failed") from exc
        blueprint = compiled[key]
        results.append({
            "task_digest_sha256": key,
            "blueprint_id": blueprint["blueprint_id"],
            "chapter_count": blueprint["chapter_count"],
            "status": "UNVERIFIED_METADATA_ONLY",
            "export_allowed": False,
        })
    return {
        "schema": SCHEMA,
        "status": "LOCAL_METADATA_BATCH_COMPLETE_UNVERIFIED",
        "results": results,
        "jobs_processed": len(results),
        "distinct_job_inputs": len(compiled),
        "local_cache_hits": cache_hits,
        "source_candidates_seen": total,
        "external_ai_api_calls": 0,
        "local_language_model_calls": 0,
        "new_scheduler_registered": False,
        "task_queue_mutated": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "source_code_executed": False,
        "other_project_data_accessed": False,
        "machine_skill_created": False,
        "skillbook_verified_or_published": False,
        "auto_promoted": False,
    }
