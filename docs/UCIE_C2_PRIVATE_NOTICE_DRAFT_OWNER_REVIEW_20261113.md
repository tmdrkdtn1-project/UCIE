# UCIE C2 original-license NOTICE private draft — owner review only (2026-11-13)

PROJECT=UCIE ONLY. This is a developer and owner human-review tool, not a legal approval, commercial distribution mechanism, or a replacement for the existing C2 proof.

## Purpose and source-of-truth

Previously verified owner receipts must not be regenerated: 3 vendor wheel↔PyPI SHA matches; 5 existing owner LICENSE file bytes with 15,755 total bytes, review entries SHA256 `98f043ba6717c207a4efbb4f0142f80fbc99c525890119ba26604cdf4fe30c7e`. These are owner-reported original reads, not re-read by the ChatGPT bridge.

Existing main's `customer_private_offline_lifecycle_v01.py` continues producing `NOTICE_REVIEW_REQUIRED.txt` and SPDX `NOASSERTION`. That is explicitly not sufficient for customer redistribution. **This change does not modify that release path.**

The new `customer_c2_private_notice_draft_v01.py` first invokes the existing approved C2 original-file SHA read-only verifier against the same pre-existing `D:/UCIE/downloaded/ucie_c2_owner_only_license_review_v01` folder and independent expected review digest. If any of the five bytes, source inventory, paths, symlinks, legal-approval flags or hashes drift, it fails before copying.

On a deliberate, separately authorized owner Windows CPython 3.15 interactive run only, it exclusive-creates one previously absent **owner-private** `downloaded/ucie_c2_private_notice_draft_v01` directory; it copies the verified five original text bytes to fixed local names `LICENSE_ORIGINAL_01.txt` through `LICENSE_ORIGINAL_05.txt`, with their exact source relative paths, SHA256 and byte sizes in a manifest, and an explicit missing-rights HOLD notice. No wheel binaries, signing keys, customer code or newly fetched source content are included. It does not overwrite existing drafts and returns exit code **2 intentionally**, including on successful private draft creation, to preclude automation mistaking a review packet for a release.

This is **not** an approved composite appendix: notably embedded OpenSSL 4.0.3 LICENSE/NOTICE and any further transitive notices are NOT automatically attached. The owner/legal reviewer must inspect the private existing originals and determine actual clauses, copyright, necessary notices, choice of cryptography's dual-license option, first-party/SkillBook ownership and any third-party copied content. An authorized security reviewer must separately resolve the OpenSSL known conditional five LOW CVEs with actual security and patch/risk decision. A designated signed customer agreement, owner product-key approval and a separate physical Windows recipient are still needed. No synthetic test can approve these gates.

## Invocation (NOT executed by this PR)

Run only from the owner Windows interactive PowerShell session after consciously deciding to create the single private review copy. The operation is one-way, does not re-download or re-export, and requires explicit owner-only typed consent:

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_c2_private_notice_draft_v01 --owner-stage-private-review-only --expected-review-entries-sha256 98f043ba6717c207a4efbb4f0142f80fbc99c525890119ba26604cdf4fe30c7e
```

TTY consent is exactly `UCIE_C2_PRIVATE_NOTICE_DRAFT_ONLY`. A successful stage prints `FIVE_ORIGINAL_LICENSE_COPIES_PRIVATE_REVIEW_ONLY_NO_GO`; exit code 2 is *expected*, not a license failure or distribution GO. Do not run again if the private folder already exists. Never upload the original texts, keys, private customer materials or approval declarations to Slack/public GitHub.

## Scope and checks

- Unit tests use only UCIE-authored synthetic text (10 cases): exact original preservation, repeated-execution refusal, wrong external SHA, tampered originals/draft, forged approval, spoofed OpenSSL notice, unexpected extra file, non-owner CLI, and network denial.
- No local D:/UCIE write, bridge refresh, scheduler/C40/Cloudflare change, operating DB access, new vendor download or GitHub storage of real copyrighted original bytes occurs as part of this PR.
- No source or test pass is customer LICENSE/NOTICE approval. **C2 human/legal + independent security = HOLD; C3 real owner signer = NOT_EXECUTED; C4 real physical Windows = PENDING; C5 actual customer contract/pilot = PENDING; paid provider integration = NOT_CONNECTED; customer distribution = NO_GO.**

The owner must not blindly set review flags. Approvals only follow true inspection of the actual owner originals, appropriate decision authority and safe private archival.
