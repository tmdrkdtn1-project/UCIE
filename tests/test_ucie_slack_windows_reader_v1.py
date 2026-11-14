"""UCIE Windows Slack bot connection isolated regressions (no real tokens/API)."""
from __future__ import annotations

import io
import json
from unittest import TestCase, mock
from urllib import error

from ucie_miner import ucie_slack_windows_reader_v1 as windows
from ucie_miner import ucie_admin_history_verdict_v1 as history


SYNTHETIC_TOKEN = "xoxb-UCIEsyntheticNotRealBotToken001"
SAMPLES = [
    {
        "ts": "1792896036.978529",
        "text": ("PR #78 UCIE_OWNER_LOCAL_ADMIN_AND_LEGACY_SEARCH_VERIFIED "
                 "관리자 도구 9개"),
    },
    {
        "ts": "1792899889.147509",
        "text": ("UCIE_P10_ONE_PROTECTED_DIRECTORY_CREATED_ACL_RECHECK_ONLY "
                 "UCIE_UnattendedHost protected"),
    },
    {
        "ts": "1792513195.589169",
        "text": "C45 Auth0 ucie:read C41 stdio status",
    },
]


class _Response:
    def __init__(self, obj, code=200):
        self._payload = json.dumps(obj).encode("utf-8")
        self._code = code

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def getcode(self):
        return self._code

    def read(self, count):
        return self._payload[:count]


class _Opener:
    def __init__(self, *, invalid=None, page_count=1):
        self.invalid = invalid
        self.calls = []
        self.page_count = page_count

    def open(self, req, timeout):
        self.calls.append((req.full_url, req.get_header("Authorization"), timeout))
        if self.invalid == "transport":
            raise error.URLError("synthetic transport failure")
        if self.invalid == "missing_scope":
            return _Response({"ok": False, "error": "missing_scope"})
        if self.invalid == "not_in_channel":
            return _Response({"ok": False, "error": "not_in_channel"})
        if self.invalid == "bad_json":
            result = _Response({"ok": True})
            result._payload = b"not-json"
            return result
        if self.invalid == "http500":
            return _Response({},code=500)
        if self.invalid == "large":
            result = _Response({"ok": True})
            result._payload = b"x" * (windows.MAX_API_BYTES+1)
            return result
        # Two-page, valid Slack simulated history.
        if self.page_count == 2 and len(self.calls) == 1:
            return _Response({"ok": True, "messages": SAMPLES[:1],
                              "has_more": True,
                              "response_metadata":{"next_cursor":"token-2"}})
        return _Response({"ok": True,
                          "messages": SAMPLES[1:] if self.page_count == 2 else SAMPLES,
                          "has_more": False,
                          "response_metadata":{"next_cursor":""}})


class _Store:
    def __init__(self, token=SYNTHETIC_TOKEN):
        self.token = token
        self.read_count = 0

    def read(self):
        self.read_count += 1
        return self.token


