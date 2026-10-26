"""Focused offline tests for the fifth manual owner addendum, no host keys.

No real GitHub requests, production release, public source execution, owner
key reads, automatic consent, scheduler or private project access.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from test_ucie_owner_risk_release import RUN, SHA, fake_api
from ucie_public.policy import PolicyError
from ucie_public.rulepack import generate_keys, canonical_json, _private_key
from ucie_public.fifth_owner_addendum import (
    BASE_SOURCE_SHA, CONFIRM, RISK, RULE_ID,
    _parent, publish_fifth_addendum, verify_fifth_addendum,
    scan_fifth_addendum,
)

SOURCE = """\
class Loop:
    async def connect_read_pipe(self, protocol_factory, pipe):
        protocol = protocol_factory()
        waiter = self.create_future()
        transport = self._make_read_pipe_transport(pipe, protocol, waiter)
        return transport
"""


class FifthAddendumTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "build").mkdir()
        self.owner_private, self.trust = generate_keys(
            self.root / "owner-key", purpose="production")
        self.base_pack = self.root / "serial4-synthetic.zip"
        self.base_pack.write_bytes(b"UCIE synthetic parent fixture, not real signed")
        self.pack = self.root / "build" / "fifth-serial5.zip"
        self.run, self.jobs = fake_api()

    def _publish(self, **kw):
        args = dict(run_id=RUN, serial=5, confirmation=CONFIRM,
                    risk_acceptance=RISK)
        args.update(kw)
        with (patch("ucie_public.fifth_owner_addendum._parent",
                    return_value=("a" * 64, {"serial": 4})),
              patch("ucie_public.fifth_owner_addendum._local_clean_sha",
                    return_value=SHA),
              patch("ucie_public.owner_release._public_json",
                    side_effect=[self.run, self.jobs])):
            return publish_fifth_addendum(
                self.root, self.owner_private, self.base_pack,
                self.trust, self.pack, **args)

    def _verify(self, **kw):
        with patch("ucie_public.fifth_owner_addendum._parent",
                   return_value=("a" * 64, {"serial": 4})):
            return verify_fifth_addendum(
                self.pack, self.base_pack, self.trust, **kw)

    def test_sign_verify_and_one_inert_candidate(self):
        self._publish()
        verified = self._verify()
        self.assertEqual(verified["result"],
                         "FIFTH_OWNER_RISK_ADDENDUM_VERIFIED")
        self.assertEqual(verified["serial"], 5)
        self.assertEqual(verified["parent_serial"], 4)
        self.assertEqual(verified["additional_signed_rules"], 1)
        self.assertEqual(verified["rule_id"], RULE_ID)
        self.assertEqual(verified["owner_signature"], "VALID")
        self.assertFalse(verified["auto_apply"])
        self.assertFalse(verified["independent_human_qa_approved"])
        with patch("ucie_public.fifth_owner_addendum._parent",
                   return_value=("a" * 64, {"serial": 4})):
            observed = scan_fifth_addendum(
                self.pack, self.base_pack, self.trust, SOURCE)
        self.assertEqual(observed["finding_count"], 1)
        self.assertFalse(observed["source_executed"])
        self.assertEqual(observed["persistent_writes"], 0)
        self.assertFalse(observed["runtime_bug_confirmed_for_input"])

    def test_requires_fresh_owner_consent_before_private_key(self):
        for change in (
            {"confirmation": "AUTOMATIC"},
            {"risk_acceptance": "YES"},
            {"serial": 4},
        ):
            with self.subTest(change=change), self.assertRaises(PolicyError):
                self._publish(**change)
        self.assertFalse(self.pack.exists())

    def test_bad_live_ci_and_key_mismatch_fail_closed(self):
        self.run["status"] = "in_progress"
        with self.assertRaises(PolicyError):
            self._publish()
        self.assertFalse(self.pack.exists())
        self.run, self.jobs = fake_api()
        _, other_trust = generate_keys(
            self.root / "other-owner", purpose="production")
        with (patch("ucie_public.fifth_owner_addendum._parent",
                    return_value=("a" * 64, {"serial": 4})),
              patch("ucie_public.fifth_owner_addendum._local_clean_sha",
                    return_value=SHA),
              patch("ucie_public.owner_release._public_json",
                    side_effect=[self.run, self.jobs])):
            with self.assertRaises(PolicyError):
                publish_fifth_addendum(
                    self.root, self.owner_private, self.base_pack,
                    other_trust, self.pack, run_id=RUN, serial=5,
                    confirmation=CONFIRM, risk_acceptance=RISK)
        self.assertFalse(self.pack.exists())

    def test_no_overwrite_and_signed_manifest_integrity(self):
        self._publish()
        with self.assertRaises(PolicyError):
            self._publish()
        with zipfile.ZipFile(self.pack) as original:
            blobs = {name: original.read(name) for name in original.namelist()}
        man = json.loads(blobs["manifest.json"])
        man["parent_pack_sha256"] = "f" * 64
        blobs["manifest.json"] = canonical_json(man)
        tamper = self.root / "build" / "altered.zip"
        with zipfile.ZipFile(tamper, "w", zipfile.ZIP_DEFLATED) as z:
            for name, raw in blobs.items():
                z.writestr(name, raw)
        with patch("ucie_public.fifth_owner_addendum._parent",
                   return_value=("a" * 64, {"serial": 4})):
            with self.assertRaises(PolicyError):
                verify_fifth_addendum(tamper, self.base_pack, self.trust)

    def test_invalid_time_and_parent_hash_fail_closed(self):
        self._publish()
        past = datetime.now(timezone.utc) + timedelta(days=8)
        with self.assertRaises(PolicyError):
            self._verify(at_time=past)
        with patch("ucie_public.fifth_owner_addendum._parent",
                   return_value=("b" * 64, {"serial": 4})):
            with self.assertRaises(PolicyError):
                verify_fifth_addendum(self.pack, self.base_pack, self.trust)
        with self.assertRaises(PolicyError):
            self._verify(min_serial=6)

    def test_parent_must_be_exact_signed_four_rule_source(self):
        parent = {
            "owner_signature": "VALID", "serial": 4,
            "rule_ids": [
                "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO",
                "PS_RESOLVE_PATH_DOT_PREFIX",
                "PS_FUZZY_GET_COMMAND_DUPLICATES",
                "PY_SCANDIR_SHARED_ITERATOR_RACE",
            ],
            "rule_count": 4, "source_commit_sha": BASE_SOURCE_SHA,
            "auto_apply": False,
        }
        with patch("ucie_public.fifth_owner_addendum.verify_mixed_owner_release",
                   return_value=parent):
            digest, original = _parent(self.base_pack, self.trust)
        self.assertEqual(len(digest), 64)
        self.assertEqual(original["serial"], 4)
        for altered in ({"serial": 3},
                        {"source_commit_sha": "b" * 40},
                        {"auto_apply": True}):
            with patch(
                "ucie_public.fifth_owner_addendum.verify_mixed_owner_release",
                return_value={**parent, **altered},
            ):
                with self.assertRaises(PolicyError):
                    _parent(self.base_pack, self.trust)


if __name__ == "__main__":
    unittest.main()
