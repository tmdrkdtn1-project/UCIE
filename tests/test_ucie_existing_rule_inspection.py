"""UCIE integrated real code inspection using existing first-party scanners.

Synthetic controls only; signed-owner branch is tested both fail-closed and
with a clearly MOCKED verifier. Original signature verification is covered by
existing mixed-release tests, never inferred from a mocked fixture.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import existing_rule_inspection as view

SCANDIR_BAD = """import os
from concurrent.futures import ThreadPoolExecutor
def run(folder, f):
    iterator = os.scandir(folder)
    with ThreadPoolExecutor(max_workers=2) as pool:
        return pool.submit(f, iterator).result()
"""
SCANDIR_GOOD = """import os
def run(folder):
    with os.scandir(folder) as iterator:
        return [item.name for item in iterator]
"""
ASYNCIO_BAD = """class BaseEventLoop:
    async def connect_read_pipe(self, protocol_factory, pipe):
        protocol = protocol_factory()
        waiter = self.create_future()
        transport = self._make_read_pipe_transport(pipe, protocol, waiter)
        try:
            await waiter
        except:
            transport.close()
            raise
"""
ASYNCIO_GOOD = """class BaseEventLoop:
    async def connect_read_pipe(self, protocol_factory, pipe):
        try:
            protocol = protocol_factory()
        except BaseException:
            pipe.close()
            raise
        waiter = self.create_future()
        transport = self._make_read_pipe_transport(pipe, protocol, waiter)
"""
MCP_BAD = """async def send_raw_request(self, method, params):
    out_params = dict(params or {})
    out_meta = {}
    out_params["_meta"] = out_meta
    return JSONRPCRequest(jsonrpc="2.0", method=method, params=out_params)
"""
MCP_GOOD = """async def send_raw_request(self, method, params):
    out_params = dict(params or {})
    out_meta = {}
    if out_meta:
        out_params["_meta"] = out_meta
    return JSONRPCRequest(jsonrpc="2.0", method=method, params=out_params)
"""
DECIMAL_BAD = """import _pydecimal as d
with d.localcontext() as c:
    c.prec = d.MAX_PREC
    value = d.Decimal("1")
    out = value % 1
