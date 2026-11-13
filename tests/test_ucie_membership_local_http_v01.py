"""Real local HTTP routes must enforce signed membership on EACH request.

All keys and data here are synthetic in-memory; product C3 verify_selected
is stubbed only in THIS isolated test, while membership Ed25519 is genuine.
Actual 4-wheel installed native Windows CI executes the same suite with the
verified installed cryptography wheel, zero skips required.
"""
from __future__ import annotations

from datetime import datetime,timezone
from hashlib import sha256
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch
from urllib.parse import urlsplit
import calendar
import json
import sys
import time
import unittest

from ucie_miner import customer_private_offline_lifecycle_v01 as life
from ucie_miner import customer_membership_recipient_v01 as rec
from ucie_miner import customer_membership_subscription_v01 as mem
from ucie_miner import customer_private_entitlement_v01 as product
from ucie_miner import local_public_pr_owner_auth_v01 as auth
from ucie_miner import local_v1_app_v01 as app


class SignedMembershipRealLoopbackHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
            from ucie_public.rulepack import key_id
        except ImportError:
            raise unittest.SkipTest("native real Ed25519 missing")
        cls.private=Ed25519PrivateKey.generate()
        cls.public=cls.private.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        cls.owner_id=key_id(cls.private.public_key())
        cls.account=sha256(b"UCIE synthetic HTTP member only").hexdigest()
        cls.subid=sha256(b"UCIE synthetic HTTP subscription only").hexdigest()
        cls.rights="c"*64
        cls.now=datetime.now(timezone.utc).replace(microsecond=0)
        cls.start=cls.now.replace(day=1,hour=0,minute=0,second=0)
        cls.end=mem._period_end(cls.start,"monthly")

    def snapshot(self,seq=1,status="ACTIVE",plan="complete"):
        row={
            "schema":mem.SCHEMA,"scope":mem.SCOPE,"service":"UCIE",
            "subscription_id_sha256":self.subid,
            "recipient_token_sha256":self.account,
            "rights_packet_sha256":self.rights,
            "owner_key_id":self.owner_id,
            "plan":plan,"billing_interval":"monthly",
            "billing_status":status,
            "payment_receipt_sha256":"d"*64,
            "renewal_sequence":seq,
            "product_entitlement_min_serial":8,
            "issued_utc":auth._stamp(self.start),
            "period_start_utc":auth._stamp(self.start),
            "period_end_utc":auth._stamp(self.end),
            "grace_until_utc":auth._stamp(self.end),
        }
        raw=product.canonical(row)
        return raw,mem._sig(raw,self.private,
                consent="OWNER_SIGN_UCIE_MEMBERSHIP_EXISTING_KEY_ONCE")

    def params(self):
        return dict(public_pem=self.public,expected_owner_key_id=self.owner_id,
            expected_recipient_token_sha256=self.account,
            expected_rights_packet_sha256=self.rights,
            expected_subscription_id_sha256=self.subid,
            min_product_serial=8,min_renewal_sequence=1)

    def mocked_product(self):
        return {"owner_signed_serial":8,"active_slot":"0123456789abcdef",
            "customer_distribution_authorized":False}

    def receiver(self,base:Path):
        root=base/"UCIE_PRIVATE_RECIPIENT"
        child=root/"slots"/"0123456789abcdef"/"venv"/"Scripts"/"python.exe"
        child.parent.mkdir(parents=True)
        child.write_bytes(b"UCIE_FAKE_INSTALLED_INTERPRETER_NOT_EXECUTED")
        ui=root/"slots"/"0123456789abcdef"/"ui"/"UCIE"
        (ui/".git").mkdir(parents=True)
        return root,child

    def import_snapshot(self,root,seq=1,status="ACTIVE",plan="complete"):
        a,b=self.snapshot(seq=seq,status=status,plan=plan)
        with patch.object(life,"verify_selected",return_value=self.mocked_product()):
            return rec.import_owner_signed_membership(
                root,a,b,consent=rec.CONSENT,**self.params())

    def perform_http(self,root,child,actions):
        original_server=app.LOCAL_SERVER_CLASS
        servers=[]
        failures=[]
        def server_factory(addr,handler):
            server=original_server(addr,handler)
            servers.append(server)
            return server
        def process():
            try:
                with patch.object(sys,"executable",str(child)):
                    life.serve_selected(root,public_pem=self.public,
                        expected_owner_key_id=self.owner_id,
                        expected_recipient_token_sha256=self.account,
                        expected_rights_packet_sha256=self.rights,
                        min_serial=8,
                        expected_subscription_id_sha256=self.subid,
                        min_membership_sequence=1,port=0)
            except Exception as exc:
                failures.append(type(exc).__name__)
        with patch.object(life,"verify_selected",return_value=self.mocked_product()):
            with patch.object(app,"LOCAL_SERVER_CLASS",side_effect=server_factory):
                t=Thread(target=process,daemon=True)
                t.start()
                try:
                    deadline=time.monotonic()+7
                    while not servers and not failures and time.monotonic()<deadline:
                        time.sleep(0.01)
                    if not servers:
                        raise AssertionError("signed membership server did not launch: "+str(failures))
                    s=servers[0]
                    values=[]
                    for method,route in actions:
                        conn=HTTPConnection("127.0.0.1",s.server_port,timeout=5)
                        try:
                            conn.request(method,route)
                            response=conn.getresponse()
                            body=response.read(4096)
                            values.append((response.status,body))
                        finally:
                            conn.close()
                    return values
                finally:
                    if servers:
                        servers[0].shutdown()
                    t.join(timeout=7)
                    if t.is_alive():
                        raise AssertionError("membership local HTTP worker leaked")
                    if failures:
                        raise AssertionError("signed membership local handler failed: "+str(failures))

    def test_01_current_signed_complete_membership_routes_active(self):
        with TemporaryDirectory() as tmp:
            root,child=self.receiver(Path(tmp))
            self.import_snapshot(root)
            results=self.perform_http(root,child,[
                ("GET","/local"),("GET","/local/health"),
                ("GET","/local/library?q=Python"),
                ("GET","/local/evolution?q=Python"),
                ("POST","/local")])
            self.assertEqual([a for a,b in results],[200,200,200,200,405])
            h=json.loads(results[1][1])
            self.assertTrue(h["membership_signature_reverified_per_request"])
            self.assertEqual(h["membership_plan"],"complete")

    def test_02_standard_blocks_direct_engine_evolution_deep_links(self):
        with TemporaryDirectory() as tmp:
            root,child=self.receiver(Path(tmp))
            self.import_snapshot(root,plan="standard")
            results=self.perform_http(root,child,[
                ("GET","/local/library"),("GET","/local/error"),
                ("GET","/local/engine?purpose=B2_CONNECTED_TRIAGE"),
                ("GET","/local/evolution?q=Git")])
            self.assertEqual([x[0] for x in results],[200,200,403,403])

    def test_03_explicit_signed_revocation_blocks_all_app_routes(self):
        with TemporaryDirectory() as tmp:
            root,child=self.receiver(Path(tmp))
            self.import_snapshot(root,status="REVOKED")
            results=self.perform_http(root,child,[("GET","/local"),("GET","/local/library")])
            self.assertEqual([x[0] for x in results],[403,403])

    def test_04_cancel_at_period_end_still_allows_paid_period(self):
        with TemporaryDirectory() as tmp:
            root,child=self.receiver(Path(tmp))
            self.import_snapshot(root,status="CANCEL_AT_PERIOD_END")
            result=self.perform_http(root,child,[("GET","/local/library")])
            self.assertEqual(result[0][0],200)

    def test_05_no_active_signed_subscription_refuses_http_start(self):
        with TemporaryDirectory() as tmp:
            root,child=self.receiver(Path(tmp))
            with patch.object(life,"verify_selected",return_value=self.mocked_product()):
                with patch.object(sys,"executable",str(child)):
                    with self.assertRaises(ValueError):
                        life.serve_selected(root,public_pem=self.public,
                            expected_owner_key_id=self.owner_id,
                            expected_recipient_token_sha256=self.account,
                            expected_rights_packet_sha256=self.rights,
                            expected_subscription_id_sha256=self.subid,
                            min_membership_sequence=1,min_serial=8,port=0)

    def test_06_launcher_without_membership_args_cannot_start(self):
        self.assertIn("$ExpectedSubscriptionIdSha256",life.LAUNCHER)
        self.assertIn("$MinMembershipSequence",life.LAUNCHER)
        with self.assertRaises(ValueError):
            life.serve_selected(
                Path("D:/UCIE_PRIVATE_RECIPIENT"),
                public_pem=self.public,expected_owner_key_id=self.owner_id,
                expected_recipient_token_sha256=self.account,
                expected_rights_packet_sha256=self.rights,min_serial=8,
                expected_subscription_id_sha256=None,
                min_membership_sequence=0)

    def test_07_signed_token_can_be_replaced_without_reinstalling_product(self):
        with TemporaryDirectory() as tmp:
            root,child=self.receiver(Path(tmp))
            self.import_snapshot(root,plan="standard")
            first=self.perform_http(root,child,[("GET","/local/engine")])[0][0]
            self.import_snapshot(root,seq=2,plan="complete")
            second=self.perform_http(root,child,[("GET","/local/engine")])[0][0]
            self.assertEqual((first,second),(403,200))


if __name__=="__main__":
    unittest.main()
