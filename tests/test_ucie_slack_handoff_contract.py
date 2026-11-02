"""UCIE-only static regression: keep new-room handoff discoverable.

This checks structure of repository guidance and one current checkpoint.
It does not post to Slack, observe the operator Windows host, or verify
third-party apps. It is not evidence of an accepted receiver handoff.
"""
from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROTO = "docs/UCIE_SLACK_HANDOFF_PROTOCOL_V1_20261102.md"
CURRENT = "docs/UCIE_HANDOFF_CURRENT.md"
REQUIRED = (
    "PROJECT", "HANDOFF_ID", "FROM_WORKROOM", "TO_WORKROOM",
    "STATUS", "BASE_MAIN_SHA", "DECISION_DOC", "ACTIVE_PRS",
    "CI_STATE", "OWNER_HOST_STATE", "APPROVAL_STATE",
    "RELEASE_STATE", "SLACK_POST_STATE", "ACK_STATE",
    "NEXT_OWNER", "NEXT_ACTION", "ACCEPTANCE", "NO_GO",
    "PREVIOUS_SLACK", "CURRENT_SLACK",
)


class UCIESlackHandoffDocumentationTests(unittest.TestCase):
    def test_agents_discovery_always_points_to_handoff(self):
        content = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn(PROTO, content)
        self.assertIn(CURRENT, content)
        self.assertIn("HANDOFF_SENT", content)
        self.assertIn("HANDOFF_RECEIVED", content)

    def test_handoff_protocol_explicitly_separates_receipts(self):
        content = (ROOT / PROTO).read_text(encoding="utf-8")
        for required in (
            "HANDOFF_REQUIRED", "DECISION_LOCKED", "GATE_CHANGED",
            "BLOCKER_NEW_OR_RESOLVED", "CORRECTION_OR_RETRACTION",
            "HANDOFF_RECEIVED", "SLACK_POST_PENDING",
            "ACK_STATE=NOT_RECEIVED", "CI_PASS", "OWNER_HOST_OBSERVED",
        ):
            with self.subTest(required=required):
                self.assertIn(required, content)

    def test_current_checkpoint_has_dedicated_fields_and_ucie_only_scope(self):
        text = (ROOT / CURRENT).read_text(encoding="utf-8")
        mapping = dict(
            line.split("=", 1) for line in text.splitlines()
            if line.startswith(tuple(x + "=" for x in REQUIRED))
        )
        self.assertEqual(set(mapping), set(REQUIRED))
        self.assertEqual(mapping["PROJECT"], "UCIE")
        self.assertTrue(mapping["HANDOFF_ID"].startswith("UCIE-HO-"))
        self.assertTrue(mapping["BASE_MAIN_SHA"])
        self.assertIn("UCIE", mapping["NEXT_OWNER"])
        self.assertIn("UCIE", mapping["TO_WORKROOM"])
        self.assertTrue(mapping["NEXT_ACTION"].strip())
        self.assertTrue(mapping["ACCEPTANCE"].strip())
        self.assertTrue(mapping["NO_GO"].strip())
        if mapping["ACK_STATE"] == "NOT_RECEIVED":
            self.assertNotIn("RECEIVED", mapping["STATUS"].replace("NOT_RECEIVED", ""))

    def test_status_claims_not_promoted_by_document_presence(self):
        proto = (ROOT / PROTO).read_text(encoding="utf-8")
        self.assertIn("ChatGPT 새 채팅이 자동으로 이 문서를 읽거나 Slack에 쓰는 것은 보장되지 않음", proto)
        self.assertIn("실제 permalink", proto)
        self.assertIn("다른 프로젝트", proto)


if __name__ == "__main__":
    unittest.main()
