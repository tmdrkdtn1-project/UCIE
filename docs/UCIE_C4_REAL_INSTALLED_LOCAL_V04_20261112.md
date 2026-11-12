# UCIE C4: clean Windows installed Local V04 first-party dependency repair

Date 2026-11-12, UCIE-only, V3 #199.

PR #251 achieved a genuine clean Windows in-place A/B/A CLI and pip uninstall but did not attest the Local V04 web UI. First PR #253 Windows CI reproduced the exact blocker: ModuleNotFoundError for cryptography while installing and probing UCIE first-party wheel with no external dependencies.

Root cause: the Local V04 catalog imports the public-candidate read-only library search, which eagerly imported signed candidate automated QA, which eagerly imports the cryptography-dependent signed-release modules. Merely opening a public read-only guide must NOT demand or bypass a vendor signing library.

Fix: place one shared fail-closed public-only unverified Stage12 handoff validation in verification_handoff, read it directly from library_search, and make automated_candidate_qa delegate to the SAME function. Preserve the exact four public upstream PR source pins, rejection of forged/approved candidate states, owner signed release modules and cryptography verification. Require the signed verification path to fail when cryptography is missing.

Actual QA scope: Stage current UCIE first-party-only committed source with its manifest in an ephemeral Windows runner, build an exact byte-preserving RECORD-verified first-party wheel, install in one real disposable Python3.15 venv with pip --isolated --no-index --no-deps, execute all four first-party synthetic engines, and open a real 127.0.0.1 web server with 5 GET routes and a negative POST 405 check. Do not claim current-source wheel is the old immutable A/B; no vendor wheel or binary code is installed. Independent untrusted third-party rights, native ABI, C2 security, C3 customer signature, C4 second owner-controlled full recipient, C5 customer pilot and entire commercial product remain NO_GO.

Owner D:/UCIE tracked edits must not be overwritten. No operating DB, C40, scheduler, Local V1 resident service, Cloudflare or daily 09:00 HOLD change. No other-project data, network feed, new collector, customer data, artifact upload or customer distribution. Final customer status: UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_NO_GO.
