"""UCIE-only Slack Evidence Reader for the owner's Windows Credential Manager.

Owner actions: 'status' (read-only), 'enroll' (interactive local-only secret
storage), 'verify' (read-only single-channel Slack API evidence gate).
This module never changes C40, MCP registrations, tasks, ACLs or databases.

The internal Slack bot is separate from ChatGPT's connected Slack account.
Never pass its xoxb token as an argument, env var, chat, repository file,
MCP parameter, PowerShell history entry or transcript.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import getpass
import json
import os
import ssl
import sys
from urllib import error, parse, request

from . import ucie_admin_history_verdict_v1 as evidence
from . import ucie_slack_history_adapter_v1 as history_adapter

SCHEMA = "UCIE_SLACK_WINDOWS_EVIDENCE_READER_V1"
TARGET = "UCIE:EvidenceReader:SlackBot:v1"
CHANNEL = evidence.CHANNEL
ENDPOINT = "https://slack.com/api/conversations.history"
CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
MAX_TOKEN_BYTES = 2048
MAX_API_BYTES = 2 * 1024 * 1024
MAX_CURSOR_CHARS = 2048
MAX_PAGE_SIZE = 100


class UCIESlackReaderError(ValueError):
    """Sanitized error code; never include token, response body or user data."""


def _windows_cred_api():
    if os.name != "nt":
        raise UCIESlackReaderError("WINDOWS_OWNER_HOST_ONLY")

    class FILETIME(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", wintypes.DWORD),
            ("dwHighDateTime", wintypes.DWORD),
        ]

    class CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    api = ctypes.WinDLL("advapi32", use_last_error=True)
    pointer = ctypes.POINTER(CREDENTIALW)
    api.CredReadW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(pointer),
    ]
    api.CredReadW.restype = wintypes.BOOL
    api.CredWriteW.argtypes = [pointer, wintypes.DWORD]
    api.CredWriteW.restype = wintypes.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    api.CredFree.restype = None
    return api, CREDENTIALW, pointer


def _valid_bot_token(text: str) -> bool:
    if type(text) is not str or not text.startswith("xoxb-"):
        return False
    try:
        raw = text.encode("ascii", "strict")
    except UnicodeError:
        return False
    return 12 <= len(raw) <= MAX_TOKEN_BYTES and all(
        b in b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
        for b in raw
    )


class WindowsCredentialStore:
    """Only fixed UCIE target in the current Windows user's credential set."""

    def read(self) -> str | None:
        api, _, pointer = _windows_cred_api()
        result = pointer()
        if not api.CredReadW(TARGET, CRED_TYPE_GENERIC, 0, ctypes.byref(result)):
            if ctypes.get_last_error() == 1168:  # ERROR_NOT_FOUND
                return None
            raise UCIESlackReaderError("WINCRED_READ_DENIED_OR_FAILED")
        try:
            cred = result.contents
            length = int(cred.CredentialBlobSize)
            if not 0 < length <= MAX_TOKEN_BYTES:
                raise UCIESlackReaderError("WINCRED_BLOB_SIZE_INVALID")
            raw = ctypes.string_at(cred.CredentialBlob, length)
            try:
                secret = raw.decode("ascii", "strict")
            except UnicodeError as exc:
                raise UCIESlackReaderError("WINCRED_TOKEN_ENCODING_INVALID") from exc
            if not _valid_bot_token(secret):
                raise UCIESlackReaderError("WINCRED_TOKEN_TYPE_INVALID")
            return secret
        finally:
            api.CredFree(ctypes.cast(result, ctypes.c_void_p))

    def enroll_new(self, token: str) -> None:
        """Never overwrite existing owner credential automatically."""
        if not _valid_bot_token(token):
            raise UCIESlackReaderError("EXPECTED_XOXB_BOT_TOKEN")
        if self.read() is not None:
            raise UCIESlackReaderError("CREDENTIAL_ALREADY_ENROLLED")
        api, credential_type, _ = _windows_cred_api()
        encoded = bytearray(token.encode("ascii"))
        raw = (ctypes.c_ubyte * len(encoded)).from_buffer(encoded)
        item = credential_type()
        item.Type = CRED_TYPE_GENERIC
        item.TargetName = TARGET
        item.Comment = "UCIE-only Slack Evidence Reader; read-only bot"
        item.UserName = "UCIE Evidence Reader"
        item.CredentialBlobSize = len(encoded)
        item.CredentialBlob = ctypes.cast(raw, ctypes.POINTER(ctypes.c_ubyte))
        item.Persist = CRED_PERSIST_LOCAL_MACHINE
        try:
            if not api.CredWriteW(ctypes.byref(item), 0):
                raise UCIESlackReaderError("WINCRED_WRITE_DENIED_OR_FAILED")
        finally:
            for index in range(len(encoded)):
                encoded[index] = 0
            del raw


