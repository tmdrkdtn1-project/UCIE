"""UCIE-only one-shot knowledge import; NEVER registered as a scheduled task."""
from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if os.name == "nt" and (ROOT.resolve() != Path("D:/UCIE").resolve() or ROOT.is_symlink()):
    raise SystemExit("FAIL_CLOSED: expected D:/UCIE checkout")
sys.path.insert(0,str(ROOT/"src"))
from ucie_miner.knowledge import import_miner_candidates

if __name__=="__main__":
    try:
        result=import_miner_candidates(ROOT)
    except Exception as exc:
        print(json.dumps({"status":"FAIL_CLOSED","error_type":type(exc).__name__}))
        raise SystemExit(2)
    print(json.dumps(result,sort_keys=True))
