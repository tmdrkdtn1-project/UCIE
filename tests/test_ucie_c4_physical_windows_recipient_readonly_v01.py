"""Synthetic C4 physical-bound receiver policy; never claims a real physical device."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sys
import unittest

from ucie_miner import customer_c4_physical_windows_recipient_readonly_v01 as c4
from ucie_miner.customer_staging_v01 import PILLARS


class C4PhysicalRecipientReadOnlyGates(unittest.TestCase):
    def fake_receiver(self,tmp:Path):
        root=tmp/"UCIE_PRIVATE_RECIPIENT"
        slot="0123456789abcdef"
        child=root/"slots"/slot/"venv"/"Scripts"/"python.exe"
        child.parent.mkdir(parents=True)
        child.write_bytes(b"FAKE-STUB-DO-NOT-EXECUTE")
        ui=root/"slots"/slot/"ui"/"UCIE"
        (ui/".git").mkdir(parents=True)
        result={
            "real_ed25519_verified":True,
            "runtime_owner_license_reverified":True,
            "exact_wheel_count":4,
            "customer_distribution_authorized":False,
            "four_pillars_bound":list(PILLARS),
            "active_slot":slot,
            "product_sha256":"a"*64,
            "product_version":"0.1.1",
            "owner_signed_serial":27,
        }
        four={
            "first_party_four_pillars_synthetic_worked":True,
            "pillars_exercised":list(PILLARS),
            "workflow_receipt_sha256":"e"*64,
        }
        local={"verified_local_V04_GET_count":4,"denied_POST":True}
        return root,child,ui,result,four,local

    def run_fake(self,root,child,result,four,local):
        with patch.object(c4.life,"verify_selected",return_value=result):
            with patch.object(c4.life,"_installed_smoke",return_value=(four,local)) as smoke:
                with patch.object(sys,"executable",str(child)):
                    got=c4._verified_installed_local_smoke(
                        root,public_pem=b"SYNTHTETIC PUBLIC ONLY",
                        expected_owner_key_id="c"*32,
                        recipient_token_sha256="a"*64,
                        rights_packet_sha256="b"*64,min_serial=27)
                return got,smoke.call_count

    def test_01_signed_existing_product_pipeline_fields_not_customer_approval(self):
        with TemporaryDirectory() as tmp:
            root,child,ui,result,four,local=self.fake_receiver(Path(tmp))
            got,called=self.run_fake(root,child,result,four,local)
            self.assertEqual(called,1)
            self.assertEqual(got["bound_four_pillars_executed"],4)
            self.assertEqual(got["local_V04_actual_HTTP_200_GETs"],4)
            self.assertFalse(got["approval_owner_hardware_is_independent_proven_cryptographically"])
            self.assertFalse(got["owner_physical_witness_approval_present"])
            self.assertFalse(got["customer_distribution_authorized"])
            self.assertFalse(got["recipient_install_update_rollback_uninstall_executed"])

    def test_02_without_owner_physical_consent_no_access(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/c4.life.RECIPIENT_NAME
            for bad in ("","yes",c4.CONSENT+"bad"):
                with self.subTest(bad=bad),self.assertRaises(ValueError):
                    c4._host_gate(root,consent=bad)
            self.assertFalse(root.exists())

    def test_03_ci_or_nonwindows_cannot_fake_real_machine(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/c4.life.RECIPIENT_NAME
            root.mkdir()
            with patch.object(c4.os,"name","posix"):
                with self.assertRaises(ValueError):
                    c4._host_gate(root,consent=c4.CONSENT)

    def test_04_tampered_or_unverified_c3_entitlement_rejected(self):
        with TemporaryDirectory() as tmp:
            root,child,ui,result,four,local=self.fake_receiver(Path(tmp))
            result["real_ed25519_verified"]=False
            with self.assertRaises(ValueError):
                self.run_fake(root,child,result,four,local)

    def test_05_wrong_runtime_interpreter_denied(self):
        with TemporaryDirectory() as tmp:
            root,child,ui,result,four,local=self.fake_receiver(Path(tmp))
            with patch.object(c4.life,"verify_selected",return_value=result):
                with patch.object(c4.life,"_installed_smoke",
                                  side_effect=AssertionError("must not run untrusted installed smoke")):
                    with self.assertRaises(ValueError):
                        c4._verified_installed_local_smoke(
                            root,public_pem=b"synthetic",expected_owner_key_id="c"*32,
                            recipient_token_sha256="a"*64,
                            rights_packet_sha256="b"*64,min_serial=1)

    def test_06_installed_ui_root_must_have_no_unapproved_customer_data(self):
        with TemporaryDirectory() as tmp:
            root,child,ui,result,four,local=self.fake_receiver(Path(tmp))
            (ui/"customer_notes.txt").write_text("NO USER DATA SHOULD BE READ")
            with self.assertRaises(ValueError):
                self.run_fake(root,child,result,four,local)

    def test_07_unsigned_or_unsafe_active_slot_denied(self):
        with TemporaryDirectory() as tmp:
            root,child,ui,result,four,local=self.fake_receiver(Path(tmp))
            result["active_slot"]="../outside"
            with self.assertRaises(ValueError):
                self.run_fake(root,child,result,four,local)

    def test_08_missing_one_four_pillar_denied(self):
        with TemporaryDirectory() as tmp:
            root,child,ui,result,four,local=self.fake_receiver(Path(tmp))
            four["pillars_exercised"]=list(PILLARS)[:-1]
            with self.assertRaises(ValueError):
                self.run_fake(root,child,result,four,local)

    def test_09_changed_local_ui_denial_detected(self):
        with TemporaryDirectory() as tmp:
            root,child,ui,result,four,local=self.fake_receiver(Path(tmp))
            local["denied_POST"]=False
            with self.assertRaises(ValueError):
                self.run_fake(root,child,result,four,local)

    def test_10_witness_policy_requires_out_of_band_sha_and_serial(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/c4.life.RECIPIENT_NAME
            with patch.object(c4,"_host_gate",return_value=root):
                with patch.object(c4,"_validated_public_key",
                                  side_effect=AssertionError("must not read trust key yet")):
                    with self.assertRaises(ValueError):
                        c4.actual_physical_recipient_readonly(
                            root,public_trust_pem=Path(tmp)/"public.pem",
                            expected_owner_key_id="BAD",
                            recipient_token_sha256="a"*64,
                            rights_packet_sha256="b"*64,min_serial=1,
                            consent=c4.CONSENT)

    def test_11_does_not_claim_physical_acceptance_from_mocked_test(self):
        with TemporaryDirectory() as tmp:
            root,child,ui,result,four,local=self.fake_receiver(Path(tmp))
            got,_=self.run_fake(root,child,result,four,local)
            for key in ("owner_physical_witness_approval_present",
                        "physical_upgrade_rollback_uninstall_accepted",
                        "independent_security_and_legal_clearance_approved",
                        "designated_customer_contract_and_pilot_accepted"):
                self.assertFalse(got[key])

    def test_12_no_changes_to_installed_test_receiver(self):
        with TemporaryDirectory() as tmp:
            root,child,ui,result,four,local=self.fake_receiver(Path(tmp))
            before=sorted(str(p.relative_to(root)) for p in root.rglob("*"))
            self.run_fake(root,child,result,four,local)
            self.assertEqual(before,sorted(str(p.relative_to(root)) for p in root.rglob("*")))


if __name__=="__main__":
    unittest.main()
