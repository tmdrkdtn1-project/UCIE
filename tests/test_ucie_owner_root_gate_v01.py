"""One targeted acceptance for the source-only portability gate.

No test creates, moves, stops or registers owner tasks, DBs, tunnels or data.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
SPEC = importlib.util.spec_from_file_location(
    'ucie_owner_root_gate_v01', SCRIPTS / 'ucie_owner_root_gate_v01.py')
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class OwnerRootGateTests(unittest.TestCase):
    def test_legacy_is_unchanged_only_without_relocation_flag(self):
        self.assertEqual(GATE.classify_root('D:/UCIE', platform='nt', relocated=False),
                         'LEGACY')
        with self.assertRaises(GATE.OwnerRootError):
            GATE.classify_root('D:/UCIE', platform='nt', relocated=True)

    def test_new_root_requires_explicit_flag_and_exact_parent(self):
        with self.assertRaises(GATE.OwnerRootError):
            GATE.classify_root('D:/UCIE_PROJECT/UCIE', platform='nt', relocated=False)
        self.assertEqual(GATE.classify_root(
            'D:/UCIE_PROJECT/UCIE', platform='nt', relocated=True),
            'RELOCATED_CONDITIONALLY')
        for bad in ('D:/UCIE_PROJECT', 'D:/UCIE_PROJECT/OTHER', 'D:/OTHER/UCIE',
                    'D:/UCIE_PROJECT/UCIE/../UNCHECKED', 'E:/UCIE_PROJECT/UCIE'):
            with self.subTest(bad=bad), self.assertRaises(GATE.OwnerRootError):
                GATE.classify_root(bad, platform='nt', relocated=True)

    def test_nonwindows_flag_is_not_a_runtime_bypass(self):
        with self.assertRaises(GATE.OwnerRootError):
            GATE.classify_root('D:/UCIE_PROJECT/UCIE', platform='posix', relocated=True)
        self.assertEqual(GATE.require_owner_runtime_root(Path('/tmp'),
                         platform='posix'), 'LEGACY_NONWINDOWS_TEST_ONLY')

    def test_missing_runtime_and_marker_cannot_enable_relocated_mode(self):
        with tempfile.TemporaryDirectory(prefix='UCIE_ROOT_GATE_TEST_') as td:
            root = Path(td)
            with self.assertRaises(GATE.OwnerRootError):
                GATE.require_owner_runtime_root(root, relocated=True, platform='nt')

    def test_gate_has_no_write_or_task_operations(self):
        text = (SCRIPTS / 'ucie_owner_root_gate_v01.py').read_text('utf-8')
        for token in ('Register-ScheduledTask', 'Set-ScheduledTask', 'Stop-ScheduledTask',
                      'os.remove(', 'unlink(', 'mkdir(', 'write_bytes(', 'write_text(',
                      'git reset', 'git clean', 'cloudflared', 'shutil.move('):
            self.assertNotIn(token, text)
        self.assertIn('MARKER_BYTES', text)
        self.assertIn('RELOCATED_RUNTIME_INCOMPLETE', text)


if __name__ == '__main__':
    unittest.main()
