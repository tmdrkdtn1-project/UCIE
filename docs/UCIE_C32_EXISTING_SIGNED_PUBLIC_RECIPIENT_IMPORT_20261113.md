# UCIE C3.2 — one-time import of EXISTING owner-signed public PR metadata

**Actual feature, not key creation.** This change closes the C3.1 manual-file placement gap for a separate clean offline UCIE recipient. It uses the already merged C3 Ed25519 verifier and already merged C3.1 read-only browser. It never generates, reads, rotates, exports or replaces any existing owner private key.

## Owner-managed inputs, already available or externally authorized

The recipient has a separate `UCIE` checkout with a `.git` directory and missing/empty `runtime`. The owner or independently approved operator provisions the recipient's already agreed PUBLIC verification key at `UCIE/.build_keys/ucie_c3_public_metadata_owner_trust.pem`. That file is **public**, not the owner signing key. Its independently communicated lowercase 32-hex fingerprint and a minimum allowed positive signature serial are provided as arguments, never copied from the signed envelope.

Transfer only these existing PUBLIC-only items into `UCIE/downloaded/` on the recipient:
- `.ucie_b2_public_pr_metadata_v01.json` (bounded public metadata capsule, no patch or original project text)
- `.ucie_b2_public_pr_metadata_v01.sha256`
- `.ucie_c3_public_pr_owner_attestation_v01.json` (detached C3 Ed25519 attestation)

This deliberately does **not** read or copy any owner `*.pem` private key. The `downloaded/` folder is already Git-ignored. The software cannot claim that the public fingerprint or the signed corpus exists on the real owner machine; that is an independent owner-controlled state and was not probed or fabricated.

## Read-only dry run and one-time import commands

After confirmed separate public-key approval and manual placement of existing public files, use the existing installed UCIE Python in the clean **recipient** environment:

    <recipient-python> -B -m ucie_miner.local_public_pr_recipient_import_v01 --recipient-ucie-root <absolute-clean-UCIE-recipient-root> --expected-owner-key-id <preapproved-32-lowercase-hex> --min-serial <approved-positive-floor>

The default command cryptographically verifies the already signed inbox and reports only a safe status. It **does not create any file**.

Perform the one-time import into the clean recipient root and immediately serve the separate read-only UI:

    <recipient-python> -B -m ucie_miner.local_public_pr_recipient_import_v01 --recipient-ucie-root <absolute-clean-UCIE-recipient-root> --expected-owner-key-id <preapproved-32-lowercase-hex> --min-serial <approved-positive-floor> --apply-once --serve --port 0

The signed capsule, exact SHA receipt and detached signature are validated **before** any write. Import makes exactly **three** fixed destination files with exclusive-create, no overwrite. The separate `GET /local/trusted-public` Local V04 screen uses existing C3.1 cryptographic verification on every GET, with no POST, customer approval, source patch application or promotion. Ordinary unsigned V04 routes continue returning HTTP400 when the signed sidecar is present.

## Boundaries and fail-closed conditions

- Any missing/malformed/out-of-date signature, wrong owner key ID/public PEM, altered payload even if the neighboring hash is recalculated, lower-than-accepted serial, noncanonical data, symlinked inbox, existing file name collision, or nonempty operating runtime **rejects import**.
- The import is intentionally non-idempotent: an already imported file **will never be replaced**, even if the bytes match. If the process is interrupted during the three O_EXCL writes, an incomplete import may remain. C3.1 still fails closed and the operator must review and reconcile it manually. There is no automatic delete/rollback.
- An owner-managed serial floor is required to reject old correctly signed data. A recipient system clock and the out-of-band owner key enrollment remain external trust dependencies, not self-proven claims.
- The installed Windows CI uses its **already declared CI cryptography dependency**, a newly installed UCIE first-party wheel, a disposable recipient and an **ephemeral in-memory** Ed25519 key. This is a real crypto and real HTTP functional test, but **not** a physical second Windows device controlled by the owner, not a real owner signature, and not a customer-release rights test.
- C2 independent legal/NOTICE and security clearance, the owner's actual existing trust pin and signed transfer, physical separate Windows recipient acceptance, C3 customer entitlement and C5 private designated pilot remain NO_GO until independently evidenced. Prior same-owner C4 vendor A→B→A is already PASS and is not re-run.

## Automated acceptance

Source tests: `tests/test_ucie_local_public_pr_recipient_import_v01.py`, with 13 ephemeral Ed25519 + positive import / HTTP200 and fail-closed cases.

Real installed native Windows CI: `.github/workflows/ucie-c32-installed-ed25519-recipient.yml` executes `tests/runtime_ucie_c32_installed_crypto_recipient_v01.py` on an ephemeral Windows Python 3.15 runner with the existing declared cryptography provider. It verifies actual installed wheel import, signed GET200, unsigned-route GET400, signature tamper GET400, duplicate/replay/expiry rejection, GET-only/no external network and disposal of all synthetic bytes. No real owner secrets or vendor binaries are included in a customer bundle.

Release remains `CUSTOMER_NO_GO` regardless of green synthetic CI. Do not copy to, overwrite or reset the 18 locally modified tracked D:/UCIE files, do not alter miner/DB/tasks/C40/Cloudflare, and do not merge until exact-head CI tests are green.
