# UCIE B3/B4 consolidated designated-customer release engineering bundle

Date: 2026-11-13 KST. Roadmap: issue #199. UCIE-only.
**Customer release decision remains NO_GO.** This one code bundle is not a signed customer installer, contract, legal security approval or pilot.

## Delivered technical components

The already merged C3 (#259), C3.1 (#260), C3.2 (#261), C2 PyPI
review (#262) and the proven owner-local same-host vendor-inclusive C4
A-to-B-to-A (#254) are reused, not regenerated.

1. src/ucie_miner/customer_private_entitlement_v01.py:
   Real recipient-side Ed25519 cryptographic verification with a NEW
   purpose-separated customer product signature scope, not the C3 public
   PR metadata scope or demonstration Rulepack. Canonical payload binds
   EXACT first-party wheel SHA256, all 3 approved C1 vendor wheel SHA256s,
   four product pillars, version 0.1.0, anonymous recipient token SHA256,
   separately specified rights-review packet SHA256, min accepted serial,
   issued/expiry and separately approved owner public-key fingerprint.
   No owner private keys are read/generated, no customer entitlement issued
   and no independent legal/business approval is inferred from a signature
   or a rights-document hash. Ephemeral private-key helper is for synthetic
   tests only, never an approved customer issuer.
2. tests/runtime_ucie_b3_b4_clean_full_vendor_release_v01.py:
   Real disposable GitHub Windows Python3.15 product test. It reads
   the CURRENT reviewed UCIE checkout source, stages/rehashes every
   first-party file and builds the existing QA wheel. On a separate
   ephemeral Windows runner ONLY, downloads EXACT pinned versions
   cryptography==50.0.2, cffi==2.1.1, pycparser==3.12 from official
   PyPI distribution (NOT public code mining), checks external official
   version JSON sha256 and each wheel internal RECORD, then writes a
   four-wheel SHA-locked requirements manifest. A NEW venv performs
   pip --no-index --require-hashes with resolver enabled, pip check,
   REAL native AESGCM/CFFI/pycparser probes and native Ed25519 customer
   scope verification (with in-memory synthetic key only).
   Four installed functional pillars and actual 127.0.0.1 Local V04:
   5 product health/routes plus 8 official reference GET routes; denied
   unsafe PR review, then real pip uninstall, absence check, reinstall
   SAME current product from identical hash-locked wheels, four-pillar
   behavior comparison, second uninstall, scratch cleanup.
   Corrupted vendor wheel must be detected BEFORE pip sees it.
3. Focused actual Ed25519 unit tests and CI strict scope/CLI-policy tests,
   plus one dedicated complete-real-vendor Windows workflow. Existing
   standard Win/Ubuntu Python3.13/3.15 CI must pass on exact PR HEAD.

## Complete C0-C5 customer release table (never just one blocker)

| Gate | Technical basis or advance | Required real completion evidence |
|---|---|---|
| C0 4 pillars | Existing full source and installed 4-pillar product checks | Complete feature/approved SkillBook inventory plus actual independent customer-use acceptance |
| C1 installer | Current source wheel, 3 vendor pinned SHA/RECORD and offline Windows full install/uninstall/reinstall | Approved versioned Windows installer/config, all assets, live signed update/rollback/uninstall/repair supported on customer devices |
| C2 security/rights | Existing C1 captures, C2 LICENSE/NOTICE packet, official advisory observations and new native probes | Human first-party and third-party licenses/NOTICE/SBOM, independent security/issuer Sigstore provenance review and explicit owner clearance |
| C3 signed entitlements | Full-product/recipient/vendor hashes bound with separate Ed25519 purpose, anti-replay/expiry/identity checks | Genuine owner-approved independent public trust pin, existing owner private key management and REAL signed customer-specific contract/activation/revocation, without exposing customer identity |
| C4 second recipient | Independent ephemeral GitHub Windows full native installer/4-pillar/local UI and cleanup QA | Separate OWNER-CONTROLLED physical Windows complete customer installer/license, update/rollback/install repair acceptance with real owner-provided artifacts |
| C5 paid customer | Functional and policy QA interface only | Named owner-approved designated pilot contract, actual customer installed/used/accepted product, rights/security review and explicit final distribution GO |

A matching Ed25519 signature and a rights document hash **DO NOT prove**
independent legal/contract review. A clean GitHub VM is not a separately
owner-managed actual recipient. Source QA wheel is NOT a commercial
installer. A zero-active-advisory PyPI snapshot never proves security.

## ONE GROUPED owner/recipient acceptance session

After this PR's exact-head tests pass, the final external acceptance
inputs should be collected together rather than 1 request per chat:

1. Existing C1 owner-captured three wheel SHA receipts AND original C2
   vendor licenses/NOTICE and owner legal/security approvals (previous
   owner-only C2 tools already exist; do not invent replacement capture).
2. Existing owner-approved purpose-specific product signing trust and
   revocation serial policy; owner private keys stay on the actual machine.
   The public key and fingerprint must be approved independently out
   of band. The C3 public PR metadata key is NOT auto-authorized for
   private product signing.
3. Reviewed complete 4-pillar product version, human SkillBook rights,
   designated customer's license/contract terms, actual product SHA
   and genuine signed customer entitlement. No customer names/IDs
   in this public repository, chat receipts or CI.
4. Separate owner-controlled clean Windows recipient capable of
   offline install, genuine native dependency behavior, versioned
   update/rollback/uninstall and final signed proof.
5. Real C5 customer pilot acceptance and explicit owner GO AFTER
   security, rights, technical install and customer tests.

Current tools cannot read ignored .build_keys private key paths or operate
a separate physical Windows computer. Their inaccessibility does not imply
those owner assets do not exist. No new keys should be generated without
an explicit owner decision.

## Rules

No private customer data, keys, license material or vendor binaries
committed to GitHub. No official source allowlist expansion for UCIE
public evidence miner. PyPI dependency downloads only in ephemeral CI;
no distribution/public hosting/automatic rule promotion. Existing
D:/UCIE owner modified 18 tracked files remain untouched. No task
scheduler/public miner/operating SQLite/C40/Cloudflare/resident UI changes.
Human legal and actual customer GO ALWAYS separate from CI.
