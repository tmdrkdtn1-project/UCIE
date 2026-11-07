"""UCIE full-product four-pillar installed CLI: FIRST-PARTY STAGING ONLY.

A real callable user entry point for the four existing UCIE product engines,
not a signed or customer-approved release. It never takes project paths,
source code, private repositories, customer tokens or scheduler arguments.
Real UCIE-authored recipes run only on temporary, synthetic first-party input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

SCHEMA = "UCIE_FOUR_PILLAR_INSTALLED_STAGING_V01"
STATE = "FOUR_PILLAR_FUNCTIONAL_STAGING_NOT_CUSTOMER_RELEASE"
PILLARS = (
    "error_prevention",
    "development_engines_and_skills",
    "virtual_library_and_skillbooks",
    "continuous_evidence_evolution",
)


class CustomerStagingError(ValueError):
    """A first-party preview contract could not be exercised safely."""


def _error_prevention() -> dict:
    from .guarded_scandir import GuardedScandir
    from .skillbook_scandir_recipe_v01 import bounded_regular_file_names

    expected = ("ucie_alpha.py", "ucie_beta.py")
    with TemporaryDirectory(prefix="UCIE_ERROR_SYNTHETIC_") as tmp:
        root = Path(tmp)
        for filename in expected:
            (root / filename).write_text(
                "# UCIE synthetic example only\n", encoding="utf-8"
            )
        recipe = bounded_regular_file_names(root, max_entries=8)
        with GuardedScandir(root) as entries:
            guarded = tuple(sorted(
                item.name for item in entries
                if item.is_file(follow_symlinks=False)
            ))
        if recipe != expected or guarded != expected:
            raise CustomerStagingError("bounded error-prevention recipe drift")
    return {
        "status": "FIRST_PARTY_BOUNDARIES_EXERCISED_ON_SYNTHETIC_INPUT",
        "real_ucie_recipe_executed": True,
        "guarded_iterator_executed": True,
        "synthetic_file_count": 2,
        "all_iterator_resources_closed": True,
        "customer_directory_inspected": False,
        "customer_source_read": False,
        "automatic_fix_applied": False,
    }


def _engines() -> dict:
    from .capability_trials import RECIPES, evaluate_ucie_owned_recipe

    trials = []
    for purpose in sorted(RECIPES):
        result = evaluate_ucie_owned_recipe(
            purpose, rows=64, queries=8, repeats=1
        )
        if (result.get("purpose_code") != purpose
                or result.get("exact_result_equivalence_observed") is not True
                or result.get("evaluates_upstream_code") is not False
                or result.get("production_adopted") is not False
                or result.get("auto_promoted") is not False
                or result.get("operating_database_writes") != 0):
            raise CustomerStagingError("first-party capability parity drift")
        trials.append({
            "purpose_code": purpose,
            "kind": result["kind"],
            "recipe_id": result["recipe_id"],
            "workload_sha256": result["workload_sha256"],
            "exact_result_equivalence_observed": True,
            "baseline_operations": result["baseline_operations"],
            "candidate_operations_including_setup": (
                result["candidate_operations_including_setup"]
            ),
            "upstream_benefit_verified": False,
            "production_adopted": False,
        })
    if len(trials) != 3:
        raise CustomerStagingError("implemented capability inventory drift")
    return {
        "status": "THREE_UCIE_OWNED_RECIPES_SYNTHETICALLY_EXERCISED",
        "development_engine_skill_learning_logic_trials": trials,
        "real_customer_workload_verified": False,
        "external_code_executed": False,
        "automatic_promotion": False,
    }


def _library(query: str) -> dict:
    from .skillbook_product_v01 import get_skillbook, search_skillbooks
    from .skillbook_git_porcelain_recipe_v01 import summarize_porcelain_v1_z

    if type(query) is not str or len(query) > 48:
        raise CustomerStagingError("unsafe library query")
    # Always inspect the unfiltered fixed 2-book baseline first.
    baseline = search_skillbooks()
    if baseline.get("total") != 2:
        raise CustomerStagingError("fixed SkillBook inventory drift")
    selected = search_skillbooks(query=query)
    books = []
    for item in selected["items"]:
        book = get_skillbook(item["skillbook_id"])
        evidence = book["source_evidence"]
        if (book.get("status") != "FIRST_PARTY_DRAFT_NOT_APPROVED"
                or book.get("export_allowed") is not False
                or book["proof_gates"].get("human_approved") is not False
                or item.get("human_approved") is not False
                or item.get("export_allowed") is not False):
            raise CustomerStagingError("unapproved SkillBook promotion drift")
        books.append({
            "skillbook_id": book["skillbook_id"],
            "title": book["title"],
            "source_id": book["library_entry"]["source_id"],
            "source_document_sha256": evidence["source_document_sha256"],
            "chapter_count": len(book["ucie_authored_chapters"]),
            "callable": book["machine_skill_contract"]["callable"],
            "review_state": "DRAFT_REQUIRES_INDEPENDENT_APPROVAL",
            "customer_export_allowed": False,
        })
    # Exercise the other first-party book's safe, non-path-leaking Git recipe
    # on inert bytes, never run git or read a working repository.
    git_result = summarize_porcelain_v1_z(
        b" M ucie_synthetic_a.py\x00?? ucie_synthetic_b.py\x00",
        max_entries=4,
    )
    if (git_result["total_entries"] != 2
            or git_result["counts"]["tracked_changed"] != 1
            or git_result["counts"]["untracked"] != 1
            or git_result["filenames_or_content_returned"] is not False
            or git_result["git_process_executed"] is not False):
        raise CustomerStagingError("Git SkillBook consumer contract drift")
    return {
        "status": "TWO_FIRST_PARTY_BOOKS_BROWSEABLE_NOT_APPROVED",
        "fixed_library_total": 2,
        "filtered_book_count": len(books),
        "books": books,
        "git_porcelain_recipe_synthetic_entries_verified": 2,
        "approved_or_exportable_books": 0,
        "remote_source_fetched": False,
        "external_git_process_invoked": False,
    }


def _evolution() -> dict:
    from .experience_evolution import run_evolution_cycle

    # The real learning candidate evaluator runs in a disposable UCIE-only
    # scratch tree. record=False means no experience/operating ledger writes.
    with TemporaryDirectory(prefix="UCIE_EVOLUTION_SYNTHETIC_") as tmp:
        root = Path(tmp) / "UCIE"
        (root / "runtime").mkdir(parents=True)
        observed = run_evolution_cycle(root, record=False)
        if (observed.get("new_experiment_executed") is not True
                or observed.get("new_event_written") is not False
                or observed.get("auto_promoted") is not False
                or observed.get("production_algorithm_changed") is not False
                or observed.get("operating_database_writes") != 0
                or observed.get("network_requests") != 0
                or any((root / "runtime").iterdir())):
            raise CustomerStagingError("first-party evolution contract drift")
        receipt = observed["receipt"]
        if (receipt["result_equivalent"] is not True
                or receipt["source_kind"] !=
                    "UCIE_FIRST_PARTY_SYNTHETIC_EXECUTION"):
            raise CustomerStagingError("evolution receipt evidence mismatch")
    return {
        "status": "UCIE_OWNED_NEXT_EXPERIMENT_EXERCISED_NO_PROMOTION",
        "experiment_id": observed["experiment_id"],
        "current_workload": observed["current_workload"],
        "experiment_dataset_sha256": receipt["dataset_sha256"],
        "reference_operations": receipt["baseline_operations"],
        "candidate_operations": receipt["candidate_operations"],
        "exact_result_equivalence_observed": True,
        "next_experiment": observed["next_experiment"],
        "experience_ledger_written": False,
        "model_weights_changed": False,
        "production_change_applied": False,
    }


def run_four_pillar_staging(*, pillar: str = "all", query: str = "") -> dict:
    """Exercise exactly the requested installed first-party product surfaces."""
    if type(pillar) is not str or pillar not in ("all", *PILLARS):
        raise CustomerStagingError("unknown full-product pillar")
    if type(query) is not str or len(query) > 48:
        raise CustomerStagingError("invalid bounded source query")
    if query and pillar not in ("all", "virtual_library_and_skillbooks"):
        raise CustomerStagingError("query is only supported for the library")
    selected = PILLARS if pillar == "all" else (pillar,)
    runners = {
        "error_prevention": _error_prevention,
        "development_engines_and_skills": _engines,
        "virtual_library_and_skillbooks": lambda: _library(query),
        "continuous_evidence_evolution": _evolution,
    }
    observations = {name: runners[name]() for name in selected}
    return {
        "schema": SCHEMA,
        "status": STATE,
        "distribution": "PRIVATE_DESIGNATED_CUSTOMERS_PROPRIETARY",
        "requested_pillar": pillar,
        "pillars_exercised": list(selected),
        "four_pillars_exercised": len(selected) == 4,
        "workflows": observations,
        "execution_scope": "UCIE_AUTHORED_DISPOSABLE_SYNTHETIC_ONLY",
        "product_capabilities_worked_in_staging": True,
        "complete_customer_functional_acceptance": False,
        "customer_license_issued": False,
        "customer_bundle_signed": False,
        "customer_distribution_authorized": False,
        "customer_data_scanned": False,
        "upstream_source_executed": False,
        "operating_ucie_database_written": False,
        "customer_project_modified": False,
        "scheduler_modified": False,
        "automatic_rule_promotion": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE four-pillar installed staging preview (NOT a released customer product)",
    )
    parser.add_argument(
        "--pillar", choices=("all", *PILLARS), default="all",
    )
    parser.add_argument(
        "--query", default="",
        help="bounded library title/topic search; no project paths or code",
    )
    args = parser.parse_args(argv)
    try:
        result = run_four_pillar_staging(
            pillar=args.pillar, query=args.query
        )
    except Exception:
        # Never print arbitrary exception messages, local paths, source text,
        # credentials or stack traces to the customer-facing preview.
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_FOUR_PILLAR_STAGING_FAIL_CLOSED",
            "customer_distribution_authorized": False,
            "customer_data_scanned": False,
            "operating_ucie_database_written": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