class UCIENativeSlackWindowsReaderTests(TestCase):
    def test_never_accept_wrong_token_type_or_injection(self):
        for bad in ("", "xapp-token", "xoxp-token", "xoxb-", "xoxb-abc space",
                    "xoxb-invalid\nToken", "xoxb-" + "z"*2050):
            self.assertFalse(windows._valid_bot_token(bad))
        self.assertTrue(windows._valid_bot_token(SYNTHETIC_TOKEN))

    def test_only_exact_ucie_channel_and_fixed_limit(self):
        op = _Opener()
        for channel, cursor, limit in [
            ("C-OTHER",None,100),
            (history.CHANNEL,None,101),
            (history.CHANNEL,None,0),
            (history.CHANNEL,"bad\ncursor",100),
        ]:
            with self.subTest(channel=channel,limit=limit):
                with self.assertRaises(windows.UCIESlackReaderError):
                    windows.slack_history_http(
                        bot_token=SYNTHETIC_TOKEN,channel=channel,
                        cursor=cursor,limit=limit,opener=op)
        self.assertEqual(op.calls, [])

    def test_authorization_header_only_to_single_endpoint(self):
        op = _Opener()
        out=windows.slack_history_http(
            bot_token=SYNTHETIC_TOKEN,channel=history.CHANNEL,
            cursor=None,limit=100,opener=op)
        self.assertEqual(len(out["messages"]),3)
        self.assertEqual(len(op.calls),1)
        self.assertTrue(op.calls[0][0].startswith(windows.ENDPOINT+"?"))
        self.assertNotIn(SYNTHETIC_TOKEN,op.calls[0][0])
        self.assertEqual(op.calls[0][1], "Bearer "+SYNTHETIC_TOKEN)
        self.assertEqual(op.calls[0][2], 12)

    def test_access_failures_are_sanitized_not_returned_as_messages(self):
        for name in ("missing_scope","not_in_channel","bad_json",
                     "http500","transport","large"):
            op=_Opener(invalid=name)
            with self.subTest(name=name):
                with self.assertRaises(windows.UCIESlackReaderError) as ctx:
                    windows.slack_history_http(
                        bot_token=SYNTHETIC_TOKEN,channel=history.CHANNEL,
                        cursor=None,limit=100,opener=op)
                self.assertNotIn(SYNTHETIC_TOKEN,str(ctx.exception))
                self.assertNotIn("synthetic transport failure",str(ctx.exception))

    def test_empty_owner_vault_blocks_without_network(self):
        opener=_Opener()
        reader=windows.UCIESlackWindowsReader(
            credential_store=_Store(None),page_opener=opener)
        result=reader.verify_history()
        self.assertEqual(result["status"],"HISTORY_RECHECK_REQUIRED_BLOCK_VERDICT")
        self.assertEqual(result["block_code"],"CREDENTIAL_NOT_ENROLLED")
        self.assertFalse(result["token_or_raw_messages_exposed"])
        self.assertEqual(opener.calls,[])

    def test_2page_history_end_to_end_3_anchors_no_write(self):
        op=_Opener(page_count=2)
        store=_Store()
        reader=windows.UCIESlackWindowsReader(
            credential_store=store,page_opener=op)
        result=reader.verify_history()
        self.assertEqual(result["status"],
                         "UCIE_SLACK_WINDOWS_READ_ONLY_HISTORY_VERIFIED")
        self.assertEqual(len(result["pinned_history_anchors"]),3)
        self.assertEqual(len(op.calls),2)
        self.assertFalse(result["server_mcp_runtime_hook_wired"])
        self.assertFalse(result["new_owner_mcp_tools_enabled"])
        self.assertFalse(result["operating_database_modified"])
        self.assertNotIn(SYNTHETIC_TOKEN,str(result))
        self.assertEqual(store.read_count,2)

    def test_wrong_channel_precedes_secret_read(self):
        store=_Store()
        reader=windows.UCIESlackWindowsReader(credential_store=store)
        with self.assertRaises(windows.UCIESlackReaderError):
            reader.read_history_page("C_OTHER",None,100)
        self.assertEqual(store.read_count,0)

    def test_no_username_or_token_emitted_in_status_with_mock_vault(self):
        with mock.patch.object(windows,"WindowsCredentialStore",return_value=_Store()):
            buffer=io.StringIO()
            with mock.patch("sys.stdout",buffer):
                ret=windows.main(["status"])
            output=buffer.getvalue()
        self.assertEqual(ret,0)
        self.assertIn("UCIE_SLACK_TOKEN_PRESENT",output)
        self.assertNotIn(SYNTHETIC_TOKEN,output)

    def test_cli_verify_fail_closed_if_bot_not_invited(self):
        op=_Opener(invalid="not_in_channel")
        reader=windows.UCIESlackWindowsReader(credential_store=_Store(),page_opener=op)
        out=reader.verify_history()
        self.assertEqual(out["status"],"HISTORY_RECHECK_REQUIRED_BLOCK_VERDICT")
        self.assertEqual(out["block_code"],"SLACK_BOT_NOT_IN_UCIE_CHANNEL")
        self.assertEqual(out["pinned_history_anchors"],[])

    def test_cli_enroll_refuses_noninteractive_and_does_not_prompt(self):
        with mock.patch.object(windows,"WindowsCredentialStore",return_value=_Store(None)):
            with mock.patch("sys.stdin",new=io.StringIO("")):
                buf=io.StringIO()
                with mock.patch("sys.stdout",buf):
                    out=windows.main(["enroll"])
        self.assertEqual(out,3)
        self.assertIn("INTERACTIVE_OWNER_CONSOLE_REQUIRED",buf.getvalue())

    def test_ssl_http_redirects_denied(self):
        handler=windows._NoRedirects()
        with self.assertRaises(windows.UCIESlackReaderError):
            handler.redirect_request(None,None,302,"move",{},"http://example.org")

    def test_owner_api_is_not_mcp_tool_and_has_no_mutating_side_effects(self):
        import inspect
        body=inspect.getsource(windows)
        for forbidden in ("@server.tool", "setenv(", "os.environ[",
                          "Start-ScheduledTask", "D:\\OFFICE_AGENT"):
            self.assertNotIn(forbidden,body)
        self.assertIn("CredReadW",body)
        self.assertIn("CredWriteW",body)


if __name__=="__main__":
    import unittest
    unittest.main()
