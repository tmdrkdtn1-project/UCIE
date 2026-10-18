# Stage18 — first CPython 3.15 remote-debugging -X spelling regression

## Scope and evidence

Only `python/cpython#159014`, merge
`91248026c8a41910098032dd23f9a05ad2d9b513`,
rule `PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO`.

- Original Python issue: [cpython #159010](https://github.com/python/cpython/issues/159010)
- [Main documentation PR #159014](https://github.com/python/cpython/pull/159014), merged 2026-10-14 13:18:20 UTC; **four spelling fixes** in
  `Doc/howto/remote_debugging.rst` and `Doc/using/cmdline.rst`
- [3.14 documentation backport #159413](https://github.com/python/cpython/pull/159413), merged 2026-10-14 15:10:35 UTC;
  commit `0d214f87921ab9b858cda64c290d89081335772f`
- [3.15 documentation backport #159414](https://github.com/python/cpython/pull/159414), merged 2026-10-14 15:09:58 UTC;
  commit `cf0c41f716871a8d19d56916e0be59d3beb887d5`
- At the earlier `v3.15.0` annotated tag (2026-10-09),
  `Python/initconfig.c` recognizes only `disable-remote-debug` while
  the tagged documentation retains `disable_remote_debug`. Thus the
  **documentation correction was not included in that tag**; the PR
  did not change Python binary behavior. Do not infer release inclusion
  from a merged maintenance branch; verify each later release separately.
- [Upstream CPython license (tag v3.15.0)](https://github.com/python/cpython/blob/v3.15.0/LICENSE)
  states Python Software Foundation License Version 2. This is a source
  metadata observation, **not** an independent legal signoff.

## Safe behavior and correct call

The unsupported underscore spelling is silently ignored by CPython -X,
so remote-debugging support can remain enabled when an operator expected
a defense-in-depth disable switch:

```text
Wrong:   python -X disable_remote_debug ...
Correct: python -X disable-remote-debug ...
```

This is a **configuration hardening bypass due to copied incorrect docs**,
not evidence of an independent remote-code-execution exploit. Platform
capabilities and OS process permissions remain relevant.

## Existing owner-host observation

Owner-provided console output for Windows CPython 3.15.0:

```text
PythonRuntime        : 3 15 cpython
BaselineEnabled      : True
WrongOptionEnabled   : True
CorrectOptionEnabled : False
RuntimeRegression    : BEHAVIOR_CONFIRMED
```

This is an **operator-reported local result**, not an independently attested
host, reviewer identity, or signed evidence. UCIE previously recorded
independent of owner *ephemeral CI runner* Python 3.15 checks in both Linux
and Windows on [UCIE main workflow 39134118749](https://github.com/tmdrkdtn1-project/UCIE/actions/runs/39134118749).
These are UCIE-authored automated tests, not third-party independent QA.

## Stage18 operator-invoked read-only command

After the Stage18 code has reached `D:\UCIE`, run:

```powershell
Set-Location 'D:\UCIE'
& '.\.venv\Scripts\python.exe' -B -m ucie_miner inspect-stage18-first-rule --local-probe
```

The command first validates the actual Stage17/Stage12 candidate ledger
and Stage16 bounded aggregate evidence. **It refuses to run a probe if the
first-rule candidate is missing, ambiguous, unpinned, or not in the
independent-review lane.** It then uses *only UCIE-authored inert fixed*
three `-I -B -X` subprocess cases, no shell, no upstream code execution,
no network and no runtime/DB file writes. Expected status when supported:

`LOCAL_RUNTIME_BEHAVIOR_OBSERVED_REVIEW_REQUIRED`.

Without `--local-probe`, the same command only inspects and reports
`LOCAL_OBSERVATION_NOT_REQUESTED_NO_GO`; no subprocess is created.
Unexpected results, Python versions other than CPython 3.15, and
subprocess errors are `NO_GO`. The printed SHA-256 is merely a checksum,
not an attestation or signature.

**Hard limits:** This command is not scheduled, does not access external
projects, and never permits automatic promotions, signing, owner approval,
independent security QA PASS, legal approval or deployment. Stage17's
68 candidates and 67 unsupported recipes remain unchanged.
