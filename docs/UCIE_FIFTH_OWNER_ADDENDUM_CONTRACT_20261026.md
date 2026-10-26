# UCIE fifth owner-signed addendum — one manual approval, no Serial4 reissue

**State before explicit owner action: CODE_READY_ONLY, not signed or activated.**

The fifth candidate \`PY_ASYNCIO_PROTOCOL_FACTORY_PRETRANSPORT_LEAK\` has
approved public CPython source proof, a Python 3.15.0 host runtime observation
with mock socket/pipe objects, and an inert AST detection implementation.
This document introduces a new opt-in **fifth rule only** owner-signed addendum.
The existing 4-rule **Serial 4 ZIP remains byte-for-byte immutable**.

## Why an addendum rather than silently extending the original pack?

The four-rule mixed owner release format and rule matcher have *exactly four*
allowlisted IDs and fixed evidence. Extending those signed contents would
silently alter the trust contract. The addendum instead:

1. Verifies the original signed Serial 4 package, including its seven-day
   expiry, rule IDs, source commit, trust key and signature.
2. Pins the SHA-256 of that exact parent ZIP and uses the **same owner key**.
3. Checks a passing **live main-push 4-job CI** whose head equals a clean
   owner UCIE checkout.
4. Requires **new owner confirmation and a separate fifth-rule risk phrase**.
5. Issues a new Serial 5-or-higher **fifth-only signed addendum**, not an
   automatic five-rule replacement.
6. Verifies that separate ZIP and supports an inert Python-only fifth scan.

There is no automatic signing, rule promotion, scheduling, source execution,
auto-fix or external deployment. The addendum's static match remains a
**manual review candidate**, not proof of a bug in arbitrary input.

## Human authorization boundary

Prior Serial 4 consent **does not** authorize the fifth. The exact owner
terminal phrases for this implementation are:

- Confirmation:
  \`AUTHORIZE_UCIE_FIFTH_RULE_MANUAL_OWNER_RISK_SERIAL5\`
- Risk acceptance:
  \`I_ACCEPT_FIFTH_ASYNCIO_MOCK_RUNTIME_AND_NO_INDEPENDENT_QA_LICENSE_SIGNOFF_OR_FIXED_RELEASE_COVERAGE\`

These phrases MUST be supplied only after a new, informed owner decision.
**Do not run a signing command based solely on "continue development."**
The private key never enters ChatGPT or the public repository.

Known limitations requiring owner review: no independent human QA, no legal
license clearance, no OS-level socket leak measurement, and no verified fixed
Python *release*. Official CPython \`v3.15.0\`, \`v3.15.1\`, and \`v3.14.9\`
sources retained the pre-fix shape. The CPython main fix is PR #156401,
merge \`ba4a0790aa8438ccd847e86910f71c9823849d05\`.

## Implemented CLI (only when owner later approves)

- \`python -B -m ucie_public.cli publish-fifth-owner-addendum\`
  requires the existing owner-private path inside that **clean checkout's**
  \`.build_keys/production/private_production.pem\`, \`--base-pack\`,
  \`--owner-trust\`, \`--output\`, \`--run-id\`, \`--serial 5\`,
  \`--confirm\`, and \`--accept-risk\`. It refuses an existing output ZIP.
- \`python -B -m ucie_public.cli verify-fifth-owner-addendum\`
  takes \`--pack\`, \`--base-pack\`, \`--owner-trust\`, \`--min-serial 5\`.
  Verification uses only the *public* trust key.
- \`python -B -m ucie_public.cli scan-fifth-owner-addendum-stdin\`
  has the same verification arguments and accepts at most 128 KiB of
  explicitly supplied **approved public** Python source via standard input.
  Source is parsed with AST only, not executed.

The owner signing checkout must contain the exact CI-verified main source,
be clean on \`main\`, and have the owner key at the fixed local path. The user's
normal \`D:\UCIE\` development worktree might contain uncommitted edits;
**never clean, reset or checkout over it** just to make a signing command
pass. A dedicated existing clean UCIE release checkout is preferable when
owner-authorized. The existing Serial 4 is immutable and must not be
re-signed or overwritten.

## Minimum focused acceptance

\`tests/test_ucie_fifth_owner_addendum.py\` builds temporary synthetic
production-purpose keys and synthetic parent identity using mocks. It tests
signature verify, signed fifth scan, refusal without explicit fifth consent,
tamper, parent digest mismatch, expiry, no overwrite, live CI rejection and
key mismatch. **These mock tests are not an owner signing action.**

The preceding actual-host fifth candidate detector and Python runtime
observation were performed separately; this addendum contract does not
replay those tests or change those implementations.
