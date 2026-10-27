# UCIE seventh candidate: low-level MCP x-mcp-header schema, 2026-10-27

Project: UCIE only. Workroom: UCIE_MAIN_DEV_V2. Status: CANDIDATE_ONLY / CI_PENDING / NO_OWNER_SIGNING.

## New, distinct upstream evidence
- Approved independent public repository: https://github.com/modelcontextprotocol/python-sdk/pull/3620 (merged 2026-10-02, upstream merge 3d0c40d8aafb37304635d75dbcafc2379b38b975).
- Repository license at pinned commit: MIT (LICENSE blob 3d48435454b105021b4f777c11b6b07d8d2ffea3).
- Pinned documented example: docs/advanced/header-parameters.md blob a47be2f87453ff9aa628445c0b755e436b5f78ff.
- Pinned upstream validator: src/mcp/shared/inbound.py blob e33d6f502f6ac25c61d0f183ed9bec044acd049c.
- The SDK says high-level MCPServer Tool.from_function now rejects invalid x-mcp-header annotations; low-level manually created Tool(input_schema=...) and low-level Server listings bypass that registration validation. Protocol-2026-07-28 clients may omit invalid tools from tools/list.

## Inert candidate-only implementation
- src/ucie_miner/static_mcp_header.py: parse bounded caller-supplied Python AST only, require a literal Tool(input_schema=...) dictionary, inspect x-mcp-header on schema positions.
- Detect invalid header type, RFC 9110 token syntax, invalid primitive type, duplicate case-insensitive header names, and schema positions off a pure properties chain.
- Dynamic schema expressions are review-required, never a safety PASS. No-match output is never a safety PASS.
- Upper bounds: 128 KiB source, 20k AST nodes, 1024 schema positions, depth 32, 20 findings.
- Scope limitation: literal Tool input_schema only. Does not resolve aliases, variables, imported source, Pydantic-generated fields, custom constructors or actual runtime registration. Static reports are unverified candidate findings.
- tests/test_ucie_seventh_mcp_header.py: synthetic regression cases, including valid, invalid and dynamic schemas, inert source handling and stdin CLI. No external SDK import, server, network or filesystem scanning by the detector.

## Operational gates
- Owner-signed existing Serial4 parent and separately signed Serial5 are IMMUTABLE and must not be re-signed for this candidate.
- Existing sixth MCP empty-_meta candidate is merged but unsigned. This seventh category is separate and also unsigned.
- Required before merge: exact PR head GitHub Actions Windows/Ubuntu x Python3.13/3.15 matrix PASS, only focused repairs if failure.
- Owner signing, independent QA, license signoff, actual 2026-07-28 peer observation, fixed release-version coverage and external distribution are NOT completed.
- No automatic promotion, source execution, release change, scheduler mutation, production DB mutation, external API calls by detector or access to unrelated projects.
