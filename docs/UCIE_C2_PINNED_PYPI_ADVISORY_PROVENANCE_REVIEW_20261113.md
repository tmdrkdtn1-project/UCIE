# UCIE C2: official pinned PyPI advisory and provenance inspection

**2026-11-13 KST | STATUS: CUSTOMER_NO_GO**

## Functional change

New first-party module: src/ucie_miner/customer_c2_pypi_advisory_provenance_v01.py

It checks exactly the previously accepted dependency versions, NOT a new
UCIE technical code-mining repository:

- cryptography==50.0.2
- cffi==2.1.1
- pycparser==3.12

On explicit one-shot invocation it queries the official PyPI version-specific
JSON endpoint and fixed per-wheel PEP 740 Integrity API. The code checks
the distribution name/version, exact wheel filename and SHA256, yanked status,
PyPI-disclosed version-specific advisories, withdrawn advisory entries,
and (where served) the declared attestation subject name and digest.

The module never fetches a wheel, runs or installs external code, changes the
customer package, imports owner keys, sends user data, modifies the operating
database, starts a scheduler, or grants any release approval.

## Exact modes

Default safe offline plan, zero network:

    <existing-UCIE-Python> -B -m ucie_miner.customer_c2_pypi_advisory_provenance_v01

Fixed public-only one-shot official metadata inspection:

    <existing-UCIE-Python> -B -m ucie_miner.customer_c2_pypi_advisory_provenance_v01 --public-one-shot

This does NOT read owner files or infer the owner wheelhouse's selected filename
and SHA256. Three public Windows CPython3.15 wheel candidates are used for
metadata-only source checks. The result explicitly records
actual_owner_wheel_captured_and_crosschecked=false.

Separate owner-managed actual wheelhouse crosscheck (not performed by ChatGPT):

    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_c2_pypi_advisory_provenance_v01 --owner-existing-c1-once

Only interactive exact D:\UCIE Windows x64 CPython3.15 owner environment.
The exact phrase REVIEW_UCIE_C2_FIXED_PYPI_METADATA_ONCE is requested
BEFORE any C1 wheel or existing receipt is read. After consent, the
previous C1 SHA+RECORD verifier validates the already captured public wheel
files before comparing that exact filename/SHA to current official PyPI metadata.
No private key, license export, customer release or automatic rule promotion.

## Trust and legal limits

The PyPI package page currently displays provenance for cryptography 50.0.2
but none for cffi 2.1.1 or pycparser 3.12. The exact file-level claims
are checked by the new real one-shot CI. Absence of attestation does not
prove a wheel malicious. A PyPI-served attestation subject with a matching
SHA is not independently cryptographic signature verification: the script
DOES NOT check Sigstore certificates, DSSE signatures or transparency logs.

PyPI version-specific vulnerabilities are an informative OSV-derived snapshot,
not a complete security audit. Zero listed IDs does not mean risk-free.
The program returns no customer GO or rights/security/NOTICE signoff,
even when metadata matches. Existing C2 human legal and third-party security,
independent customer-owner device, C3 entitlement and C5 customer pilot remain
blocked. Previous same-owner vendor-inclusive A-to-B-to-A test is completed
and not rerun.

## Official public references

- https://docs.pypi.org/api/json/
- https://docs.pypi.org/api/integrity/
- https://docs.pypi.org/attestations/consuming-attestations/
- https://pypi.org/project/cryptography/50.0.2/
- https://pypi.org/project/cffi/2.1.1/
- https://pypi.org/project/pycparser/3.12/
- https://cryptography.io/en/50.0.2/changelog/

Tests: tests/test_ucie_c2_pypi_advisory_provenance_v01.py includes 16
source-only cases (PyPI SHA and version pinning, attestation subject,
no phantom signed status, known/withdrawn advisories, invalid/duplicate
metadata and endpoints, and owner consent BEFORE local files).
The dedicated workflow checks live fixed PyPI endpoints only on an isolated
Windows CI runner. No owner C1 wheel or secret was used in CI.

Keep all 18 previously modified owner tracked files untouched. No
git pull/reset/clean, scheduler, C40, miner, daily report or cloud action.
