"""UCIE V1 final product goals and roadmap, strictly inert planning data.

This module does NOT implement the finished Source Registry, Virtual Library,
learning engine or a production release. W01/W02 have initial code contracts,
not an integrated source crawler or searchable library. It offers a work-order
preview without network, filesystem, scheduler, source execution or mutation.
Canonical human specifications: docs/UCIE_V1_MASTER_ROADMAP_20261027.md.
"""
from __future__ import annotations

import json

SCHEMA = "UCIE_V1_FOUR_PILLAR_PRODUCT_PLAN_V1"
WORKROOM = "UCIE_MAIN_DEV"
CURRENT_PHASE = "P0_BASELINE_OBSERVED__P1_AND_P3_NEXT"
STATUS = "PLAN_DEFINED_IMPLEMENTATION_INCOMPLETE"

PILLARS = (
    ("G1", "CODING_ERROR_PREVENTION"),
    ("G2", "DEVELOPMENT_MAINTENANCE_ENGINE_SKILL_LEARNING_LOGIC_DISCOVERY_IMPROVEMENT"),
    ("G3", "CATEGORIZED_REUSABLE_VIRTUAL_KNOWLEDGE_LIBRARY"),
    ("G4", "UCIE_EXPERIENCE_DRIVEN_CONTINUAL_LIBRARY_EVOLUTION"),
)
FOUNDATIONS = ("APPROVED_PUBLIC_SOURCE_SELECTION", "MODULAR_AUTOMATIC_PUBLIC_ACQUISITION")
APPROVED_REPOSITORIES = (
    "python/cpython",
    "PowerShell/PowerShell",
    "git/git",
    "modelcontextprotocol/python-sdk",
    "actions/runner-images",
)
OFFICIAL_PUBLIC_MATERIAL = (
    "OFFICIAL_TECHNICAL_DOCUMENTATION",
    "OFFICIAL_RELEASE_NOTES",
    "OFFICIAL_SECURITY_ADVISORIES",
)
RESEARCH_ONLY_SOURCE_CANDIDATES = (
    "GH Archive", "Software Heritage", "SWE-bench", "The Stack v2",
)

# NOT a runtime gate for external requests. Existing production allowlists
# remain authoritative; adding a source here is never an authorization.
MILESTONES = (
    ("P0", "PRESERVE_OBSERVED_FOUNDATION", "BASELINE_OBSERVED_PARTIAL",
     "Keep existing collector, evidence ledgers, signing and review tools intact."),
    ("P1", "APPROVED_SOURCE_REGISTRY", "NEXT",
     "Registry records source owner, approved vs research-only status, API, license and limits."),
    ("P2", "MODULAR_AUTOMATIC_PUBLIC_ACQUISITION", "PARTIAL",
     "Approved GitHub and official-material adapters feed bounded incremental normalized evidence."),
    ("P3", "CATEGORIZED_SEARCHABLE_VIRTUAL_LIBRARY", "NEXT",
     "Evidence-linked rule, skill, engine and learning-logic search with provenance and versions."),
    ("P4", "ENGINE_SKILL_LEARNING_LOGIC_DISCOVERY_IMPROVEMENT", "FOUNDATION_ONLY",
     "Identify and compare positive capabilities beyond error fixes using approved public evidence."),
    ("P5", "PREVENTION_KNOWLEDGE_LIBRARY_INTEGRATION", "PARTIAL",
     "Expose versioned signed and unsigned error-prevention items with correct status."),
    ("P6", "SAFE_CAPABILITY_EXPERIMENTS_AND_IMPROVEMENT", "PARTIAL",
     "Compare safe UCIE-authored performance and regression evidence before/after."),
    ("P7", "INDEPENDENTLY_REUSABLE_CAPABILITY_PACKAGES", "NOT_IMPLEMENTED",
     "Export only approved general-purpose version-pinned packages with dependencies."),
    ("P8", "UCIE_OWNED_EXPERIENCE_AND_LIBRARY_EVOLUTION", "PARTIAL",
     "Record allowed UCIE experiments and revision/rejection/improvement lineage."),
    ("P9", "INTEGRATED_UCIE_V1_PRODUCT", "NOT_ACCEPTED",
     "Demonstrate the connected intake-to-search-to-evaluation-to-export-to-evolution flow."),
)

