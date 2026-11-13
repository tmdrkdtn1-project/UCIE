# UCIE C2: five existing LICENSE originals physically included in private QA bundle (2026-11-13)

This implements a REAL missing file-copy capability for the preexisting B3/B4 private technical bundle; it is **not** yet a customer-releasable rights appendix.

**Previously done, not repeated:** owner original 3 vendor wheel PyPI digests matched 3/3; five SHA-verified LICENSE originals 15,755 bytes already exist under the owner-ignored \`downloaded/ucie_c2_owner_only_license_review_v01\`. The ChatGPT bridge cannot read those protected originals, and this PR does not run a real owner bundle build or transfer copyrighted texts to GitHub.

New optional \`build_private_qa_bundle(..., existing_owner_license_packet=..., expected_owner_review_sha256=...)\` path:
- **requires both** exact owner packet path and independent owner review digest; calls the existing C2 verified read-only original-five audit before creating the bundle;
- copies the five exact original bytes, source-relative names and SHA256/size into \`UCIE_PRIVATE_BUNDLE/ORIGINAL_LICENSES_REVIEW_ONLY\` (one-time, exclusive files, no overwrite);
- writes a strict canonical manifest plus an explicit \`NOTICE_REVIEW_REQUIRED.txt\`; all legal, OpenSSL native attribution, security, first-party/SkillBook and customer distribution flags remain FALSE;
- validates the new directory and SHA on technical bundle **verification**, including installation copies; rejects unrecognized files, forged approval, altered manifests and bytes;
- preserves existing 4-wheel technical QA behavior with the option omitted. No unauthorized extraction/download or changes to the original five-file owner packet.

**Important:** the B3/B4 bundle is still a technical QA artifact with \`customer_distribution_authorized=false\`. OpenSSL 4.0.3 native component LICENSE/conditional upstream NOTICE and any extra notices are NOT independently assembled by this step; SPDX \`licenseDeclared=NOASSERTION\` remains truthful. The new nested manifest hash provides file integrity **only**, NOT independent original-owner authentication or real owner-product binding; final signed manifest/real human approval is a later separately authorized release path. Do not ship this QA bundle to customers.

Tests: new synthetic 13-case source SHA/bytes, replay, tamper, forged OpenSSL/approval, missing or additional file, wrong directory, no-network and integration contract; plus existing full Windows/Ubuntu standard and installed signed release-candidate regression. Owner D:/UCIE source changes require absolute SHA lease; existing dirty source must not be overwritten and all unrelated runtime data, tasks, C40, Cloudflare, payment and private keys remain untouched.

**Manual owner handoff (no coding):** open \`D:\UCIE\downloaded\ucie_c2_owner_only_license_review_v01\README_KO.md\` and the five \`license-text\` originals; identify unusual clauses and whether first-party UCIE/SkillBooks are actually owned/authorized, without uploading the original copyright text. Developer handles actual vendor LICENSE inclusion and conditional OpenSSL NOTICE obligations. OpenSSL CVE disposition and real customer/payment contract are independent human actions.
