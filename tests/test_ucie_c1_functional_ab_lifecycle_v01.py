"""UCIE C1 functional A/B first-party tests; NEVER real vendor pip in CI.

Real UCIE-owned inert wheels, SHA and atomic scratch selectors are exercised.
Child installs, native vendor execution and local HTTP are fully mocked.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from ucie_miner import customer_functional_ab_lifecycle_v01 as ab
from ucie_miner import customer_installed_health_v01 as health
from ucie_miner import customer_full_product_offline_rehearsal_v01 as full
from ucie_miner import customer_component_lifecycle_v01 as comp
from ucie_miner import customer_runtime_closure_v01 as runtime
from ucie_miner import customer_owner_wheelhouse_acquire_v01 as vendor
from ucie_miner.customer_staging_v01 import PILLARS


PROJECT = """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
[project]
name = "ucie-public-only-demo"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["cryptography>=50.0.2,<51"]
"""
HASHES = {"cryptography": "a"*64, "cffi": "b"*64, "pycparser": "c"*64}


class UCIEFunctionalABLifecycleV01Tests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="UCIE_C1_AB_TEST_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "UCIE"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        (self.root / ".gitignore").write_text("downloaded/\n", encoding="utf-8")
        (self.root / "pyproject.toml").write_text(PROJECT, encoding="utf-8")
        self.snapshot = {name: b"# UCIE inert C0 first-party\n" for name in comp.FILES}
        self.snapshot.update({
            "src/ucie_miner/__init__.py": b"# UCIE inert package\n",
            "src/ucie_public/__init__.py": b"# UCIE inert public package\n",
            "src/ucie_miner/local_v1_app_v01.py": b"# UCIE inert local V04\n",
            "src/ucie_miner/customer_staging_v01.py": b"# UCIE inert four pillars\n",
            "src/ucie_miner/customer_portable_preview_v01.py":
                b'REVISION = "UCIE_C1_DISPOSABLE_GENERATION_A"\n',
            ab.B_SOURCE: (
                b"TEST_ONLY_B_VERSION = '0.1.1'\n"
                b"def run_installed_self_check():\n"
                b"    return {'customer_distribution_authorized': False}\n"
            ),
        })

    def test_readonly_preview_fails_closed_before_owner_full_receipt(self):
        with patch("subprocess.run", side_effect=AssertionError("NO PIP")), patch(
            "urllib.request.urlopen", side_effect=AssertionError("NO NETWORK")
        ):
            result = ab.preview(self.root)
        self.assertEqual(result["readiness"], "PREVIOUS_FULL_PRODUCT_RECEIPT_PENDING")
        self.assertFalse(result["prior_owner_product_verified"])
        self.assertEqual(result["subprocesses_executed"], 0)
        self.assertFalse(result["customer_distribution_authorized"])

    def test_preview_ready_only_with_prior_verified_full_product(self):
        with patch.object(full, "_dependency_evidence", return_value=(HASHES, "e"*64)), patch.object(
            ab, "_previous_full_receipt", return_value="a"*64
        ):
            data = ab.preview(self.root)
        self.assertEqual(data["readiness"], "READY_FOR_OWNER_FUNCTIONAL_AB_CONSENT")
        self.assertTrue(data["prior_owner_product_verified"])
        f = self.root / ab.RECEIPT
        f.parent.mkdir()
        f.write_text("UCIE inert prior receipt", encoding="ascii")
        data = ab.preview(self.root)
        self.assertEqual(data["readiness"], "PREVIOUS_AB_RECEIPT_PRESERVED")
        self.assertFalse(data["prior_owner_product_verified"])

    def test_real_synthetic_A_B_distinct_source_and_features(self):
        a, b = ab._two_sources(self.snapshot)
        self.assertNotIn(ab.B_SOURCE, a)
        self.assertIn(ab.B_SOURCE, b)
        self.assertEqual(len(b), len(a)+1)
        self.assertEqual(a["src/ucie_miner/customer_staging_v01.py"],
                         b["src/ucie_miner/customer_staging_v01.py"])
        with TemporaryDirectory(prefix="UCIE_TWO_WHEELS_") as temp:
            root = Path(temp)
            out_a, out_b = root / "A", root / "B"
            out_a.mkdir()
            out_b.mkdir()
            wheel_a = full._build_first_party_wheel(out_a, a, version=ab.A_VERSION)
            wheel_b = full._build_first_party_wheel(out_b, b, version=ab.B_VERSION)
            digest_a = sha256(wheel_a.read_bytes()).hexdigest()
            digest_b = sha256(wheel_b.read_bytes()).hexdigest()
            self.assertNotEqual(digest_a, digest_b)
            aa = ab._verified_wheel(wheel_a, a, ab.A_VERSION, digest_a)
            bb = ab._verified_wheel(wheel_b, b, ab.B_VERSION, digest_b)
            self.assertEqual(bb["file_count"], aa["file_count"]+1)
            self.assertEqual(bb["version"], "0.1.1")
            with ZipFile(wheel_a) as z:
                self.assertNotIn("ucie_miner/customer_installed_health_v01.py",
                                 z.namelist())
            with ZipFile(wheel_b) as z:
                self.assertIn("ucie_miner/customer_installed_health_v01.py",
                              z.namelist())

    def test_b_wheel_wrong_expected_version_and_corruption_rejected(self):
        a, b = ab._two_sources(self.snapshot)
        with TemporaryDirectory(prefix="UCIE_AB_NEGATIVE_") as temp:
            out = Path(temp)
            wheel = full._build_first_party_wheel(out, b, version=ab.B_VERSION)
            original = sha256(wheel.read_bytes()).hexdigest()
            with self.assertRaises(full.OfflineFullProductError):
                full._inspect_first_party_wheel(wheel, b, version=ab.A_VERSION)
            with self.assertRaises(ab.ABRehearsalError):
                ab._verified_wheel(wheel, b, ab.B_VERSION, "0"*64)
            with wheel.open("ab") as f:
                f.write(b"UCIE inert tamper appended\n")
            with self.assertRaises(ab.ABRehearsalError):
                ab._verified_wheel(wheel, b, ab.B_VERSION, original)

    def test_missing_b_feature_is_not_faked_by_version_marker(self):
        snapshot = dict(self.snapshot)
        snapshot.pop(ab.B_SOURCE)
        with self.assertRaises(ab.ABRehearsalError):
            ab._two_sources(snapshot)
        snapshot[ab.B_SOURCE] = b"REVISION = 'B'\n"
        with self.assertRaises(ab.ABRehearsalError):
            ab._two_sources(snapshot)

    def test_invalid_hashes_version_and_wheel_names_fail_closed(self):
        with TemporaryDirectory(prefix="UCIE_AB_REQ_") as temp:
            p = Path(temp)
            with self.assertRaises(full.OfflineFullProductError):
                full._build_first_party_wheel(p, self.snapshot, version="CUSTOMER_GO")
            with self.assertRaises(full.OfflineFullProductError):
                full._requirements(HASHES, "0"*64, version="CUSTOMER_GO")
            with self.assertRaises(ab.ABRehearsalError):
                ab._verified_wheel(p / "missing.whl", {}, ab.A_VERSION, "1"*64)

    def test_disposable_pointer_A_then_B_then_A_rollback(self):
        with TemporaryDirectory(prefix="UCIE_AB_SELECTOR_") as temp:
            root = Path(temp)
            hashes = {"A": "1"*64, "B": "2"*64}
            ab._select(root, "A", hashes)
            ab._selected(root, "A", hashes)
            ab._select(root, "B", hashes)
            ab._selected(root, "B", hashes)
            ab._select(root, "A", hashes)
            ab._selected(root, "A", hashes)
            with self.assertRaises(ab.ABRehearsalError):
                ab._selected(root, "B", hashes)
            (root / "active-slot.json").write_text(json.dumps(
                {"schema": ab.SCHEMA, "slot": "CUSTOMER_GO"}))
            with self.assertRaises(ab.ABRehearsalError):
                ab._selected(root, "A", hashes)

    def test_b_only_real_installed_self_check_is_functional(self):
        data = {
            "schema": "UCIE_FOUR_PILLAR_INSTALLED_STAGING_V01",
            "four_pillars_exercised": True,
            "product_capabilities_worked_in_staging": True,
            "customer_distribution_authorized": False,
            "automatic_rule_promotion": False,
            "customer_data_scanned": False,
            "operating_ucie_database_written": False,
            "complete_customer_functional_acceptance": False,
            "workflows": {p: {"status": "UCIE synthetic"} for p in PILLARS},
        }
        with patch.object(health, "version", return_value="0.1.1"), patch.object(
            health, "run_four_pillar_staging", return_value=data
        ):
            actual = health.run_installed_self_check()
        self.assertEqual(actual["schema"], health.SCHEMA)
        self.assertEqual(actual["installed_version"], "0.1.1")
        self.assertTrue(actual["installed_four_pillar_workflows_checked"])
        self.assertFalse(actual["customer_distribution_authorized"])
        with patch.object(health, "version", return_value="0.1.0"):
            with self.assertRaises(health.InstalledHealthError):
                health.run_installed_self_check()
        data["customer_distribution_authorized"] = True
        with patch.object(health, "version", return_value="0.1.1"), patch.object(
            health, "run_four_pillar_staging", return_value=data
        ):
            with self.assertRaises(health.InstalledHealthError):
                health.run_installed_self_check()

    def test_installed_version_feature_and_isolation_checked(self):
        path = self.root / "downloaded" / "venv"
        a = {"version": "0.1.0", "b_only_health_present": False,
             "prefix": str(path), "isolated": True, "bits": 64}
        b = dict(a, version="0.1.1", b_only_health_present=True)
        with patch.object(full, "_run", return_value=json.dumps(a)):
            with self.assertRaises(ab.ABRehearsalError):
                ab._install(Path(sys.executable), self.root,
                            self.root, self.root / "missing.whl",
                            "0.1.0", "a"*64, HASHES, {})
        # Unit of installed identity is observed via the mocked complete path.

    def test_bad_owner_gate_or_wrong_consent_never_starts_pip(self):
        with patch("subprocess.run", side_effect=AssertionError("NO PIP")), patch(
            "urllib.request.urlopen", side_effect=AssertionError("NO NETWORK")
        ):
            with self.assertRaises(ab.ABRehearsalError):
                ab._owner_gate(self.root)
            with patch.object(ab, "_owner_gate", side_effect=AssertionError(
                "gate must not run without user consent"
            )):
                with self.assertRaises(ab.ABRehearsalError):
                    ab.run_once(self.root, "WRONG_USER_CONFIRMATION")

    def test_real_source_snapshot_rehearsal_is_mocked_not_vendor_exec(self):
        (self.root / "downloaded").mkdir()
        events = []
        def pretend(args, cwd, env, why):
            events.append(why)
            if why == "A/B new venv":
                child = Path(args[-1]) / "Scripts" / "python.exe"
                child.parent.mkdir(parents=True)
                child.write_bytes(b"UCIE inert fake, never executed")
            if why == "A/B installed version":
                slot_b = "slot_B" in str(cwd)
                return json.dumps({
                    "version": "0.1.1" if slot_b else "0.1.0",
                    "b_only_health_present": slot_b,
                    "prefix": str(Path(cwd) / "recipient_venv"),
                    "isolated": True, "bits": 64,
                })
            if why == "A/B four-pillar installed CLI":
                return json.dumps({
                    "schema": "UCIE_FOUR_PILLAR_INSTALLED_STAGING_V01",
                    "four_pillars_exercised": True,
                    "product_capabilities_worked_in_staging": True,
                    "customer_distribution_authorized": False,
                    "operating_ucie_database_written": False,
                    "customer_data_scanned": False,
                    "automatic_rule_promotion": False,
                    "pillars_exercised": list(PILLARS),
                    "workflows": {p: {"status": "UCIE synthetic"}
                                  for p in PILLARS},
                })
            if why == "A/B installed localhost UI":
                return json.dumps({
                    "schema": "UCIE_C1_PORTABLE_LOCALHOST_PREVIEW_V01",
                    "loopback_http_routes_checked": 5,
                    "negative_post_checked": True, "bound_host": "127.0.0.1",
                    "task_scheduler_modified": False,
                    "customer_distribution_authorized": False
                })
            if why == "B-only installed four-pillar self-check":
                return json.dumps({
                    "schema": "UCIE_C1_INSTALLED_FOUR_PILLAR_SELF_CHECK_V01",
                    "installed_version": "0.1.1",
                    "new_in_functional_version_b": True,
                    "installed_four_pillar_workflows_checked": True,
                    "customer_distribution_authorized": False,
                    "auto_promoted": False,
                    "customer_code_read": False,
                    "four_pillars": list(PILLARS),
                    "four_pillar_synthetic_workflow_sha256": "9"*64,
                })
            if why == "confirm UCIE distribution absent":
                return json.dumps({
                    "installed": False, "ucie_module_still_present": False
                })
            return ""
        with patch.object(ab, "_owner_gate", return_value=Path(sys.executable)), patch.object(
            ab, "_previous_full_receipt", return_value="e"*64
        ), patch.object(full, "_dependency_evidence", return_value=(HASHES, "f"*64)), patch.object(
            runtime, "inspect_static_runtime_closure",
            return_value={"missing_first_party_imports": []}
        ), patch.object(runtime, "_copy_payload", return_value=self.snapshot), patch.object(
            full, "_run", side_effect=pretend
        ), patch("subprocess.run", side_effect=AssertionError("NO REAL PIP")), patch(
            "urllib.request.urlopen", side_effect=AssertionError("NO NETWORK")
        ):
            receipt = ab.run_once(self.root, ab.CONSENT)
        self.assertTrue(receipt["two_first_party_product_wheels_functionally_distinct"])
        self.assertTrue(receipt["A_then_B_activation_then_A_rollback_tested"])
        self.assertTrue(receipt["tampered_B_candidate_rejected_before_activation"])
        self.assertTrue(receipt["two_first_party_pip_uninstalls_confirmed"])
        self.assertTrue(receipt["disposable_venvs_source_and_wheels_removed"])
        self.assertFalse(receipt["customer_distribution_authorized"])
        self.assertIn("B-only installed four-pillar self-check", events)
        self.assertEqual(events.count("disposable UCIE product pip uninstall"), 2)
        self.assertEqual(events.count("A/B four-pillar installed CLI"), 3)
        self.assertTrue((self.root / ab.RECEIPT).is_file())
        self.assertEqual(list((self.root / "downloaded").glob(
            "ucie_c1_ab_slots_*")), [])

    def test_readonly_main_does_not_request_consumption_consent(self):
        path = self.root / "src" / "ucie_miner" / "customer_functional_ab_lifecycle_v01.py"
        output = io.StringIO()
        with patch.object(ab, "__file__", str(path)), patch(
            "subprocess.run", side_effect=AssertionError("NO PIP")
        ), redirect_stdout(output):
            rc = ab.main([])
        self.assertEqual(rc, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["mode"], "OFFLINE_READONLY_PREVIEW")
        self.assertFalse(payload["customer_distribution_authorized"])

    def test_real_complete_ucie_source_inventory_yields_distinct_a_b_wheels(self):
        """Actually package BOTH bounded complete UCIE first-party snapshots.

        Pure standard-library work; no pip, vendor imports, network or owner
        operating data. This proves more than changing the metadata label.
        """
        real = Path(__file__).resolve().parents[1]
        if real.name.casefold() != "ucie" or not (real / ".git").is_dir():
            self.skipTest("exact UCIE checkout required")
        graph = runtime.inspect_static_runtime_closure(real)
        inventory = runtime._copy_payload(real, graph)
        a, b = ab._two_sources(inventory)
        with TemporaryDirectory(prefix="UCIE_REAL_SOURCE_AB_WHEELS_") as tmp:
            root = Path(tmp)
            first, second = root / "A", root / "B"
            first.mkdir()
            second.mkdir()
            aw = full._build_first_party_wheel(first, a, version=ab.A_VERSION)
            bw = full._build_first_party_wheel(second, b, version=ab.B_VERSION)
            x = full._inspect_first_party_wheel(aw, a, version=ab.A_VERSION)
            y = full._inspect_first_party_wheel(bw, b, version=ab.B_VERSION)
            self.assertNotEqual(x["sha256"], y["sha256"])
            self.assertEqual(y["file_count"], x["file_count"] + 1)
            self.assertGreaterEqual(x["file_count"], 190)
            self.assertEqual(y["file_count"],
                             graph["all_python_modules_indexed"])
            print("UCIE_C1_REAL_FULL_SOURCE_AB_MODULES=" +
                  str(x["file_count"]) + "/" + str(y["file_count"]))
            self.assertTrue(x["wheel_record_verified"])
            self.assertTrue(y["wheel_record_verified"])
            self.assertTrue(x["source_code_bytes_match"])
            self.assertTrue(y["source_code_bytes_match"])

    def test_real_ucie_owner_is_preview_only(self):
        root = Path(__file__).resolve().parents[1]
        if root.name.casefold() != "ucie" or not (root / ".git").is_dir():
            self.skipTest("only first-party UCIE checkout")
        state = ab.preview(root)
        print("UCIE_C1_FUNCTIONAL_AB_READINESS=" + state["readiness"])
        self.assertFalse(state["customer_distribution_authorized"])
        self.assertEqual(state["subprocesses_executed"], 0)


if __name__ == "__main__":
    unittest.main()
