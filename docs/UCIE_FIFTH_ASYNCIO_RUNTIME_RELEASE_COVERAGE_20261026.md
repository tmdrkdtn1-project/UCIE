# UCIE fifth rule: real Python 3.15.0 runtime + official release-tag evidence (2026-10-26)

## Decision

**`PY_ASYNCIO_PROTOCOL_FACTORY_PRETRANSPORT_LEAK` is runtime-grounded as an
unfixed resource-cleanup gap in the observed owner-host Python 3.15.0.**
It remains a **candidate-only** rule, outside the existing four-rule signed
Rulepack. Neither automatically approving nor signing a new Rulepack is authorized.

The issue involves `asyncio` invoking `protocol_factory()` after it has taken
or created a socket/pipe but before a transport owns that resource. If the
factory throws, the original implementation propagates the exception without
closing the acquired resource.

- Official issue: https://github.com/python/cpython/issues/156400
- Official fixed PR: https://github.com/python/cpython/pull/156401
- Merged upstream main code commit: `ba4a0790aa8438ccd847e86910f71c9823849d05`
- Merged on: **2026-09-05 UTC**
- Fixed upstream file: `Lib/asyncio/base_events.py`; blob
  `90269c936555cb59c8b190416986c2a70ed3ec66`

## Actual isolated UCIE-host runtime observation

Executed one file through the UCIE-only one-file test bridge:

`tests/test_ucie_fifth_rule_actual_runtime_20261026.py`

- Interpreter actually executing: **Python 3.15.0**
- Command boundary: one authorized UCIE `unittest` file.
- Host test exit: `0`, **1 test ran, OK**.
- UCIE-owned `factory()` raises `UCIEControlledError` for each API call.
- All resources are `unittest.mock.Mock()` objects; no real sockets or
  pipes, no externally sourced code, no network, and no native crash attempt.

| Runtime method | Factory exception propagated | Mock resource `close()` called |
| --- | --- | --- |
| `create_datagram_endpoint()` | Yes | **No** |
| `connect_read_pipe()` | Yes | **No** |
| `connect_write_pipe()` | Yes | **No** |

Observed receipt status: `UNPATCHED_FACTORY_CLEANUP_GAP_OBSERVED`.

**Interpretation:** This is an actual execution of the installed interpreter's
standard-library `asyncio` code, not an AST-only/synthetic source scan.
It proves the observable cleanup-call omission in these controlled
factory-error paths. Mock objects are not real socket/file descriptors;
the test does **not** measure OS resource leakage, production risk magnitude,
or a real network failure. Passing the test proves the bounded observation
completed, not that the Python interpreter is safe or fixed.

## Official release source comparison (fixed release inclusion)

For each exact signed/annotated upstream release tag, the official
`Lib/asyncio/base_events.py` file still contains the unguarded
`protocol = protocol_factory()` at all three methods:

| Tag | Tagged commit | File Git blob | Three factory calls guarded by close? |
| --- | --- | --- | --- |
| `v3.15.0` (2026-10-09 tag) | `d220409a13b77de7a6c30abe16ea90db01528edc` | `7b6a67023381fec69a4cd074f5888dc5c29a4eaf` | **No / No / No** |
| `v3.15.1` (2026-10-21 tag) | `c37e74cb6bcdadcd5f46f289498f6b3298ddee61` | `59c61f9ba657a1228b5e02dafdd86f4586b3b63d` | **No / No / No** |
| `v3.14.9` (2026-10-21 tag) | `ead82c07db1f111d613926ed1b6667411d768125` | `ed47f757a26144b87b514c99b5a945772b59011f` | **No / No / No** |

Tag sources:
- https://github.com/python/cpython/blob/v3.15.0/Lib/asyncio/base_events.py
- https://github.com/python/cpython/blob/v3.15.1/Lib/asyncio/base_events.py
- https://github.com/python/cpython/blob/v3.14.9/Lib/asyncio/base_events.py
- Compared fixed main commit:
  https://github.com/python/cpython/blob/ba4a0790aa8438ccd847e86910f71c9823849d05/Lib/asyncio/base_events.py

These are **release source** observations, not executions of all listed
versions. Confirmed **fix absence** in three exact releases does not
establish fix inclusion in any other release. The actual host run is only
on 3.15.0; no assertion is made about other CPython versions or about
whether `_make_*_transport` exceptions are fully cleaned up.

## Allowed scope and next gate

The existing separate `src/ucie_miner/static_asyncio_resource.py`
detector can propose a **human-review candidate** for the narrowly
identified pattern without executing the supplied source.

- No new signed Serial 5, no automatic rule promotion, auto-fix,
  external release, scheduler installation, or private project scanning.
- No independent human QA, license approval, or full false-positive
  study is asserted.
- Before signed release: independent validation of the detection
  boundary/ownership semantics, version scope, and **separate explicit**
  owner risk acceptance. The previous signed Serial 4 is immutable.

This evidence update does **not** change the signed owner release,
production scanner, miner schedule, or any existing rule definitions.
