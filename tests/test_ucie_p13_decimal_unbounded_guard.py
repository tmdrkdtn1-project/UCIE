"""P13 Decimal AST guard candidates: precise, inert and bounded."""
from __future__ import annotations
import unittest

from ucie_miner import p13_decimal_unbounded_guard as guard

PROBLEM = '''
import _pydecimal as d
with d.localcontext() as c:
    c.prec = d.MAX_PREC
    c.Emax = d.MAX_EMAX
    c.Emin = d.MIN_EMIN
    x = d.Decimal("1")
    remainder = x % 1
    pair = divmod(x, 1)
'''
NORMAL = '''
import _pydecimal as d
with d.localcontext() as c:
    c.prec = 28
    x = d.Decimal("1")
    remainder = x % 1
    pair = divmod(x, 1)
'''
ACCELERATED = PROBLEM.replace("_pydecimal", "decimal")
FROM = '''
from _pydecimal import Decimal as D, localcontext as lc, MAX_PREC as MP
with lc() as c:
    c.prec = MP
    x = D("1")
    value = x % 1
'''


class P13DecimalUnboundedGuardTests(unittest.TestCase):
    def test_flags_only_explicit_maxprec_pure_python_decimal_ops(self):
        r = guard.inspect_source(PROBLEM)
        self.assertEqual(r["findings_count"], 2)
        self.assertEqual(
            {x["risk"] for x in r["findings"]}, {"MODULO", "DIVMOD"})
        self.assertFalse(r["auto_promoted"])
        self.assertTrue(all(not x["source_fix_proven"] for x in r["findings"]))
        self.assertEqual(r["database_writes"], 0)
        self.assertEqual(r["network_requests"], 0)

    def test_normal_precision_not_falsely_flagged(self):
        self.assertEqual(guard.inspect_source(NORMAL)["findings_count"], 0)

    def test_c_decimal_accelerator_not_falsely_flagged(self):
        self.assertEqual(guard.inspect_source(ACCELERATED)["findings_count"], 0)

    def test_from_import_syntax_detected(self):
        r = guard.inspect_source(FROM)
        self.assertEqual(r["findings_count"], 1)
        self.assertEqual(r["findings"][0]["risk"], "MODULO")

    def test_no_named_context_not_flagged(self):
        source = '''
import _pydecimal as d
x = d.Decimal("1")
with d.localcontext():
    y = x % 1
'''
        self.assertEqual(guard.inspect_source(source)["findings_count"], 0)

    def test_non_decimal_lhs_not_flagged(self):
        source = '''
import _pydecimal as d
with d.localcontext() as c:
    c.prec = d.MAX_PREC
    x = 4
    y = x % 1
'''
        self.assertEqual(guard.inspect_source(source)["findings_count"], 0)

    def test_decimal_variable_reassigned_to_non_decimal_not_flagged(self):
        source = '''
import _pydecimal as d
with d.localcontext() as c:
    c.prec = d.MAX_PREC
    x = d.Decimal("1")
    x = 2
    y = x % 1
'''
        self.assertEqual(guard.inspect_source(source)["findings_count"], 0)

    def test_reject_code_without_running_it(self):
        dangerous = '''
import _pydecimal as d
import os
with d.localcontext() as c:
    c.prec = d.MAX_PREC
    x = d.Decimal("1")
    z = x % 1
os.system("NEVER_EXECUTE_THIS")
'''
        self.assertEqual(guard.inspect_source(dangerous)["findings_count"], 1)
        # No os.system monkeypatch required because ast.parse is not execution.

    def test_reject_unbounded_input(self):
        with self.assertRaises(guard.DecimalGuardError):
            guard.inspect_source("a=" + "0" * 21000)

    def test_invalid_source_fails_closed(self):
        with self.assertRaises(guard.DecimalGuardError):
            guard.inspect_source("with invalid := :")

    def test_floordiv_control_keeps_separate_label(self):
        source = PROBLEM.replace("remainder = x % 1", "quotient = x // 1")
        r = guard.inspect_source(source)
        self.assertEqual({x["risk"] for x in r["findings"]},
                         {"FLOORDIV_CONTROL", "DIVMOD"})

    def test_no_original_source_text_leaked(self):
        r = guard.inspect_source(PROBLEM)
        self.assertIn("source_sha256", r)
        self.assertEqual(len(r["source_sha256"]), 64)
        self.assertNotIn("source_text", r)
        self.assertNotIn(PROBLEM, str(r))


if __name__ == "__main__":
    unittest.main()
