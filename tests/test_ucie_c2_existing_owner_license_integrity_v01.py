"""UCIE: synthetic fake local license packet, never actual copyrighted text."""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from ucie_miner import customer_c2_existing_owner_license_integrity_v01 as review
from ucie_miner import customer_c2_owner_license_review_packet_v01 as original
from ucie_miner.customer_owner_wheelhouse_acquire_v01 import PINNED


class ExistingOwnerC2FiveLicenseTextAuditTests(unittest.TestCase):
    def build(self,home:Path):
        folder=home/"UCIE"/"downloaded"/review.FOLDER
        folder.mkdir(parents=True)
        assigned={"cryptography":["LICENSE.APACHE","LICENSE.BSD"],
                  "cffi":["LICENSE","COPYING"],"pycparser":["LICENSE"]}
        entries=[]
        total=0
        for name,version in sorted(PINNED):
            files=[]
            for number,filename in enumerate(assigned[name]):
                rel=f"license-text/{name}-{version}/{filename}"
                raw=(name+version+filename+" UCIE SYNTHETIC REVIEW, NOT A REAL LICENSE\n").encode()
                child=folder.joinpath(*rel.split("/"))
                child.parent.mkdir(parents=True,exist_ok=True)
                child.write_bytes(raw)
                files.append({
                    "relative_review_path":rel,
                    "sha256":sha256(raw).hexdigest(),"bytes":len(raw),
                    "human_rights_reviewed":False,
                    "notice_obligations_approved":False,
                })
                total+=len(raw)
            entries.append({
                "distribution":name,"version":version,
                "wheel_sha256":sha256(name.encode()).hexdigest(),
                "vendor_license_reviewed":False,
                "redistribution_and_commercial_rights_approved":False,
                "NOTICE_absence_does_not_prove_obligations_absent":True,
                "observed_notice_under_dist_info_licenses_count":0,
                "declared_license_texts":files,
            })
        packed=json.dumps(entries,sort_keys=True,ensure_ascii=True,
                          separators=(",",":")).encode("ascii")
        pin=sha256(packed).hexdigest()
        manifest={
            "schema":original.SCHEMA,
            "status":original.STATUS,
            "source":"EXISTING_UCIE_C1_SHA_LOCKED_WINDOWS_315_LOCAL_WHEELHOUSE",
            "target":"WIN_AMD64_PY315_ONLY",
            "parent_c2_evidence_sha256":"f"*64,
            "review_entries_sha256":pin,
            "reviewed_packages":entries,
            "license_file_count":5,"license_total_bytes":total,
            "reviewer_approval":False,
            "legal_redist_clearance":False,
            "security_clearance":False,
            "all_customer_release_gates_passed":False,
            "customer_distribution_authorized":False,
        }
        (folder/"review_manifest.json").write_text(
            json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="ascii")
        (folder/"README_KO.md").write_text("UCIE SYNTHETIC LOCAL REVIEW ONLY",encoding="utf-8")
        return folder,pin,manifest

    def test_01_five_existing_exact_bytes_validated_without_approval(self):
        with TemporaryDirectory() as tmp:
            folder,pin,_=self.build(Path(tmp))
            result=review.verify_existing_owner_license_texts(
                folder,expected_review_entries_sha256=pin)
            self.assertEqual(result["exact_existing_licenses_files_sha_verified"],5)
            self.assertEqual(len(result["source_pkgs"]),3)
            self.assertEqual(sum(x["declared_texts_sha_verified"] for x in result["source_pkgs"]),5)
            self.assertFalse(result["actual_human_license_notice_review_completed"])
            self.assertFalse(result["customer_distribution_authorized"])

    def test_02_wrong_out_of_band_owner_sha_denied(self):
        with TemporaryDirectory() as tmp:
            folder,pin,_=self.build(Path(tmp))
            with self.assertRaises(ValueError):
                review.verify_existing_owner_license_texts(
                    folder,expected_review_entries_sha256="0"*64)

    def test_03_original_license_text_tamper_denied(self):
        with TemporaryDirectory() as tmp:
            folder,pin,manifest=self.build(Path(tmp))
            rel=manifest["reviewed_packages"][0]["declared_license_texts"][0]["relative_review_path"]
            file=folder.joinpath(*rel.split("/"))
            data=file.read_bytes()
            file.write_bytes(b"X"+data[1:])
            with self.assertRaises(ValueError):
                review.verify_existing_owner_license_texts(
                    folder,expected_review_entries_sha256=pin)

    def test_04_deleting_original_denied(self):
        with TemporaryDirectory() as tmp:
            folder,pin,manifest=self.build(Path(tmp))
            rel=manifest["reviewed_packages"][0]["declared_license_texts"][0]["relative_review_path"]
            folder.joinpath(*rel.split("/")).unlink()
            with self.assertRaises(ValueError):
                review.verify_existing_owner_license_texts(folder,expected_review_entries_sha256=pin)

    def test_05_unexpected_extra_file_denied(self):
        with TemporaryDirectory() as tmp:
            folder,pin,_=self.build(Path(tmp))
            (folder/"private-data.zip").write_bytes(b"untrusted, must not read")
            with self.assertRaises(ValueError):
                review.verify_existing_owner_license_texts(folder,expected_review_entries_sha256=pin)

    def test_06_noncanonical_duplicate_manifest_denied(self):
        with TemporaryDirectory() as tmp:
            folder,pin,_=self.build(Path(tmp))
            (folder/"review_manifest.json").write_bytes(b'{"schema":"bad","schema":"forged"}\n')
            with self.assertRaises(ValueError):
                review.verify_existing_owner_license_texts(folder,expected_review_entries_sha256=pin)

    def test_07_review_field_tamper_recomputed_manifest_still_denied(self):
        with TemporaryDirectory() as tmp:
            folder,_,m=self.build(Path(tmp))
            m["reviewed_packages"][0]["vendor_license_reviewed"]=True
            new=json.dumps(m["reviewed_packages"],sort_keys=True,ensure_ascii=True,
                           separators=(",",":")).encode()
            m["review_entries_sha256"]=sha256(new).hexdigest()
            (folder/"review_manifest.json").write_text(
                json.dumps(m,sort_keys=True)+"\n",encoding="ascii")
            with self.assertRaises(ValueError):
                review.verify_existing_owner_license_texts(
                    folder,expected_review_entries_sha256=m["review_entries_sha256"])

    def test_08_bad_target_and_scope_rejected(self):
        with TemporaryDirectory() as tmp:
            folder,pin,_=self.build(Path(tmp))
            for path in (folder.parent,folder.parent.parent,Path(tmp)):
                with self.subTest(path=str(path)),self.assertRaises(ValueError):
                    review.verify_existing_owner_license_texts(
                        path,expected_review_entries_sha256=pin)

    def test_09_no_owner_disk_writes_or_vendor_python_code_executed(self):
        with TemporaryDirectory() as tmp:
            folder,pin,_=self.build(Path(tmp))
            before={p.relative_to(folder).as_posix():sha256(p.read_bytes()).hexdigest()
                    for p in folder.rglob("*") if p.is_file()}
            with patch("urllib.request.urlopen",side_effect=AssertionError("network")):
                result=review.verify_existing_owner_license_texts(
                    folder,expected_review_entries_sha256=pin)
            after={p.relative_to(folder).as_posix():sha256(p.read_bytes()).hexdigest()
                   for p in folder.rglob("*") if p.is_file()}
            self.assertEqual(before,after)
            self.assertEqual(result["operating_database_writes"],0)

    def test_10_cli_stays_no_go_even_when_hash_audit_succeeds(self):
        with TemporaryDirectory() as tmp:
            folder,pin,_=self.build(Path(tmp))
            with patch.object(review,"owner_inspect_once",
                              return_value=review.verify_existing_owner_license_texts(
                                  folder,expected_review_entries_sha256=pin)):
                from io import StringIO
                from contextlib import redirect_stdout
                buf=StringIO()
                with redirect_stdout(buf):
                    status=review.main([
                        "--inspect-existing-owner-packet",
                        "--expected-review-entries-sha256",pin])
            self.assertEqual(status,2)
            self.assertFalse(json.loads(buf.getvalue())["customer_distribution_authorized"])


if __name__=="__main__":
    unittest.main()
