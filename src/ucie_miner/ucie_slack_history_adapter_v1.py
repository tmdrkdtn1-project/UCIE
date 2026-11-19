"""UCIE-only, read-only Slack conversations.history adapter.

The hosting UCIE service supplies its *own trusted* Slack history reader.
No remote MCP payload can select a channel, token, URL or provider. This
module never imports Slack credentials, performs HTTP, or writes Slack data.

Slack conversation message text is untrusted EVIDENCE; it is never executed.
An adapter instance may be used for exactly one negative-verdict review;
a new instance must be created for each review. No persistent history cache.
"""
from __future__ import annotations

from collections.abc import Callable
import re

from . import ucie_admin_history_verdict_v1 as historical

CHANNEL = historical.CHANNEL
SOURCE = "SLACK_CONVERSATIONS_HISTORY_HOST_CALLBACK_V1"
PAGE_SIZE = 100
MAX_HISTORY_PAGES = 50
MAX_HISTORY_MESSAGES = 2000
MAX_BODY_CHARS = historical.MAX_MESSAGE_CHARS
TS = re.compile(r"[1-9][0-9]{8,11}\.[0-9]{6}\Z")


class UCIESlackHistoryAdapterError(ValueError):
    """Fail closed; never return an unsupported absence verdict."""


class UCIESlackHistoryAdapter:
    """Normalize trusted server-owned Slack history pages for history gate.

    read_history_page(channel_id, cursor, limit) must call an authenticated
    Slack conversations.history API for exactly the requested UCIE channel.
    Its implementation and credentials belong to the trusted host service,
    never to an MCP caller. This adapter verifies response schema, cursor
    closure, channel restriction, message sizes and the source structure;
    it cannot independently prove who owns a remote plugin connection.
    """

    def __init__(self, *, read_history_page: Callable):
        if not callable(read_history_page):
            raise UCIESlackHistoryAdapterError("TRUSTED_HOST_SLACK_READER_REQUIRED")
        self._read_history_page = read_history_page
        self._snapshot = None

    def _read_one(self, cursor: str | None) -> tuple[list, str | None]:
        try:
            raw = self._read_history_page(CHANNEL, cursor, PAGE_SIZE)
        except Exception as exc:
            raise UCIESlackHistoryAdapterError(
                "UCIE_SLACK_HISTORY_UPSTREAM_UNAVAILABLE") from exc
        if (type(raw) is not dict or raw.get("ok") is not True
                or type(raw.get("messages")) is not list
                or len(raw["messages"]) > PAGE_SIZE):
            raise UCIESlackHistoryAdapterError("UCIE_SLACK_HISTORY_RESPONSE_INVALID")
        # Slack Web API cursor, not page size, determines pagination.
        meta = raw.get("response_metadata") or {}
        if type(meta) is not dict:
            raise UCIESlackHistoryAdapterError("UCIE_SLACK_HISTORY_META_INVALID")
        next_cursor = meta.get("next_cursor") or None
        if next_cursor is not None and (
                type(next_cursor) is not str or len(next_cursor) > 2048):
            raise UCIESlackHistoryAdapterError("UCIE_SLACK_HISTORY_CURSOR_INVALID")
        more = raw.get("has_more")
        if more is not None and type(more) is not bool:
            raise UCIESlackHistoryAdapterError("UCIE_SLACK_HISTORY_HAS_MORE_INVALID")
        if more is True and next_cursor is None:
            raise UCIESlackHistoryAdapterError("UCIE_SLACK_HISTORY_INCOMPLETE_PAGE")
        if more is False and next_cursor is not None:
            raise UCIESlackHistoryAdapterError("UCIE_SLACK_HISTORY_CURSOR_CONFLICT")
        if raw.get("channel_id", CHANNEL) != CHANNEL:
            raise UCIESlackHistoryAdapterError("UCIE_SLACK_HISTORY_WRONG_CHANNEL")
        return raw["messages"], next_cursor

    def _load_once(self) -> tuple:
        if self._snapshot is not None:
            return self._snapshot
        items = []
        timestamps = set()
        cursor = None
        cursors = set()
        for _ in range(MAX_HISTORY_PAGES):
            messages, next_cursor = self._read_one(cursor)
            for item in messages:
                if type(item) is not dict:
                    raise UCIESlackHistoryAdapterError("UCIE_SLACK_MESSAGE_NOT_OBJECT")
                ts = item.get("ts")
                body = item.get("text", "")
                if (type(ts) is not str or not TS.fullmatch(ts)
                        or type(body) is not str
                        or len(body) > MAX_BODY_CHARS or ts in timestamps):
                    raise UCIESlackHistoryAdapterError("UCIE_SLACK_MESSAGE_INVALID")
                timestamps.add(ts)
                if body:  # Slack joins and non-text events can lack text.
                    items.append({
                        "channel_id": CHANNEL,
                        "ts": ts,
                        "permalink": historical.SLACK_BASE + "p" + ts.replace(".", ""),
                        "text": body,
                    })
            if len(timestamps) > MAX_HISTORY_MESSAGES:
                raise UCIESlackHistoryAdapterError("UCIE_SLACK_HISTORY_TOO_LARGE")
            if next_cursor is None:
                self._snapshot = tuple(items)
                return self._snapshot
            if next_cursor in cursors:
                raise UCIESlackHistoryAdapterError("UCIE_SLACK_HISTORY_CURSOR_REPEATED")
            cursors.add(next_cursor)
            cursor = next_cursor
        raise UCIESlackHistoryAdapterError("UCIE_SLACK_HISTORY_PAGES_NOT_EXHAUSTED")

    def __call__(self, channel_id: str, query: str, cursor: str | None) -> dict:
        if channel_id != CHANNEL or query not in historical.SEARCH_TERMS:
            raise UCIESlackHistoryAdapterError("UCIE_SLACK_QUERY_NOT_ALLOWLISTED")
        if cursor is not None:
            if (type(cursor) is not str or not re.fullmatch(r"offset-[1-9][0-9]{0,5}",
                                                          cursor)):
                raise UCIESlackHistoryAdapterError("UCIE_SLACK_REVIEW_CURSOR_INVALID")
            offset = int(cursor[7:])
            if offset % historical.MAX_RESULTS_PER_PAGE:
                raise UCIESlackHistoryAdapterError("UCIE_SLACK_REVIEW_CURSOR_INVALID")
        else:
            offset = 0
        # The fetched snapshot is in-memory for this one review only, with no
        # replayed disk receipts, caller-supplied complete flag or global cache.
        matches = [item for item in self._load_once()
                   if query.casefold() in item["text"].casefold()]
        limit = historical.MAX_RESULTS_PER_PAGE
        if len(matches) > limit * historical.MAX_PAGES_PER_QUERY:
            raise UCIESlackHistoryAdapterError("UCIE_SLACK_REVIEW_TOO_MANY_MATCHES")
        if offset >= len(matches) and offset != 0:
            raise UCIESlackHistoryAdapterError("UCIE_SLACK_REVIEW_CURSOR_OUT_OF_RANGE")
        end = offset + limit
        more = end < len(matches)
        return {
            "channel_id": CHANNEL,
            "query": query,
            "messages": matches[offset:end],
            "next_cursor": "offset-" + str(end) if more else None,
            "complete": not more,
        }


def history_verdict_from_trusted_reader(claim: str, *,
                                        read_history_page: Callable) -> dict:
    """End-to-end history gate, one new read-only Slack snapshot per judgment.

    Only the trusted UCIE server itself may call this with its app-owned
    Slack reader. Never expose the reader/callback/credentials to an MCP input.
    """
    # Missing host callback is a blocked judgment, not a raised exception
    # or a false statement that an established UCIE deployment is absent.
    provider = (UCIESlackHistoryAdapter(read_history_page=read_history_page)
                if callable(read_history_page) else None)
    return historical.judge_negative_ucie_admin_claim(
        claim, search_provider=provider
    )