# Work IDs are ordered for execution; some can run in parallel once their
# narrow interface contracts are agreed. All are planned tasks, NOT PASS.
WORK = (
    ("W01", "P1", "ACQUISITION", (),
     "Source Registry V1; allowlisted five repositories and official material types; unapproved sources inert."),
    ("W02", "P3", "LIBRARY", (),
     "LibraryEntry identity/kind/category/provenance/version/lifecycle/dependency contract."),
    ("W03", "P2", "ACQUISITION", ("W01",),
     "Adapt existing public miner to the new source adapter interface without replacing the scheduler."),
    ("W04", "P3", "LIBRARY", ("W02",),
     "Read-only search and indexing over existing Stage10-17 metadata and approved Rulepacks."),
    ("W05", "P4", "INTELLIGENCE", ("W01", "W02"),
     "Find and classify reusable engine/skill/learning-logic candidates beyond bug fixes."),
    ("W06", "P2", "ACQUISITION", ("W03",),
     "Integrate only already-approved official documentation, release and advisory routes."),
    ("W07", "P5", "LIBRARY", ("W04",),
     "Link exact version, signature and evidence state for prevention rules in Library."),
    ("W08", "P6", "INTELLIGENCE", ("W05",),
     "UCIE-authored bounded evaluation of a reusable skill/engine and before/after measures."),
    ("W09", "P7", "PRODUCT", ("W04", "W07", "W08"),
     "Package an approved generic capability with version, contract, dependency, lineage."),
    ("W10", "P8", "INTEGRATION", ("W03", "W06", "W09"),
     "Record UCIE-owned experience and demonstrate the complete P9 V1 closed loop."),
)
NEXT_PARALLEL = ("W01", "W02")
FOUNDATION_CODE_AVAILABLE = ("W01", "W02")  # code only; no local runtime or V1 acceptance
FOLLOWING_INTERFACE = ("W05",)
SAFE_STATUS_VALUES = frozenset({
    "BASELINE_OBSERVED_PARTIAL", "NEXT", "PARTIAL",
    "FOUNDATION_ONLY", "NOT_IMPLEMENTED", "NOT_ACCEPTED",
})


def validate_product_plan() -> bool:
    """Fail closed on contradictory roadmap metadata, not runtime operations."""
    if tuple(x[0] for x in PILLARS) != ("G1", "G2", "G3", "G4"):
        raise ValueError("four equally ranked UCIE goals required")
    if len(set(name for _, name in PILLARS)) != 4:
        raise ValueError("duplicate UCIE product goal")
    if len(FOUNDATIONS) != 2:
        raise ValueError("two acquisition foundations required")
    if set(APPROVED_REPOSITORIES) != {
        "python/cpython", "PowerShell/PowerShell", "git/git",
        "modelcontextprotocol/python-sdk", "actions/runner-images",
    }:
        raise ValueError("approved upstream scope changed")
    if set(RESEARCH_ONLY_SOURCE_CANDIDATES) & set(APPROVED_REPOSITORIES):
        raise ValueError("research-only source promoted into active list")
    if tuple(entry[0] for entry in MILESTONES) != tuple(f"P{i}" for i in range(10)):
        raise ValueError("P0-P9 roadmap is incomplete")
    if any(status not in SAFE_STATUS_VALUES for _, _, status, _ in MILESTONES):
        raise ValueError("unrecognized product readiness state")
    if tuple(entry[0] for entry in WORK) != tuple(f"W{i:02d}" for i in range(1, 11)):
        raise ValueError("work sequence is incomplete")
    positions = {entry[0]: i for i, entry in enumerate(WORK)}
    for i, (work_id, milestone, track, dependencies, acceptance) in enumerate(WORK):
        if milestone not in {p[0] for p in MILESTONES}:
            raise ValueError("work references an unknown milestone")
        if track not in {"ACQUISITION", "LIBRARY", "INTELLIGENCE", "PRODUCT", "INTEGRATION"}:
            raise ValueError("unknown development track")
        if not acceptance or any(positions.get(dep, i) >= i for dep in dependencies):
            raise ValueError("invalid or cyclic work dependencies")
    if (NEXT_PARALLEL != ("W01", "W02") or FOLLOWING_INTERFACE != ("W05",)
            or FOUNDATION_CODE_AVAILABLE != ("W01", "W02")):
        raise ValueError("initial parallel roadmap boundary changed")
    return True


def preview_next_work() -> dict:
    """Pure metadata preview. It does not inspect or modify a user's runtime."""
    validate_product_plan()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "current_phase": CURRENT_PHASE,
        "pillars": [{"id": x, "goal": y} for x, y in PILLARS],
        "foundations": list(FOUNDATIONS),
        "milestones": [
            {"id": x, "goal": y, "planning_state": status, "acceptance": acceptance}
            for x, y, status, acceptance in MILESTONES
        ],
        "immediate_parallel_work": list(NEXT_PARALLEL),
        "next_contract_work": list(FOLLOWING_INTERFACE),
        "foundation_code_available": list(FOUNDATION_CODE_AVAILABLE),
        "work_order": [
            {"id": x, "milestone": milestone, "track": track,
             "depends_on": list(deps), "acceptance": acceptance,
             "execution_state": ("FOUNDATION_CODE_IMPLEMENTED_NOT_HOST_VERIFIED"
                                  if x in FOUNDATION_CODE_AVAILABLE
                                  else "PLANNED_NOT_EXECUTED")}
            for x, milestone, track, deps, acceptance in WORK
        ],
        "approved_public_repositories": list(APPROVED_REPOSITORIES),
        "approved_material_types": list(OFFICIAL_PUBLIC_MATERIAL),
        "research_only_source_candidates": list(RESEARCH_ONLY_SOURCE_CANDIDATES),
        "source_allowlist_changed": False,
        "runtime_modified": False,
        "scheduled_task_registered": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "other_projects_accessed": False,
        "candidate_auto_promoted": False,
        "rulepacks_signed": False,
        "v1_accepted": False,
    }


def main() -> int:
    print(json.dumps(preview_next_work(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
