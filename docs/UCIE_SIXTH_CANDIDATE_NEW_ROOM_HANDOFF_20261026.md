# UCIE sixth candidate and new-room handoff — 2026-10-26 KST

WORKROOM_ID: UCIE_MAIN_DEV_V2
PROJECT: UCIE only
REPOSITORY: https://github.com/tmdrkdtn1-project/UCIE
OWNER_LOCAL_ROOT: D:\UCIE
PYTHON_RUNTIME: 3.15.0
GOVERNANCE: public technical evidence only; other projects, private files, conversation/app sources and unapproved repositories strictly out of scope.

## A. Completed fifth-rule owner release (do NOT repeat)

The owner submitted the actual signed and verified receipt:

- status: UCIE_FIFTH_SERIAL5_OWNER_SIGNED_VERIFIED
- serial: 5
- owner_signature: VALID
- rule_id: PY_ASYNCIO_PROTOCOL_FACTORY_PRETRANSPORT_LEAK
- parent_serial: 4
- parent_sha256: 9DBFDF56987C3940F0F5E1C45A2E82AC8D7DA2EBE395D688EBC8CB1956CBE34F
- source_commit_sha: 853d12fdab5734586450069fafa40cb6211c562c
- pack_sha256: CC9F46CD7FD7AFC01B47AD0DF98604650C65C5F7EAE47A937DCF59563F455F56
- signing_performed_this_run: true
- auto_fix: false
- auto_apply: false
- external_deployment: false
- independent_human_qa_approved: false

Owner-signed new artifact (reported by owner host):
D:\UCIE\runtime\owner_release_main_81d935b1\build\UCIE_Fifth_Rule_Addendum_Serial_5.zip

The immutable original Serial4 contains FOUR rules. Serial5 is a SEPARATELY SIGNED one-rule addendum bound to the Serial4 parent. The fifth release is completed, not a reason to re-sign, repeat its QA, or reread the same evidence. No external deployment was made. Signed artifacts have expiration; the receipt does not authorize silent re-signing.

## B. Sixth rule candidate — real new category

New sixth-rule candidate identifier:
MCP_JSONRPC_UNCONDITIONAL_EMPTY_META

Official independent public upstream:
https://github.com/modelcontextprotocol/python-sdk/pull/3628

- Upstream title: "Omit an empty _meta and empty params from outbound requests"
- Merged: 2026-10-02 13:32:29 UTC
- Before source: modelcontextprotocol/python-sdk commit
  19e4f2a6c4a35e8aaad0ca07d3d9f37703865e2e;
  src/mcp/shared/jsonrpc_dispatcher.py blob
  5c09126a17d9a45e02b5662964a04b5cd63b1ba8
- Merged after source: commit
  0b2fd3ea60efb16b349e8c887cf91bf2f9f773fc;
  same file blob
  ab333912d2857c12eb42dd5adfa59df4dceefa24

Underlying compatibility problem: a v2 client using an earlier initialize handshake would send an unconditional empty "_meta": {} in every request; for ping and list methods the entire params envelope could consist of only empty metadata. The approved upstream PR states some v1/legacy peers rejected this otherwise-spec-valid empty metadata and became unreachable. The official fix:
- include out_params["_meta"] only when out_meta is nonempty;
- omit params entirely when out_params is empty;
- preserve caller metadata, tracing and progress.

This rule is DIFFERENT from the previous five rules: MCP client/JSON-RPC compatibility, not Python resource cleanup, PowerShell command discovery, or scandir threading.

## C. Work performed in this room

New source:
src/ucie_miner/static_mcp_empty_meta.py

New tests:
tests/test_ucie_sixth_mcp_empty_meta.py

Rule only detects a narrowly sourced AST pattern in a method called send_raw_request:
- unconditional out_params["_meta"] = out_meta
- JSONRPCRequest(..., params=out_params) in that function scope
- no positive if out_meta: guard around the assignment.

The scanner only parses explicitly passed Python text as AST, maximum 128 KiB, 20,000 AST nodes and 20 findings. It never executes imported/upstream/user code, opens files, contacts a service, fixes source, signs a Rulepack or auto-promotes. The output MUST be described as STATIC_CANDIDATE_REVIEW_REQUIRED, never a confirmed runtime failure in an arbitrary input. No independent deployed SDK-v1 compatibility run or release-version mapping has been established.

Tests cover upstream-shaped pre/post, incorrect guard, unrelated methods and sinks, nested scope, invalid/oversized input, inert stdin CLI, and synthetic before/after wire payload. They do not substitute for a real v1 server interoperability test.

## D. Next owner and minimal stages

1. Finish this ONE branch's focused CI; repair only a real failure, avoiding repeated PRs or re-checking Serial4/Serial5.
2. Merge this candidate code only after exact-head CI passes. Record PR, final SHA, and test result in this handoff.
3. New room should start with official PR #3628 and the merged UCIE sixth candidate, then either add one targeted real-runtime legacy peer observation or select another evidence-backed distinct rule. Do NOT claim Sixth is signed.
4. Owner risk approval/signing of Rule6 is an entirely separate explicit decision; the prior fifth-rule owner consent does NOT include Rule6.
5. Do not touch the existing owner signer, signed ZIPs, release scheduler, or other projects. Stay within approved public sources python/cpython, PowerShell/PowerShell, git/git, modelcontextprotocol/python-sdk and actions/runner-images, plus official documents.

## E. Priority/efficiency

Speed priority: one functional improvement per bundle; no repeated validation of already completed rules, no PR proliferation merely to rename statuses, no automatic promotion or artificial PASS. Only necessary focused tests + one normal CI run.
