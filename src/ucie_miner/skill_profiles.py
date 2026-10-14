"""Five reusable UCIE *capability profiles* for public technical evidence.

Profiles dispatch repeatable read-only analysis work, not chat instructions,
arbitrary code execution, private-app access or Rulepack auto-promotion.
"""
from __future__ import annotations

from .public_discovery import SOURCE_SKILL
from .public_discovery import DiscoveryError

PROFILE = {
    "python-runtime-safety": {
        "domain": "Python",
        "review_question": "Does this merged public change mitigate a runtime error or concurrency hazard?",
        "recommended_action": "CHECK_PUBLIC_VERSION_AND_REPRODUCE_IN_ISOLATED_RUNNER",
        "safe_call": "Review iterator ownership and exception-safe calls; run no upstream patch automatically",
    },
    "powershell-safe-calls": {
        "domain": "PowerShell",
        "review_question": "Does the fix change command resolution, relative paths or error handling?",
        "recommended_action": "CHECK_COMMAND_IDENTITY_AND_PS_VERSION",
        "safe_call": "Use reviewed CommandInfo identity and anchored paths without invoking unknown commands",
    },
    "git-workflow-prevention": {
        "domain": "Git",
        "review_question": "Is the change relevant to CLI errors, data loss or compatibility?",
        "recommended_action": "CHECK_GIT_RELEASE_NOTES_AND_RECOVERY_TESTS",
        "safe_call": "Use isolated throwaway repositories for proposed Git behavior tests",
    },
    "mcp-api-compatibility": {
        "domain": "MCP/API",
        "review_question": "Do public SDK changes alter argument schemas, error codes or supported runtimes?",
        "recommended_action": "CHECK_MCP_SDK_VERSION_AND_SCHEMA_CONTRACT",
        "safe_call": "Validate declared schema and reject unknown prompts/tools without arbitrary execution",
    },
    "runner-environment-drift": {
        "domain": "GitHub Actions Runner",
        "review_question": "Does a public runner image change affect CI tool versions or environment behavior?",
        "recommended_action": "CHECK_PINNED_RUNNER_IMAGE_AND_TOOL_VERSION",
        "safe_call": "Use explicit runner image versions and synthetic CI smoke tests",
    },
}


def prepare_public_skill_tasks(priority: dict) -> dict:
    """Build short human-readable playbooks from an unapproved lead queue."""
    if (not isinstance(priority, dict)
            or priority.get("schema") != "UCIE_ADAPTIVE_PUBLIC_PRIORITY_PREVIEW_V1"
            or priority.get("status") != "CANDIDATES_ONLY"
            or priority.get("production_approved") is not False
            or priority.get("persistent_feedback_learning") is not False
            or priority.get("rules_auto_promoted") != 0
            or not isinstance(priority.get("novel_review_queue"), list)
            or len(priority["novel_review_queue"]) > 30):
        raise DiscoveryError("invalid priority receipt for public skills")
    tasks = []
    for lead in priority["novel_review_queue"]:
        if not isinstance(lead, dict):
            raise DiscoveryError("malformed public task lead")
        skill = lead.get("skill_id")
        source = lead.get("source")
        number = lead.get("pr_number")
        if (skill not in PROFILE or SOURCE_SKILL.get(source) != skill
                or type(number) is not int or number < 1
                or lead.get("public_url") !=
                    f"https://github.com/{source}/pull/{number}"
                or lead.get("independent_fix_verified") is not False
                or lead.get("auto_promoted") is not False):
            raise DiscoveryError("unsupported public task source or forged approval")
        profile = PROFILE[skill]
        tasks.append({
            "skill_id": skill,
            "domain": profile["domain"],
            "public_pr": lead["public_url"],
            "question": profile["review_question"],
            "next_review": profile["recommended_action"],
            "safe_call": profile["safe_call"],
            "independent_evidence_needed": (
                "EXACT_UPSTREAM_COMMIT_VERSION_LICENSE_AND_SYNTHETIC_REGRESSION"),
            "status": "UNVERIFIED_RESEARCH_TASK",
            "auto_executed": False,
            "auto_learned": False,
            "production_approved": False,
        })
    return {
        "schema": "UCIE_REUSABLE_PUBLIC_SKILL_TASKS_V1",
        "skills_available": sorted(PROFILE),
        "tasks": tasks,
        "task_count": len(tasks),
        "workflow": "COLLECT_PUBLIC_METADATA__RANK__SELECT_SKILL__MANUAL_REVIEW",
        "persistent_writes": 0,
        "installed_chatgpt_skill": False,
        "automation_registered": False,
        "production_approved": False,
    }
