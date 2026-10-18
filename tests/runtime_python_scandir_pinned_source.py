"""One-shot, read-only official CPython source-revision proof for scandir.

NEVER reproduce the unfixed raw native close/next race. The regression
mitigation is tested separately with UCIE GuardedScandir in normal CI.
No external Python code is executed or installed; only official raw GitHub
source files are hashed and inspected in memory on an ephemeral CI runner.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request

URL_BASE = "https://raw.githubusercontent.com/python/cpython/"
RELEASE = ("v3.15.0", "0b42b059541d351423bb604586058363f7d0f35f")
PATCH = (
    "999a046b24cff4ba0e72b574196721f66bd08237",
    "bec305a4042c49d23410bf0c55c976ed78fe3fc1",
)
MARKERS = (
    b"PyMutex read_mutex;",
    b"_Py_atomic_store_uint8(&iterator->closed",
    b"PyMutex_Lock(&iterator->read_mutex)",
)


def fetch_git_blob(ref: str, expected_blob: str) -> bytes:
    url = URL_BASE + ref + "/Modules/posixmodule.c"
    with urllib.request.urlopen(urllib.request.Request(
            url, headers={"User-Agent": "UCIE-pinned-public-readonly"}),
            timeout=25) as result:
        if result.status != 200 or result.geturl() != url:
            raise RuntimeError("noncanonical official source response")
        raw = result.read(750001)
    if not 400000 < len(raw) <= 750000:
        raise RuntimeError("unexpected upstream source size")
    identity = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()
    if identity != expected_blob:
        raise RuntimeError("source not the exact published Git blob")
    return raw


def main() -> None:
    if sys.version_info[:2] != (3, 15):
        raise RuntimeError("one-shot source check runs on Python 3.15")
    unfixed = fetch_git_blob(*RELEASE)
    patched = fetch_git_blob(*PATCH)
    release_has_fix = all(marker in unfixed for marker in MARKERS)
    patch_has_fix = all(marker in patched for marker in MARKERS)
    if release_has_fix or not patch_has_fix:
        raise RuntimeError("expected release/master source difference absent")
    print("UCIE_FOURTH_SOURCE_EVIDENCE=" + json.dumps({
        "schema": "UCIE_SCANDIR_PUBLIC_SOURCE_DIFFERENTIAL_V1",
        "source": "python/cpython",
        "upstream_pr": "https://github.com/python/cpython/pull/153462",
        "upstream_merge_sha": PATCH[0],
        "patched_git_blob_sha": PATCH[1],
        "release_version": "v3.15.0",
        "release_git_blob_sha": RELEASE[1],
        "release_contains_upstream_mutex_fix": release_has_fix,
        "merged_main_contains_mutex_fix": patch_has_fix,
        "actual_binary_correspondence_verified": False,
        "unsafe_native_race_executed": False,
        "native_crash_reproduced": False,
        "owner_risk_accepted": False,
        "automatic_rule_promotion": False,
        "production_release_authorized": False,
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print("UCIE_SCANDIR_SOURCE_NO_GO=" + str(exc), file=sys.stderr)
        raise SystemExit(1)