"""
DECIMAL_GOOD = DECIMAL_BAD.replace("c.prec = d.MAX_PREC", "c.prec = 28")
POSITIVE = [
    ("scandir", SCANDIR_BAD, "PY_SCANDIR_SHARED_ITERATOR_RACE"),
    ("asyncio", ASYNCIO_BAD, "PY_ASYNCIO_PROTOCOL_FACTORY_PRETRANSPORT_LEAK"),
    ("mcp", MCP_BAD, "MCP_JSONRPC_UNCONDITIONAL_EMPTY_META"),
    ("decimal", DECIMAL_BAD, "PY_DECIMAL_UNBOUNDED_PURE_PYTHON_REVIEW"),
]


class ExistingRuleInspectionTests(unittest.TestCase):
    def test_four_existing_detectors_through_one_real_inspection(self):
        for name, text, expected in POSITIVE:
            with self.subTest(name=name):
                out = view.inspect_existing_python(text)
                self.assertEqual(out["finding_count"], 1, out["findings"])
                self.assertEqual(out["findings"][0]["rule_id"], expected)
                self.assertEqual(out["findings"][0]["authorization"],
                                 "UNVERIFIED_STATIC_CANDIDATE_ONLY")
                self.assertFalse(out["source_executed"])
                self.assertFalse(out["auto_promoted"])
                self.assertEqual(out["database_writes"], 0)
                self.assertEqual(out["existing_signed_manual_matches"], 0)
                self.assertFalse(out["independent_qa_completed"])

    def test_four_normal_code_negative_controls(self):
        for text in (SCANDIR_GOOD, ASYNCIO_GOOD, MCP_GOOD, DECIMAL_GOOD):
            with self.subTest(fragment=text[:20]):
                result = view.inspect_existing_python(text)
                self.assertEqual(result["finding_count"], 0)
                self.assertEqual(result["status"],
                                 "NO_PATTERN_FOUND_NOT_A_SAFETY_PASS")

    def test_fast_path_skips_only_impossible_detector_families(self):
        # No required identifier: validate the complete AST, but none of the
        # four heavy detectors needs to re-parse it.
        with (
            patch.object(view, "inspect_python_scandir_source",
                         side_effect=AssertionError("scandir unnecessary")),
            patch.object(view, "inspect_asyncio_protocol_factory_source",
                         side_effect=AssertionError("asyncio unnecessary")),
            patch.object(view, "inspect_mcp_empty_meta_source",
                         side_effect=AssertionError("mcp unnecessary")),
            patch.object(view, "inspect_decimal_source",
                         side_effect=AssertionError("decimal unnecessary")),
        ):
            r = view.inspect_existing_python(
                "def simple(a, b):\n    return a + b\n")
        self.assertEqual(r["finding_count"], 0)
        self.assertFalse(r["auto_promoted"])

    def test_specialized_scanners_still_called_for_their_required_identifiers(self):
        originals = {
            "scandir": view.inspect_python_scandir_source,
            "asyncio": view.inspect_asyncio_protocol_factory_source,
            "mcp": view.inspect_mcp_empty_meta_source,
            "decimal": view.inspect_decimal_source,
        }
        mapping = {
            "scandir": "inspect_python_scandir_source",
            "asyncio": "inspect_asyncio_protocol_factory_source",
            "mcp": "inspect_mcp_empty_meta_source",
            "decimal": "inspect_decimal_source",
        }
        for name, source, _ in POSITIVE:
            with self.subTest(name=name):
                calls = {key: 0 for key in originals}
                def wrappers(key, func):
                    def bound(text):
                        calls[key] += 1
                        return func(text)
                    return bound
                with (
                    patch.object(view, mapping["scandir"],
                                 side_effect=wrappers("scandir", originals["scandir"])),
                    patch.object(view, mapping["asyncio"],
                                 side_effect=wrappers("asyncio", originals["asyncio"])),
                    patch.object(view, mapping["mcp"],
                                 side_effect=wrappers("mcp", originals["mcp"])),
                    patch.object(view, mapping["decimal"],
                                 side_effect=wrappers("decimal", originals["decimal"])),
                ):
                    result = view.inspect_existing_python(source)
                self.assertEqual(result["finding_count"], 1)
                self.assertEqual(calls[name], 1)
                self.assertEqual(sum(calls.values()), 1)

    def test_fast_path_still_rejects_invalid_python(self):
        # Syntax checking cannot be bypassed just because no rule-name
        # tokens were present in the untrusted text.
        for source in ("def broken(:\n", "class A:\n  def", "if True\n  pass"):
            with self.subTest(source=source), self.assertRaises(
                (view.InspectionError, ValueError)
            ):
                view.inspect_existing_python(source)

    def test_fast_path_preserves_strict_ast_complexity_bound(self):
        source = "x = 1\n" * 2600  # 15.6 KiB, over 10,000 AST nodes
        with self.assertRaises(view.InspectionError):
            view.inspect_existing_python(source)

    def test_string_tokens_cannot_hide_actual_risk_code(self):
        # A misleading comment/string must not suppress a real detector.
        source = "note = 'ignore scandir, protocol_factory and _pydecimal'\n" + MCP_BAD
        result = view.inspect_existing_python(source)
        self.assertEqual(result["finding_count"], 1)
        self.assertEqual(result["findings"][0]["rule_id"],
                         "MCP_JSONRPC_UNCONDITIONAL_EMPTY_META")
        self.assertFalse(result["auto_promoted"])

    def test_synthetic_feedback_reuses_inspection_and_counts_errors(self):
        cases = [
            {"case_id": name + "_positive", "source": text,
             "expected_rule_ids": [rule]} for name,text,rule in POSITIVE
        ]
        cases += [
            {"case_id": f"control_{i}", "source": text,
             "expected_rule_ids": []}
            for i,text in enumerate(
                (SCANDIR_GOOD, ASYNCIO_GOOD, MCP_GOOD, DECIMAL_GOOD)
            )
        ]
        result = view.evaluate_labeled_feedback(cases)
        self.assertEqual(result["case_count"], 8)
        self.assertEqual(result["true_positive_rules"], 4)
        self.assertEqual(result["false_positive_rules"], 0)
        self.assertEqual(result["false_negative_rules"], 0)
        self.assertEqual(result["clean_negative_control_cases"], 4)
        self.assertEqual(result["precision_ppm"], 1000000)
        self.assertEqual(result["recall_ppm"], 1000000)
        self.assertFalse(result["production_quality_claim"])
        self.assertEqual(result["automatic_rule_updates"], 0)
        print("UCIE_EXISTING_INSPECTION_SYNTHETIC_FEEDBACK=" +
              json.dumps({
                  "cases": result["case_count"],
                  "tp": result["true_positive_rules"],
                  "fp": result["false_positive_rules"],
                  "fn": result["false_negative_rules"],
                  "tn_clean_control": result["clean_negative_control_cases"],
                  "production_quality_claim": False,
              }, sort_keys=True))

    def test_known_label_false_positive_and_false_negative_exposed(self):
        cases = [
            {"case_id": "fp", "source": SCANDIR_BAD,
             "expected_rule_ids": []},
            {"case_id": "fn", "source": SCANDIR_GOOD,
             "expected_rule_ids": ["PY_SCANDIR_SHARED_ITERATOR_RACE"]},
        ]
        result = view.evaluate_labeled_feedback(cases)
        self.assertEqual(result["true_positive_rules"], 0)
        self.assertEqual(result["false_positive_rules"], 1)
        self.assertEqual(result["false_negative_rules"], 1)
        self.assertEqual(result["precision_ppm"], 0)
        self.assertEqual(result["recall_ppm"], 0)

    def test_feedback_priority_uses_failures_not_raw_public_get_count(self):
        cases = [
            {"case_id":"fp", "source":SCANDIR_BAD, "expected_rule_ids":[]},
            {"case_id":"fn", "source":SCANDIR_GOOD,
             "expected_rule_ids":["PY_SCANDIR_SHARED_ITERATOR_RACE"]},
        ]
        result = view.evaluate_labeled_feedback(cases)
        self.assertEqual(result["next_review_priority"][0]["rule_id"],
                         "PY_SCANDIR_SHARED_ITERATOR_RACE")
        self.assertEqual(result["next_review_priority"][0]["false_positives"],1)
        self.assertEqual(result["next_review_priority"][0]["false_negatives"],1)
        self.assertEqual(result["automatic_rule_updates"],0)

    def test_lightweight_cli_synthetic_feedback_matches_existing_cli(self):
        root = Path(__file__).resolve().parents[1]
        cases = [
            {"case_id":"bad", "source":SCANDIR_BAD,
             "expected_rule_ids":["PY_SCANDIR_SHARED_ITERATOR_RACE"]},
            {"case_id":"good", "source":SCANDIR_GOOD,
             "expected_rule_ids":[]},
        ]
        fast = subprocess.run(
            [sys.executable,"-B","-m",
             "ucie_miner.existing_rule_inspection",
             "--ucie-root",str(root),"--feedback-synthetic"],
            input=json.dumps(cases),text=True,capture_output=True,
            cwd=root,timeout=8,
        )
        old = subprocess.run(
            [sys.executable,"-B","-m","ucie_miner",
             "feedback-python-synthetic-stdin"],
            input=json.dumps(cases),text=True,capture_output=True,
            cwd=root,timeout=8,
        )
        self.assertEqual(fast.returncode,0,fast.stderr)
        self.assertEqual(old.returncode,0,old.stderr)
        self.assertEqual(json.loads(fast.stdout),json.loads(old.stdout))
        self.assertFalse(json.loads(fast.stdout)["auto_promoted"])

    def test_lightweight_cli_missing_variables_report_distinct_reasons(self):
        root = Path(__file__).resolve().parents[1]
        for extra, reason in (
            ([], "EMPTY_SOURCE_STDIN"),
            (["--feedback-synthetic"], "EMPTY_FEEDBACK_STDIN"),
        ):
            with self.subTest(reason=reason):
                result = subprocess.run(
                    [sys.executable, "-B", "-m",
                     "ucie_miner.existing_rule_inspection",
                     "--ucie-root", str(root), *extra],
                    input="", text=True, capture_output=True, cwd=root,
                    timeout=8,
                )
                self.assertEqual(result.returncode, 2, result.stderr)
                data = json.loads(result.stdout)
                self.assertEqual(data["status"],
                                 "UCIE_CODE_INSPECTION_FAIL_CLOSED")
                self.assertEqual(data["reason_code"], reason)
                self.assertFalse(data["source_executed"])
                self.assertEqual(data["database_writes"], 0)
                self.assertNotIn("source_text", data)

    def test_feedback_cli_rejection_is_specific_without_leaking_source(self):
        root = Path(__file__).resolve().parents[1]
        good = {"case_id": "positive", "source": SCANDIR_BAD,
                "expected_rule_ids": ["PY_SCANDIR_SHARED_ITERATOR_RACE"]}
        clean = {"case_id": "negative", "source": SCANDIR_GOOD,
                 "expected_rule_ids": []}
        variants = [
            ([good, {**clean, "source": {"not": "a Python string"}}],
             "FEEDBACK_CASE_SOURCE_INVALID"),
            ([{**good, "source": "def broken(:"}, clean],
             "FEEDBACK_CASE_PYTHON_INVALID"),
            ([{**good, "expected_rule_ids": "PY_SCANDIR_SHARED_ITERATOR_RACE"},
              clean], "FEEDBACK_LABEL_INVALID"),
            ([good], "FEEDBACK_CASE_ARRAY_REQUIRED"),
            ([good, {**clean, "expected_rule_ids":
                     ["PY_SCANDIR_SHARED_ITERATOR_RACE"]}],
             "FEEDBACK_NEGATIVE_CASE_REQUIRED"),
            ([{**good, "expected_rule_ids": []}, clean],
             "FEEDBACK_POSITIVE_CASE_REQUIRED"),
        ]
        for cases, reason in variants:
            with self.subTest(reason=reason):
                p = subprocess.run(
                    [sys.executable, "-B", "-m",
                     "ucie_miner.existing_rule_inspection",
                     "--ucie-root", str(root), "--feedback-synthetic"],
                    input=json.dumps(cases), text=True, capture_output=True,
                    cwd=root, timeout=8)
                self.assertEqual(p.returncode, 2, p.stderr)
                result = json.loads(p.stdout)
                self.assertEqual(result["reason_code"], reason)
                self.assertEqual(result["database_writes"], 0)
                self.assertFalse(result["auto_promoted"])
                self.assertNotIn("source", result)

    def test_lightweight_cli_rejects_duplicate_json_and_signed_pack_flags(self):
        root = Path(__file__).resolve().parents[1]
        invocations = [
            ('[{"case_id":"a","case_id":"a"}]', []),
            ('[]', ["--serial4-pack",str(root/"missing.zip")]),
        ]
        for raw, extra in invocations:
            with self.subTest(raw=raw):
                p = subprocess.run(
                    [sys.executable,"-B","-m",
                     "ucie_miner.existing_rule_inspection",
                     "--ucie-root",str(root),"--feedback-synthetic",*extra],
                    input=raw,text=True,capture_output=True,cwd=root,timeout=8,
                )
                self.assertEqual(p.returncode,2,p.stderr)
                self.assertEqual(json.loads(p.stdout)["status"],
                                 "UCIE_CODE_INSPECTION_FAIL_CLOSED")

    def test_existing_main_cli_synthetic_feedback_json_produces_review_queue(self):
        root = Path(__file__).resolve().parents[1]
        cases = [
            {"case_id":"fp","source":SCANDIR_BAD,"expected_rule_ids":[]},
            {"case_id":"fn","source":SCANDIR_GOOD,
             "expected_rule_ids":["PY_SCANDIR_SHARED_ITERATOR_RACE"]},
        ]
        p = subprocess.run(
            [sys.executable,"-B","-m","ucie_miner",
             "feedback-python-synthetic-stdin"],
            input=json.dumps(cases),text=True,capture_output=True,
            cwd=root,timeout=8,
        )
        self.assertEqual(p.returncode,0,p.stderr)
        result=json.loads(p.stdout)
        self.assertEqual(result["false_positive_rules"],1)
        self.assertEqual(result["false_negative_rules"],1)
        self.assertEqual(len(result["next_review_priority"]),1)
        self.assertFalse(result["auto_promoted"])
        self.assertEqual(result["database_writes"],0)

    def test_existing_main_cli_duplicate_feedback_json_fails_closed(self):
        root=Path(__file__).resolve().parents[1]
        bad='[{"case_id":"x","case_id":"y","source":"pass","expected_rule_ids":[]}]'
        p=subprocess.run(
            [sys.executable,"-B","-m","ucie_miner",
             "feedback-python-synthetic-stdin"],
            input=bad,text=True,capture_output=True,cwd=root,timeout=8,
        )
        self.assertNotEqual(p.returncode,0)
        self.assertNotIn("FIRST_PARTY_SYNTHETIC_CALIBRATION_ONLY",p.stdout)

    def test_nested_unhashable_feedback_rule_id_fails_closed(self):
        cases = [
            {"case_id":"a","source":SCANDIR_BAD,
             "expected_rule_ids":[{"rule_id":"PY_SCANDIR_SHARED_ITERATOR_RACE"}]},
            {"case_id":"b","source":SCANDIR_GOOD,"expected_rule_ids":[]},
        ]
        with self.assertRaises(view.InspectionError):
            view.evaluate_labeled_feedback(cases)

    def test_invalid_forged_feedback_labels_fail_closed(self):
        base=[
            {"case_id":"positive","source":SCANDIR_BAD,
             "expected_rule_ids":["PY_SCANDIR_SHARED_ITERATOR_RACE"]},
            {"case_id":"negative","source":SCANDIR_GOOD,
             "expected_rule_ids":[]},
        ]
        for bad in (
            [*base,base[0]], # duplicate ID
            [{**base[0],"expected_rule_ids":["NOT_APPROVED"]},base[1]],
            [{**base[0],"expected_rule_ids":[base[0]["expected_rule_ids"][0]]*2},
             base[1]],
            [base[0],{**base[1],"source":"x"*20000}],
        ):
            with self.subTest(bad=str(bad)[:40]), self.assertRaises(view.InspectionError):
                view.evaluate_labeled_feedback(bad)

    def test_invalid_python_and_bounded_stdin_input_fail_closed(self):
        for raw in ("", "a"*20000, "def f(:", 123):
            with self.subTest(length=len(str(raw))), self.assertRaises(
                (view.InspectionError, ValueError)
            ):
                view.inspect_existing_python(raw)

    def test_unsigned_path_cannot_pretend_to_be_signed(self):
        with self.assertRaises(view.InspectionError):
            view.inspect_existing_python(SCANDIR_BAD,
                                         serial4_pack=Path("fake.zip"))
        with self.assertRaises(view.InspectionError):
            view.inspect_existing_python(SCANDIR_BAD,
                                         serial5_pack=Path("fake.zip"))

    def test_missing_or_invalid_original_signed_pack_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)/"UCIE"
            root.mkdir()
            (root/"runtime").mkdir()
            with self.assertRaises(view.InspectionError):
                view.inspect_existing_python(
                    SCANDIR_BAD,root=root,
                    serial4_pack=root/"absent.zip",
                    owner_public_trust=root/"missing.pem",
                )

    def test_only_original_verified_signed_match_can_receive_manual_scope(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)/"UCIE"
            root.mkdir()
            (root/"runtime").mkdir()
            fake_index={"items":[{"rule_id":"PY_SCANDIR_SHARED_ITERATOR_RACE"}]}
            from ucie_miner.static_concurrency import inspect_python_scandir_source
            finding=inspect_python_scandir_source(SCANDIR_BAD)["findings"][0]
            matched={
                "owner_signature":"VALID", "pack_serial":4,
                "source_sha256":inspect_python_scandir_source(SCANDIR_BAD)["source_sha256"],
                "auto_apply":False,
                "findings":[{
                    "rule_id":"PY_SCANDIR_SHARED_ITERATOR_RACE",
                    "line":finding["line"],"column":finding["column"],
                    "public_evidence":finding["public_evidence"],
                    "guidance":finding["safe_fix_guidance"],
                }],
            }
            with (
                patch("ucie_miner.signed_rule_library.inspect_signed_library",
                      return_value=fake_index),
                patch("ucie_public.mixed_release.scan_mixed_owner_receipt",
                      return_value=matched),
            ):
                result=view.inspect_existing_python(
                    SCANDIR_BAD,root=root,serial4_pack=root/"synthetic-pack.zip",
                    owner_public_trust=root/"synthetic-public.pem")
            self.assertEqual(result["existing_signed_manual_matches"],1)
            self.assertEqual(result["findings"][0]["authorization"],
                             "EXISTING_OWNER_SIGNED_MANUAL_ONLY")
            self.assertFalse(result["auto_applied"])
            self.assertFalse(result["independent_qa_completed"])
            # Signature behavior is MOCKED here; genuine cryptographic
            # verification is exercised by existing mixed-release tests.

    def test_existing_main_cli_switch_uses_one_combined_inspection(self):
        root = Path(__file__).resolve().parents[1]
        p = subprocess.run(
            [sys.executable, "-B", "-m", "ucie_miner",
             "scan-python-stdin", "--all-existing-rules"],
            input=SCANDIR_BAD, text=True, capture_output=True,
            timeout=8, cwd=root)
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result["schema"], view.SCHEMA)
        self.assertEqual(result["finding_count"], 1)
        self.assertEqual(result["findings"][0]["rule_id"],
                         "PY_SCANDIR_SHARED_ITERATOR_RACE")
        self.assertFalse(result["auto_promoted"])
        self.assertEqual(result["database_writes"], 0)

    def test_existing_main_cli_default_legacy_scanner_unchanged(self):
        root = Path(__file__).resolve().parents[1]
        p = subprocess.run(
            [sys.executable, "-B", "-m", "ucie_miner", "scan-python-stdin"],
            input=SCANDIR_BAD, text=True, capture_output=True,
            timeout=8, cwd=root)
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result["schema"],
                         "UCIE_PYTHON_SCANDIR_STATIC_CANDIDATES_V1")
        self.assertEqual(result["finding_count"], 1)

    def test_existing_main_cli_conflicting_approval_flags_fail_closed(self):
        root = Path(__file__).resolve().parents[1]
        p = subprocess.run(
            [sys.executable, "-B", "-m", "ucie_miner",
             "scan-python-stdin", "--all-existing-rules",
             "--preview-candidates"],
            input=SCANDIR_BAD, text=True, capture_output=True,
            timeout=8, cwd=root)
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn("EXISTING_OWNER_SIGNED_MANUAL_ONLY", p.stdout)

    def test_actual_ephemeral_signed_pack_cryptographically_verified_before_match(self):
        # Ephemeral test-only keypair and pack; NEVER use owner-host private key.
        from test_ucie_mixed_release import fake_api
        from test_ucie_owner_risk_release import RUN, SHA
        from ucie_public.rulepack import generate_keys
        from ucie_public.mixed_release import (
            publish_mixed_owner_release, CONFIRM, RULE_ORDER, ELIGIBLE,
            FOURTH_CI,
        )
        from ucie_public.selected_release import (
            EXPECTED_SECOND_CI, EXPECTED_THIRD_CI,
        )
        with tempfile.TemporaryDirectory() as location:
            root = Path(location) / "UCIE"
            root.mkdir()
            (root / "build").mkdir()
            key, trust = generate_keys(root / "synthetic", purpose="production")
            pack = root / "build" / "mixed-four.zip"
            main_ci, jobs = fake_api()
            with (
                patch("ucie_public.mixed_release._local_clean_sha",
                      return_value=SHA),
                patch("ucie_public.owner_release._public_json",
                      side_effect=[main_ci, jobs]),
                patch("ucie_public.mixed_release._postfix_ci",
                      return_value=EXPECTED_SECOND_CI),
                patch("ucie_public.mixed_release._third_ci",
                      return_value=EXPECTED_THIRD_CI),
                patch("ucie_public.mixed_release._fourth_ci",
                      return_value=FOURTH_CI),
            ):
                publish_mixed_owner_release(
                    root, key, pack, run_id=RUN, serial=4,
                    rule_ids=list(RULE_ORDER), confirmation=CONFIRM,
                    risk_acceptances={
                        rid: ELIGIBLE[rid][2] for rid in RULE_ORDER
                    },
                )
            result = view.inspect_existing_python(
                SCANDIR_BAD, root=root, serial4_pack=pack,
                owner_public_trust=trust,
            )
            self.assertEqual(result["existing_signed_manual_matches"], 1)
            self.assertEqual(result["finding_count"], 1)
            self.assertEqual(result["findings"][0]["authorization"],
                             "EXISTING_OWNER_SIGNED_MANUAL_ONLY")
            self.assertFalse(result["independent_qa_completed"])
            self.assertFalse(result["auto_applied"])
            # A changed or untrusted public trust key must fail closed.
            (root / "synthetic" / "invalid-trust.pem").write_text(
                "NOT_A_PUBLIC_KEY", encoding="ascii"
            )
            with self.assertRaises(view.InspectionError):
                view.inspect_existing_python(
                    SCANDIR_BAD, root=root, serial4_pack=pack,
                    owner_public_trust=root / "synthetic" / "invalid-trust.pem",
                )

    def test_standalone_cli_inspects_stdin_without_db_files(self):
        root=Path(__file__).resolve().parents[1]
        process=subprocess.run(
            [sys.executable,"-B","-m",
             "ucie_miner.existing_rule_inspection",
             "--ucie-root",str(root)],
            input=SCANDIR_BAD,text=True,capture_output=True,timeout=8,
            cwd=root,
        )
        self.assertEqual(process.returncode,0,process.stderr)
        receipt=json.loads(process.stdout)
        self.assertEqual(receipt["finding_count"],1)
        self.assertEqual(receipt["network_requests"],0)
        self.assertFalse(receipt["auto_promoted"])
        self.assertNotIn("source_text",receipt)


if __name__=="__main__":
    unittest.main()
