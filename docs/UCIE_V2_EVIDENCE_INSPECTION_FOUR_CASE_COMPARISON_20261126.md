# UCIE V2 offline Local B1/B2/B4 inspected proof and four-case comparison

Owner-first product development, stacked after prior verified PR #380 at exact HEAD f6f5ba8d13283c689d8e8b3afd0b301d650f7757 (4/4 exact CI #45790481544 SUCCESS, owner separately observed the previous HTML in Edge).

The previously visible preview only showed the case/capsule ID and count of original review assets. It now invokes the existing first-party B1/B2/B4 code to show *inspectable* proof: original pinned official MCP SDK PR and public spec links, exact fixed commit, historical real first-party CI receipt, distinct version/QA/rights limitations and two actual source-linked virtual-library proposed review packages with IDs/SHA/status/next-test kind. Review packages are clearly distinguished from the historical real SDK test. Other three known cases display their original issue/control synthetic observations, never invented MCP-specific provenance.

`python -m ucie_miner.ucie_v2_local_readonly_preview_v01 --case all` prints one standalone, Korean, single-column HTML page with 4 anchor-navigation case sections, proof disclosures and relative safe fallback summaries. Existing `--case mcp-prompts` remains valid. This is a pure offline preview, no user data entry, file operation, extra GET/POST endpoint, network fetch, dynamic browser script, arbitrary customer code, status promotion, Local V04 route/app or live operating DB modification.

Eight additional tests assert all four existing classifiers, evidence source identity/negative controls, no forged rights, no active remote resources, CLI compatibility and deterministic render. Actual user-first-use/Edge visual keyboard+responsive QA, source-independent validation, and signed/licensed customer distribution require separate evidence.

Release remains blocked; no merge, Windows V04 or owner local original checkout write. CI: one exact-head original Ubuntu/Windows Python3.13/3.15 checkpoint, no new workflow or runners.
