# UCIE SkillBook V0.1 — First technical chapter (2026-11-05)

UCIE-only, first-party original draft; neither an independent upstream verification nor a production package.

Approved public context: python/cpython PR #160930, merged 2026-10-30T06:46:19Z, merge commit af79f49308f8f87896d1c09419db3f5ff67185af.
Topic: avoiding resource-count snapshot races when background cleanup is still pending.

New source: src/ucie_miner/skillbook_first_chapter_v01.py
New tests: tests/test_ucie_skillbook_first_chapter_v01.py

Outputs: original readable chapter, structured machine contract, W01/W02-linked library entry, immutable PR identity metadata, UCIE-authored positive/negative synthetic cases, draft revision history.
Search: search_first_skillbook(query,kind,source_id) is a nonpersistent W04-compatible metadata lookup. Existing V0.9 browser remains unchanged. No new global UI, no DB or task changes.
Important: the record SHA256 is of UCIE-created public PR metadata, NOT upstream content. Actual version support, rights, security and independent effectiveness remain NOT VERIFIED.

Test on owner UCIE: python -B -m unittest discover -s tests -p test_ucie_skillbook_first_chapter_v01.py -v
Preview: python -B -m ucie_miner.skillbook_first_chapter_v01

Next: wire separate non-mutating V0.9 UI read-only route, actual isolated first-party runner/version matrix, rights review, approved portable draft and UCIE-native revision measurements.