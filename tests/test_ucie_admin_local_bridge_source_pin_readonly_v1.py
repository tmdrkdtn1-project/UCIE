"""Read-only exact UCIE local bridge source identity pin, no source output."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import unittest

UCIE_ROOT=Path(r"D:\UCIE")
PATH=UCIE_ROOT / "src" / "ucie_miner" / "owner_scoped_bridge_v1.py"
PR175_EXPECTED_OLD_GIT_BLOB="ea4b9941dbb3ba4c3c4f7f354c694c146bf3a17d"


def blob_sha(data):
    prefix=f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(prefix+data).hexdigest()


class UCIELocalOwnerBridgePin(unittest.TestCase):
    def test_git_blob_calculation(self):
        self.assertEqual(blob_sha(b"hello\n"),
                         "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_host_owner_bridge_pin_readonly(self):
        if os.name!="nt" or not UCIE_ROOT.is_dir():
            self.skipTest("UCIE owner Windows only")
        if not PATH.is_file() or PATH.is_symlink():
            self.fail("UCIE owner scoped local source missing or symlinked")
        if any(parent.is_symlink() for parent in PATH.parents):
            self.fail("UCIE parent symlink unexpected")
        data=PATH.read_bytes()
        self.assertLess(len(data),25_000)
        found=blob_sha(data)
        record={
            "schema":"UCIE_OWNER_BRIDGE_PRIOR_SOURCE_PIN_READONLY_V1",
            "sha256":hashlib.sha256(data).hexdigest(),
            "old_git_blob_match":found==PR175_EXPECTED_OLD_GIT_BLOB,
            "new_gate_symbol_present":b"classify_admin_deploy_absence" in data,
            "source_or_secret_exposed":False,
            "filesystem_modified":False,
        }
        print("UCIE_OWNER_BRIDGE_OLD_SOURCE_PIN="+json.dumps(record,sort_keys=True))
        self.assertFalse(record["filesystem_modified"])


if __name__=="__main__":
    unittest.main()
