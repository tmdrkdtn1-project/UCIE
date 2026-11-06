"""UCIE-only historical Slack recheck gate for owner/deployment/identity claims.

This gate cannot authenticate a remote MCP caller or authorize mutations.
It prevents a negative "missing/unverified" verdict from being emitted merely
because one source path or one code search does not contain a known admin name.

Only a *trusted host-owned* Slack search adapter may be supplied. A remote MCP
payload, caller-provided proof flag, cached receipt, or static owner marker is
not an adapter. No network, Slack token, plugin config, or other project read
occurs inside this module.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

SCHEMA = "UCIE_ADMIN_HISTORICAL_SLACK_VERDICT_V1"
CHANNEL = "C0CA4AW06BH"
SLACK_BASE = "https://kangsoolnc.slack.com/archives/" + CHANNEL + "/"
REPOSITORY = "tmdrkdtn1-project/UCIE"
SEARCH_TERMS = (
    "PR #78",
    "UCIE_OWNER_LOCAL_ADMIN_AND_LEGACY_SEARCH_VERIFIED",
    "UCIE_UnattendedHost",
    "Auth0",
)
MAX_PAGES_PER_QUERY = 25
MAX_RESULTS_PER_PAGE = 20
MAX_MESSAGE_CHARS = 20000

# Independently located prior records. These are historical evidence, NOT
# proof of the current plugin backend owner or its per-call authorization.
ANCHORS = (
    {
        "key": "UCIE_ADMIN_PR78_OWNER_LAUNCH",
        "query": "UCIE_OWNER_LOCAL_ADMIN_AND_LEGACY_SEARCH_VERIFIED",
        "ts": "1792896036.978529",
        "url": SLACK_BASE + "p1792896036978529",
        "must_include": (
            "PR #78", "UCIE_OWNER_LOCAL_ADMIN_AND_LEGACY_SEARCH_VERIFIED",
            "관리자 도구 9개",
        ),
    },
    {
        "key": "UCIE_P10_PROTECTED_ROOT_SELF_CHECK",
        "query": "UCIE_UnattendedHost",
        "ts": "1792899889.147509",
        "url": SLACK_BASE + "p1792899889147509",
        "must_include": (
            "UCIE_P10_ONE_PROTECTED_DIRECTORY_CREATED_ACL_RECHECK_ONLY",
            "UCIE_UnattendedHost",
        ),
    },
    {
        "key": "UCIE_C45_AUTH0_READONLY_SCOPE",
        "query": "Auth0",
        "ts": "1792513195.589169",
        "url": SLACK_BASE + "p1792513195589169",
        "must_include": ("Auth0", "ucie:read", "C41"),
    },
)
HISTORICAL_SOURCE_PIN = {
    "pr": "https://github.com/tmdrkdtn1-project/UCIE/pull/78",
    "source_doc": (
        "https://github.com/tmdrkdtn1-project/UCIE/blob/"
        "feat/ucie-local-write-bridge-20261023/docs/UCIE_LOCAL_ADMIN_BRIDGE_V1.md"
    ),
    "registration": "src/ucie_admin/mcp_registration.py",
    "owner_launcher": "scripts/ucie_owner_admin_mcp_launch.ps1",
    "server_file": r"D:\UCIE_DATA\library_app\private_lib\mcp_stdio_server.py",
    "source_root": r"D:\UCIE_PREVIEW\UCIE_ADMIN\src",
}
CLAIMS = frozenset({
    "ADMIN_OWNER_ABSENT",
    "ADMIN_DEPLOYMENT_PATH_ABSENT",
    "ADMIN_IDENTITY_EVIDENCE_ABSENT",
    "PLUGIN_BACKEND_OWNER_CURRENTLY_UNVERIFIED",
    "FOUR_NEW_OWNER_TOOLS_RUNTIME_UNVERIFIED",
})


class SlackRecheckRequired(ValueError):
    """A required historical query or source validation was not completed."""


def _page(provider: Callable, query: str, cursor: str | None) -> dict:
    try:
        page = provider(CHANNEL, query, cursor)
    except Exception as exc:
        raise SlackRecheckRequired("TRUSTED_SLACK_SEARCH_UNAVAILABLE") from exc
    if (type(page) is not dict or page.get("channel_id") != CHANNEL
            or page.get("query") != query
            or type(page.get("messages")) is not list
            or type(page.get("complete")) is not bool
            or len(page["messages"]) > MAX_RESULTS_PER_PAGE):
        raise SlackRecheckRequired("SLACK_SEARCH_PAGE_INVALID")
    next_cursor = page.get("next_cursor")
    if next_cursor is not None and (
            type(next_cursor) is not str or not next_cursor
            or len(next_cursor) > 2048):
        raise SlackRecheckRequired("SLACK_CURSOR_INVALID")
    if page["complete"] is not (next_cursor is None):
        raise SlackRecheckRequired("SLACK_PAGINATION_INCOMPLETE")
    for item in page["messages"]:
        if type(item) is not dict or set(item) != {
            "channel_id", "ts", "permalink", "text"
        }:
            raise SlackRecheckRequired("SLACK_ITEM_SCHEMA_INVALID")
        ts = item["ts"]
        url = item["permalink"]
        body = item["text"]
        if (item["channel_id"] != CHANNEL or type(ts) is not str
                or type(url) is not str or type(body) is not str
                or not (0 < len(body) <= MAX_MESSAGE_CHARS)
                or not ts.replace(".", "").isdigit()
                or ts.count(".") != 1
                or not url.startswith(SLACK_BASE + "p")
                or url != SLACK_BASE + "p" + ts.replace(".", "")):
            raise SlackRecheckRequired("SLACK_ITEM_ORIGIN_INVALID")
    return page


def recheck_ucie_history(search_provider: Callable, *,
                         now: datetime | None = None) -> dict:
    """Re-search the exact UCIE Slack channel at the moment of judgment.

    No caller-supplied completed/stale receipt is accepted. The adapter must
    execute actual Slack queries and return every page. This check is an audit
    gate, not a cryptographic attestation or a permission grant.
    """
    if not callable(search_provider):
        raise SlackRecheckRequired("TRUSTED_SLACK_PROVIDER_REQUIRED")
    checked_at = now if now is not None else datetime.now(timezone.utc)
    if (not isinstance(checked_at, datetime)
            or checked_at.tzinfo is None
            or checked_at.utcoffset() is None):
        raise SlackRecheckRequired("UTC_REVIEW_CLOCK_REQUIRED")
    seen_anchors = set()
    query_counts = {}
    for query in SEARCH_TERMS:
        cursor = None
        seen_cursors = set()
        count = 0
        for _ in range(MAX_PAGES_PER_QUERY):
            page = _page(search_provider, query, cursor)
            count += len(page["messages"])
            for item in page["messages"]:
                for anchor in ANCHORS:
                    if (anchor["query"] == query
                            and item["ts"] == anchor["ts"]
                            and item["permalink"] == anchor["url"]
                            and all(marker in item["text"]
                                    for marker in anchor["must_include"])):
                        seen_anchors.add(anchor["key"])
            cursor = page["next_cursor"]
            if cursor is None:
                break
            if cursor in seen_cursors:
                raise SlackRecheckRequired("SLACK_CURSOR_REPEATED")
            seen_cursors.add(cursor)
        else:
            raise SlackRecheckRequired("SLACK_PAGES_NOT_EXHAUSTED")
        query_counts[query] = count
    missing = {anchor["key"] for anchor in ANCHORS} - seen_anchors
    if missing:
        # Do not treat an empty/partial/unexpected Slack result as absence
        # when previously confirmed UCIE deployment facts are on record.
        raise SlackRecheckRequired("PREVIOUS_SLACK_PROOFS_NOT_RECONCILED")
    return {
        "schema": SCHEMA,
        "review_status": "FRESH_UCIE_SLACK_HISTORY_RECHECK_MATCHED",
        "reviewed_utc": checked_at.astimezone(timezone.utc).isoformat(),
        "channel_id": CHANNEL,
        "queries_exhausted": len(query_counts),
        "anchors_reconfirmed": sorted(seen_anchors),
        "source_urls": sorted(a["url"] for a in ANCHORS),
        "raw_slack_messages_returned": False,
        "current_plugin_backend_owner_proven": False,
        "remote_per_request_identity_proven": False,
        "new_owner_four_tool_registration_proven": False,
        "authorizes_mcp_mutation": False,
    }


def judge_negative_ucie_admin_claim(claim: str, *,
                                    search_provider: Callable | None = None,
                                    now: datetime | None = None) -> dict:
    """Only canonical negative-claim decision API; rechecks Slack every call.

    This method NEVER issues an absolute negative verdict about an established
    owner/source/deployment path, nor authorizes an MCP mutation.
    """
    if claim not in CLAIMS or type(claim) is not str:
        raise ValueError("unsupported UCIE admin historical claim")
    base = {
        "schema": SCHEMA,
        "requested_claim": claim,
        "final_absence_verdict_allowed": False,
        "mcp_mutation_authorized": False,
        "owner_and_deployment_are_the_same_as_remote_user_auth": False,
    }
    try:
        audit = recheck_ucie_history(search_provider, now=now)
    except SlackRecheckRequired as exc:
        return {
            **base,
            "status": "HISTORY_RECHECK_REQUIRED_BLOCK_VERDICT",
            "block_code": str(exc),
            "reviewed_slack_now": False,
            "existing_historical_pr": HISTORICAL_SOURCE_PIN["pr"],
        }
    classifications = {
        "ADMIN_OWNER_ABSENT":
            "PR78_OWNER_LOCAL_APPROVAL_EXISTS_ABSENCE_REJECTED",
        "ADMIN_DEPLOYMENT_PATH_ABSENT":
            "PR78_DEPLOYMENT_AND_REGISTRATION_PATH_EXISTS_ABSENCE_REJECTED",
        "ADMIN_IDENTITY_EVIDENCE_ABSENT":
            "HISTORICAL_LOCAL_OWNER_GATE_EXISTS_REMOTE_IDENTITY_NOT_PROVEN",
        "PLUGIN_BACKEND_OWNER_CURRENTLY_UNVERIFIED":
            "BACKEND_PLUGIN_OWNERSHIP_REQUIRES_CURRENT_CONTROL_PLANE_PROOF",
        "FOUR_NEW_OWNER_TOOLS_RUNTIME_UNVERIFIED":
            "FOUR_TOOLS_REQUIRE_CURRENT_TOOLS_LIST_AND_AUTH_PROOF",
    }
    return {
        **base,
        "status": classifications[claim],
        "reviewed_slack_now": True,
        "review": audit,
        "historical_pr_78": HISTORICAL_SOURCE_PIN["pr"],
        "historical_registration_module":
            HISTORICAL_SOURCE_PIN["registration"],
        "historical_launch_script":
            HISTORICAL_SOURCE_PIN["owner_launcher"],
    }


def main() -> int:
    import json
    # No trusted Slack connector is available in this standalone Python CLI.
    # It must fail closed, not pretend that a stored local JSON reviewed Slack.
    report = judge_negative_ucie_admin_claim(
        "ADMIN_DEPLOYMENT_PATH_ABSENT", search_provider=None
    )
    print(json.dumps(report, sort_keys=True))
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
