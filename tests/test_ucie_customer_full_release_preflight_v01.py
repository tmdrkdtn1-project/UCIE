"""First-party synthetic validation of UCIE complete commercial product NO-GO.

No real customer data, signer, installer, network or operating DB is accessed.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from ucie_miner.customer_full_release_preflight_v01 import (
    DISTRIBUTION, NO_GO, PILLAR_FILES, REQUIRED_FOUNDATION,
    inspect_customer_full_release, main,
)


class UCIEFullCustomerReleasePreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="UCIE_CUSTOMER_GATE_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / ".git").mkdir(parents=True)
        self.all_paths = {
            path for entries in PILLAR_FILES.values() for path in entries
        } | set(REQUIRED_FOUNDATION)
        for relative in sorted(self.all_paths):
            target = self.root.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# purely synthetic UCIE source\n", encoding="utf-8")

    def test_all_four_pillars_are_required_not_one_rule(self):
        r = inspect_customer_full_release(self.root)
        self.assertEqual(r["status"], NO_GO)
        self.assertEqual(r["distribution"], DISTRIBUTION)
        self.assertEqual(r["pillar_count_required"], 4)
        self.assertEqual(set(r["pillars"]), set(PILLAR_FILES))
        self.assertTrue(r["four_pillar_source_inventory_present"])
        self.assertTrue(r["single_rule_release_is_not_full_product"])
        self.assertEqual(r["first_party_file_sha256_count"],
                         len(self.all_paths))
        self.assertTrue(all(
            not row["real_customer_end_to_end_accepted"]
            for row in r["pillars"].values()
        ))

    def test_full_inventory_does_not_become_customer_release_approval(self):
        r = inspect_customer_full_release(self.root)
        for key in ("customer_license_issued", "customer_bundle_signed",
                    "actual_customer_receipt_verified",
                    "private_distribution_executed",
                    "public_package_published",
                    "approved_skillbook_export_executed",
                    "proprietary_license_and_recipient_terms_approved",
                    "customer_data_read",
                    "other_project_access"):
            self.assertIs(r[key], False)
        self.assertEqual(r["runtime_database_writes"], 0)
        self.assertEqual(r["task_scheduler_changes"], 0)
        self.assertIn(
            "HUMAN_AND_MACHINE_SKILLBOOKS_NOT_APPROVED_FOR_CUSTOMER_EXPORT",
            r["blocker_codes"],
        )

    def test_missing_library_evidence_is_reported_independently(self):
        (self.root / "src/ucie_miner/skillbook_catalog_union_v01.py").unlink()
        r = inspect_customer_full_release(self.root)
        self.assertFalse(r["four_pillar_source_inventory_present"])
        self.assertFalse(r["pillars"][
            "virtual_library_and_skillbooks"
        ]["first_party_file_inventory_present"])
        self.assertIn(
            "MISSING_OR_UNSAFE_FIRST_PARTY_SURFACE:virtual_library_and_skillbooks",
            r["blocker_codes"],
        )
        self.assertEqual(r["status"], NO_GO)

    def test_missing_evolution_contract_blocks_even_with_other_three(self):
        (self.root / "src/ucie_miner/p11_closed_loop.py").unlink()
        r = inspect_customer_full_release(self.root)
        self.assertFalse(r["four_pillar_source_inventory_present"])
        self.assertIn(
            "MISSING_OR_UNSAFE_FIRST_PARTY_SURFACE:continuous_evidence_evolution",
            r["blocker_codes"],
        )

    def test_wrong_root_rejected_before_reading_any_file(self):
        r = inspect_customer_full_release(Path(self.tmp.name))
        self.assertEqual(r["pillars"], {})
        self.assertIn("NOT_EXACT_UCIE_CHECKOUT", r["blocker_codes"])

    def test_code_sha_tracks_any_first_party_drift(self):
        relative = "src/ucie_miner/regression_plans.py"
        a = inspect_customer_full_release(self.root)
        row = a["pillars"]["error_prevention"]["files"][relative]
        self.assertEqual(
            row["sha256"], sha256(
                (self.root / relative).read_bytes()
            ).hexdigest(),
        )
        (self.root / relative).write_text("changed first-party synthetic", encoding="utf-8")
        b = inspect_customer_full_release(self.root)
        self.assertNotEqual(
            row["sha256"],
            b["pillars"]["error_prevention"]["files"][relative]["sha256"],
        )
        self.assertEqual(b["status"], NO_GO)

    def test_cli_is_machine_readable_and_refuses_release(self):
        out = StringIO()
        with redirect_stdout(out):
            exit_code = main(["--ucie-root", str(self.root)])
        self.assertEqual(exit_code, 2)
        data = json.loads(out.getvalue())
        self.assertEqual(data["status"], NO_GO)
        self.assertFalse(data["private_distribution_executed"])

    def test_no_customer_distribution_content_in_report(self):
        r = inspect_customer_full_release(self.root)
        serialized = json.dumps(r)
        for forbidden in ("customer_name", "customer_email",
                          "license_key", "private_key",
                          "customer_project_path"):
            self.assertNotIn('"' + forbidden + '"', serialized)


class UCIECurrentCheckoutSmoke(unittest.TestCase):
    def test_real_first_party_checkout_presence_not_customer_acceptance(self):
        root = Path(__file__).resolve().parents[1]
        if root.name.casefold() != "ucie" or not (root / ".git").is_dir():
            self.skipTest("requires first-party UCIE checkout")
        r = inspect_customer_full_release(root)
        self.assertEqual(r["status"], NO_GO)
        self.assertEqual(set(r["pillars"]), set(PILLAR_FILES))
        self.assertFalse(r["actual_customer_receipt_verified"])
        self.assertFalse(r["private_distribution_executed"])
        print("UCIE_COMPLETE_CUSTOMER_READINESS=" + json.dumps({
            "schema": r["schema"],
            "status": r["status"],
            "distribution": r["distribution"],
            "pillar_file_inventory": {
                k: v["first_party_file_inventory_present"]
                for k, v in r["pillars"].items()
            },
            "first_party_file_sha256_count": r["first_party_file_sha256_count"],
            "real_customer_acceptance": False,
            "commercial_license_signed": False,
            "customer_bundle_signed": False,
        }, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
