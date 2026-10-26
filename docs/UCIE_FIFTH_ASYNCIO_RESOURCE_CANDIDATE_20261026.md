# UCIE fifth prevention-rule candidate: asyncio pre-transport resource leak

## Decision and source pin

**Candidate only:** `PY_ASYNCIO_PROTOCOL_FACTORY_PRETRANSPORT_LEAK`

- Official upstream: [python/cpython PR #156401](https://github.com/python/cpython/pull/156401), merged **2026-09-05**.
- Before: `e2118b0ac21191bfeecdc97758a87d88ffdda154`, `Lib/asyncio/base_events.py` Git blob `f26fba175b63cd72e472f0c529123f08b47918b1`.
- After: `ba4a0790aa8438ccd847e86910f71c9823849d05`, same file blob `90269c936555cb59c8b190416986c2a70ed3ec66`.
- Upstream changed three `protocol_factory()` call sites: `create_datagram_endpoint` (socket), `connect_read_pipe`, and `connect_write_pipe` (pipe). An exception handler now closes the associated resource if the factory raises before the transport owns it.
- The upstream PR describes additional ownership/transport concerns; **this candidate targets only the explicit protocol-factory exception gap**, not every possible transport-creation leak.

## Implemented behavior

`src/ucie_miner/static_asyncio_resource.py` parses explicitly supplied inert Python text with the standard library `ast`, without running or importing that text. It detects the narrowly specified upstream structure: an asynchronous method with the upstream name, `protocol = protocol_factory()`, followed by its respective `self._make_*_transport(resource, protocol, ...)`, where the factory call is not guarded by an exception handler/finally explicitly closing the same resource.

**Output is a human-review candidate**. A static match cannot prove that the protocol factory will raise, that the caller owns the resource, or that an installed Python interpreter is vulnerable. A missing match is not a safety finding. Bounds: input 128 KiB, 20,000 AST nodes, 20 findings; invalid input fails closed.

The separate scanner is not one of the four owner-signed rules. **No automatic rule approval, Rulepack Serial 5, signing, distribution, runtime operation, source execution, private source access, or persistent learning occurs.**

## Local-only manual entrypoint

For explicitly approved and source-pinned public snippets (or UCIE-authored synthetic examples) only:

```powershell
$env:PYTHONPATH = 'D:\UCIE\src'
@'
class EventLoop:
    async def connect_read_pipe(self, protocol_factory, pipe):
        protocol = protocol_factory()
        waiter = self.create_future()
        transport = self._make_read_pipe_transport(pipe, protocol, waiter)
        return transport
'@ | D:\UCIE\.venv\Scripts\python.exe -B -m ucie_miner.static_asyncio_resource
```

This is a **synthetic usage sample**, not an upstream runtime reproduction. The code is read from standard input; no file discovery or untrusted code execution takes place.

## Gates before adding to any signed Rulepack

1. Confirm pinned upstream source before/after static inspection and cross-version applicability; merged CPython `main` is not proof of a particular fixed release.
2. Independent runtime regression and false-positive review, including cleanup ownership cases.
3. License/provenance/rights review and explicit independent QA or owner-risk approval according to the existing release contract.
4. Separate owner selection and signing. Never silently mutate the existing Serial 1, 2 or 4 packs.

CI's `tests/test_ucie_static_asyncio_resource.py` covers the three upstream-shaped pre/post branches, exception cleanup correctness, unrelated and nested functions, input bounds, and inert command-line execution. The tests use excerpts, **not full pre/post upstream file execution or native crash reproduction**.
