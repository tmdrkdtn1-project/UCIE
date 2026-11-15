"""One approved UCIE public 403 diagnostic GET: synthetic only.

Real owner root is only PREVIEWED, never a public GET, queue action,
scheduler change, credential access or automatic rule approval.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
import json
import os
import unittest

from ucie_miner import public_owner_one_403_probe_v01 as probe
from ucie_miner import worker

ROOT=Path(__file__).resolve().parents[1]
T0=datetime(2026,11,15,11,0,tzinfo=timezone.utc)
POISON="UNTRUSTED_403_API_BODY_DO_NOT_STORE_9945"


class One403OwnerProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(prefix="UCIE_403_OWNER_SYNTH_")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"UCIE"
        (self.root/"runtime").mkdir(parents=True)
        (self.root/"runtime"/"UCIE_PUBLIC_403_PROBE_SYNTH_ONLY.marker"
         ).write_text(probe.SYNTH_MARKER,encoding="ascii")
        self._last_at(T0-timedelta(minutes=75))

    def _last_at(self,when):
        payload={
            "schema":"UCIE_MINER_CYCLE_V1","status":"COLLECTION_FAILED",
            "finished_utc":when.isoformat(),"error_http_status":403,
            "error_public_source":"python/cpython",
            "error_public_operation":"FETCH_PR_LIST",
            "consecutive_failures":1,"production_approved":False,
        }
        (self.root/"runtime"/"last_run.json").write_text(
            json.dumps(payload),encoding="utf-8")

    def _preview(self,now=T0):
        return probe.preview(self.root,now=now)

    def _apply(self,fetch,now=T0,fingerprint=None):
        return probe.apply_one(
            self.root,
            expected_sha256=(self._preview(now)["original_receipt_sha256"]
                             if fingerprint is None else fingerprint),
            consent=probe.CONSENT,now=now,fetch=fetch)

    def _receipt(self):
        return json.loads((self.root/"runtime"/probe.PROBE_NAME).read_text(
            encoding="ascii"))

    def test_01_preview_is_zero_get_and_no_new_receipt(self):
        before=(self.root/"runtime"/"last_run.json").read_bytes()
        r=self._preview()
        self.assertEqual(r["status"],
                         "EXACT_ONE_403_OWNER_DIAGNOSTIC_PREVIEW_ONLY")
        self.assertEqual(r["approved_source"],"python/cpython")
        self.assertEqual(r["maximum_approved_gets"],1)
        self.assertTrue(r["unknown_shared_rate_budget"])
        self.assertEqual(r["public_gets_requested"],0)
        self.assertFalse((self.root/"runtime"/probe.PROBE_NAME).exists())
        self.assertEqual((self.root/"runtime"/"last_run.json").read_bytes(),before)

    def test_02_only_one_success_then_replay_denied(self):
        called=[]
        def fake(url):
            called.append(url)
            return []
        original=(self.root/"runtime"/"last_run.json").read_bytes()
        r=self._apply(fake)
        self.assertEqual(r["status"],
                         "EXACT_ONE_403_DIAGNOSTIC_SUCCEEDED_UNVERIFIED")
        self.assertEqual(r["public_gets_requested"],1)
        self.assertEqual(r["source_id"],"repo:python/cpython")
        self.assertEqual(len(called),1)
        self.assertEqual(self._receipt()["state"],"SUCCESS")
        self.assertEqual(self._receipt()["public_gets_requested"],1)
        self.assertEqual(original,(self.root/"runtime"/"last_run.json").read_bytes())
        with self.assertRaises(probe.One403Error):
            self._apply(lambda _:self.fail("no second request permitted"))

    def test_03_real_http403_rate_reset_is_sanitized(self):
        e=HTTPError("https://invalid.test/"+POISON,403,
                    "NO "+POISON,{
                        "X-RateLimit-Remaining":"0",
                        "X-RateLimit-Reset":
                            str(int((T0+timedelta(minutes=60)).timestamp())),
                        "Retry-After":"120"
                    },None)
        self.addCleanup(e.close)
        r=self._apply(lambda _url:(_ for _ in ()).throw(e))
        self.assertEqual(r["status"],"EXACT_ONE_403_DIAGNOSTIC_FAILED_NO_RETRY")
        self.assertEqual(r["sanitized_error_category"],"UPSTREAM_HTTP_403")
        self.assertEqual(r["rate_remaining"],0)
        self.assertEqual(r["rate_hold_reason"],"HTTP_403_RETRY_AFTER")
        self.assertEqual(self._receipt()["state"],"FAILED")
        self.assertNotIn(POISON.encode(),
                         (self.root/"runtime"/probe.PROBE_NAME).read_bytes())

    def test_04_deny_too_early_wrong_fingerprint_and_miner_lock(self):
        self._last_at(T0-timedelta(minutes=25))
        with self.assertRaises(probe.One403Error):
            self._apply(lambda _:self.fail("too early GET"))
        self._last_at(T0-timedelta(minutes=75))
        with self.assertRaises(probe.One403Error):
            self._apply(lambda _:self.fail("bad SHA GET"),fingerprint="a"*64)
        with worker._single_instance(self.root/"runtime") as acquired:
            self.assertTrue(acquired)
            with self.assertRaises(probe.One403Error):
                self._apply(lambda _:self.fail("concurrent miner GET"))
        self.assertFalse((self.root/"runtime"/probe.PROBE_NAME).exists())

    def test_05_http429_cause_does_not_replay(self):
        e=HTTPError("https://invalid.test",429,"NO",{},None)
        self.addCleanup(e.close)
        r=self._apply(lambda _url:(_ for _ in ()).throw(e))
        self.assertEqual(r["sanitized_error_category"],"UPSTREAM_HTTP_429")
        self.assertEqual(r["rate_hold_reason"],"HTTP_429_EXPONENTIAL_FALLBACK")
        with self.assertRaises(probe.One403Error):
            self._preview()

    def test_06_exact_upstream_source_operation_is_mandatory(self):
        path=self.root/"runtime"/"last_run.json"
        original=json.loads(path.read_text(encoding="utf-8"))
        for change in (
            {"error_public_source":"unapproved/repo"},
            {"error_public_operation":"FETCH_PR_FILES"},
            {"error_http_status":429},
            {"status":"COLLECTED_UNVERIFIED"}
        ):
            copy={**original,**change}
            path.write_text(json.dumps(copy),encoding="utf-8")
            with self.assertRaises(probe.One403Error):
                self._preview()
        path.write_text(json.dumps(original),encoding="utf-8")
        self.assertEqual(self._preview()["approved_source"],"python/cpython")

    @unittest.skipUnless(os.name=="nt","exact owner Windows only")
    def test_07_real_owner_readonly_no_network(self):
        if ROOT.resolve()!=Path("D:/UCIE").resolve() or ROOT.is_symlink():
            self.skipTest("owner checkout absent")
        before=(ROOT/"runtime"/"last_run.json").read_bytes()
        try:
            x=probe.preview(ROOT)
            outcome=x["status"]
            one_get_eligible=True
        except probe.One403Error:
            outcome="OWNER_ONE_403_PROBE_PREVIEW_FAIL_CLOSED_NO_GET"
            one_get_eligible=False
        self.assertEqual(before,(ROOT/"runtime"/"last_run.json").read_bytes())
        print("UCIE_403_OWNER_PROBE_READONLY="+json.dumps({
            "schema":probe.SCHEMA,
            "status":outcome,
            "one_get_eligible":one_get_eligible,
            "public_gets_requested":0,
            "task_modified":False,
        },sort_keys=True))


if __name__=="__main__":
    unittest.main()