class _NoRedirects(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise UCIESlackReaderError("SLACK_HTTP_REDIRECT_DENIED")


def slack_history_http(*, bot_token: str, channel: str,
                       cursor: str | None, limit: int, opener=None) -> dict:
    """One API page. HTTPS direct only, redirects forbidden, no response dumps."""
    if channel != CHANNEL:
        raise UCIESlackReaderError("UCIE_CHANNEL_ONLY")
    if type(limit) is not int or not 1 <= limit <= MAX_PAGE_SIZE:
        raise UCIESlackReaderError("SLACK_PAGE_LIMIT_DENIED")
    if cursor is not None and (
            type(cursor) is not str or not cursor
            or len(cursor) > MAX_CURSOR_CHARS
            or any(ord(c) < 32 for c in cursor)):
        raise UCIESlackReaderError("SLACK_CURSOR_INVALID")
    if not _valid_bot_token(bot_token):
        raise UCIESlackReaderError("SLACK_BOT_TOKEN_MISSING_OR_INVALID")
    params = {"channel": CHANNEL, "limit": str(limit)}
    if cursor is not None:
        params["cursor"] = cursor
    uri = ENDPOINT + "?" + parse.urlencode(params)
    # Do not follow redirects with Authorization. Disable ambient proxies to
    # keep the bot token off unapproved proxy endpoints.
    opener = opener or request.build_opener(
        request.ProxyHandler({}),
        request.HTTPSHandler(context=ssl.create_default_context()),
        _NoRedirects(),
    )
    req = request.Request(
        uri, method="GET",
        headers={
            "Authorization": "Bearer " + bot_token,
            "Accept": "application/json",
            "User-Agent": "UCIE-Evidence-Reader/1.0",
        },
    )
    try:
        with opener.open(req, timeout=12) as response:
            if response.getcode() != 200:
                raise UCIESlackReaderError("SLACK_HTTP_NON_200")
            payload = response.read(MAX_API_BYTES + 1)
    except UCIESlackReaderError:
        raise
    except (error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise UCIESlackReaderError("SLACK_TRANSPORT_UNAVAILABLE") from None
    if len(payload) > MAX_API_BYTES:
        raise UCIESlackReaderError("SLACK_RESPONSE_TOO_LARGE")
    try:
        obj = json.loads(payload.decode("utf-8", "strict"))
    except (UnicodeError, ValueError):
        raise UCIESlackReaderError("SLACK_RESPONSE_NOT_JSON") from None
    if type(obj) is not dict:
        raise UCIESlackReaderError("SLACK_RESPONSE_NOT_OBJECT")
    if obj.get("ok") is not True:
        classification = {
            "missing_scope": "SLACK_MISSING_CHANNELS_HISTORY_SCOPE",
            "not_in_channel": "SLACK_BOT_NOT_IN_UCIE_CHANNEL",
            "channel_not_found": "SLACK_CHANNEL_NOT_ACCESSIBLE",
            "invalid_auth": "SLACK_TOKEN_NOT_AUTHORIZED",
            "token_revoked": "SLACK_TOKEN_REVOKED",
            "ratelimited": "SLACK_RATE_LIMITED",
        }
        code = obj.get("error")
        raise UCIESlackReaderError(classification.get(code, "SLACK_API_ACCESS_DENIED"))
    msgs = obj.get("messages")
    meta = obj.get("response_metadata") or {}
    if type(msgs) is not list or len(msgs) > limit or type(meta) is not dict:
        raise UCIESlackReaderError("SLACK_PAGE_SCHEMA_INVALID")
    next_cursor = meta.get("next_cursor", "")
    more = obj.get("has_more")
    if type(next_cursor) is not str or more is not None and type(more) is not bool:
        raise UCIESlackReaderError("SLACK_PAGE_CURSOR_INVALID")
    return {
        "ok": True, "channel_id": CHANNEL, "messages": msgs,
        "has_more": more,
        "response_metadata": {"next_cursor": next_cursor},
    }


class UCIESlackWindowsReader:
    def __init__(self, *, credential_store=None, page_opener=None):
        self._store = (credential_store if credential_store is not None
                       else WindowsCredentialStore())
        self._page_opener = page_opener
        self.last_error_code = None

    def read_history_page(self, channel: str, cursor: str | None,
                          limit: int) -> dict:
        # Check the fixed target before ever reading the owner's secret.
        if channel != CHANNEL:
            raise UCIESlackReaderError("UCIE_CHANNEL_ONLY")
        token = self._store.read()
        if token is None:
            self.last_error_code = "CREDENTIAL_NOT_ENROLLED"
            raise UCIESlackReaderError(self.last_error_code)
        try:
            return slack_history_http(
                bot_token=token, channel=channel, cursor=cursor, limit=limit,
                opener=self._page_opener,
            )
        except UCIESlackReaderError as exc:
            self.last_error_code = str(exc)
            raise

    def verify_history(self) -> dict:
        """Read-only owner-host E2E; cannot authorize mutating MCP commands."""
        report = history_adapter.history_verdict_from_trusted_reader(
            "ADMIN_DEPLOYMENT_PATH_ABSENT",
            read_history_page=self.read_history_page,
        )
        result = {
            "schema": SCHEMA,
            "status": (
                "UCIE_SLACK_WINDOWS_READ_ONLY_HISTORY_VERIFIED"
                if report.get("reviewed_slack_now") is True else
                "HISTORY_RECHECK_REQUIRED_BLOCK_VERDICT"
            ),
            "credential_stored_in_windows_vault": None,
            "pinned_history_anchors": (
                report.get("review", {}).get("anchors_reconfirmed", [])
                if report.get("reviewed_slack_now") else []
            ),
            "block_code": (
                self.last_error_code or report.get("block_code")
                if not report.get("reviewed_slack_now") else None
            ),
            "server_mcp_runtime_hook_wired": False,
            "new_owner_mcp_tools_enabled": False,
            "operating_database_modified": False,
            "c40_or_scheduled_tasks_modified": False,
            "token_or_raw_messages_exposed": False,
        }
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE Slack Evidence Reader; owner-local only")
    parser.add_argument("action", choices=("status", "enroll", "verify"))
    args = parser.parse_args(argv)
    status = {"schema": SCHEMA, "action": args.action}
    try:
        store = WindowsCredentialStore()
        if args.action == "status":
            token_present = store.read() is not None
            status.update({
                "status": "UCIE_SLACK_TOKEN_PRESENT" if token_present
                          else "UCIE_SLACK_TOKEN_NOT_ENROLLED",
                "token_exposed": False, "remote_slack_call": False,
                "mcp_runtime_hook_wired": False,
            })
            print(json.dumps(status, sort_keys=True))
            return 0
        if args.action == "enroll":
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise UCIESlackReaderError("INTERACTIVE_OWNER_CONSOLE_REQUIRED")
            if store.read() is not None:
                raise UCIESlackReaderError("CREDENTIAL_ALREADY_ENROLLED")
            confirmation = input(
                "Store UCIE-only Slack xoxb token in local Windows Credential Manager? "
                "Type UCIE_SLACK_OWNER_ENROLL: "
            )
            if confirmation != "UCIE_SLACK_OWNER_ENROLL":
                raise UCIESlackReaderError("OWNER_CONFIRMATION_REJECTED")
            token = getpass.getpass(
                "Paste Slack Bot User OAuth Token (hidden, never sent to ChatGPT): "
            )
            try:
                store.enroll_new(token)
            finally:
                token = None
            status.update({
                "status": "UCIE_SLACK_LOCAL_CREDENTIAL_STORED",
                "token_exposed": False, "workspace_permission_verified": False,
                "history_read_verified": False,
            })
            print(json.dumps(status, sort_keys=True))
            return 0
        report = UCIESlackWindowsReader(credential_store=store).verify_history()
        print(json.dumps(report, sort_keys=True))
        return 0 if report["status"] == "UCIE_SLACK_WINDOWS_READ_ONLY_HISTORY_VERIFIED" else 3
    except UCIESlackReaderError as exc:
        status.update({"status":"UCIE_SLACK_READER_FAIL_CLOSED",
                       "block_code":str(exc),
                       "token_exposed":False})
        print(json.dumps(status, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
