"""Read-only Stage 4 Knowledge + curated review -> Stage 5-7 preview bridge.

No network, no code execution, no SQL INSERT, no scheduler interaction.
The active public miner is never modified. Callers must separately and
manually authorize Stage 4 Knowledge import; this bridge never imports.
"""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import re
import sqlite3

from .knowledge import SOURCES as KNOWLEDGE_SOURCES
from .patterns import MAX_ROWS, PatternError, group_patterns
from .review import _read_candidates, load_manifest
from .rule_candidates import approval_gate, candidate_rulepack

HASH = re.compile(r"[a-f0-9]{64}")


def preview_knowledge_rules(root: Path) -> dict:
    """Join metadata only, fail closed on stale/unsafe/partial knowledge."""
    root = Path(root)
    runtime = root / "runtime"
    knowledge = runtime / "knowledge.sqlite3"
    if (root.is_symlink() or runtime.is_symlink()
            or knowledge.is_symlink() or not knowledge.is_file()):
        raise PatternError("safe existing Knowledge DB required")
    manifest = load_manifest(root)
    mappings = {(e["source"], e["pr_number"]): e
                for e in manifest["entries"]}
    miner_rows = _read_candidates(root)  # strictly read-only
    if len(miner_rows) > MAX_ROWS:
        raise PatternError("candidate limit exceeded")
    source_by_key = {(r["source"], r["pr_number"]): r for r in miner_rows}
    with closing(sqlite3.connect(knowledge.resolve(strict=True).as_uri()
                                 + "?mode=ro", uri=True)) as con:
        con.execute("PRAGMA query_only=ON")
        if con.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise PatternError("Knowledge DB integrity failed")
        rows = con.execute("""SELECT source,pr_number,url,merge_timestamp,
                evidence_sha256,provenance_status,license_status,security_status,
                disposition FROM evidence""").fetchmany(MAX_ROWS + 1)
    if len(rows) > MAX_ROWS:
        raise PatternError("Knowledge ledger too large")
    knowledge_by_key = {}
    for source, number, url, merged, digest, provenance, license_state, security, disposition in rows:
        key = (source, number)
        if (source not in KNOWLEDGE_SOURCES
                or type(number) is not int or number < 1
                or key in knowledge_by_key
                or not isinstance(digest, str) or not HASH.fullmatch(digest)
                or provenance != "UNVERIFIED" or license_state != "UNVERIFIED"
                or security != "UNVERIFIED"
                or disposition not in ("CANDIDATE", "QUARANTINED", "RETRACTED")):
            raise PatternError("unsafe knowledge evidence")
        old = source_by_key.get(key)
        if (old is None or url != old["public_url"]
                or merged != old["merged_at"]
                or digest != old["evidence_sha256"]):
            raise PatternError("Knowledge does not match current miner")
        knowledge_by_key[key] = disposition
    if set(knowledge_by_key) != set(source_by_key):
        raise PatternError("Knowledge import incomplete or out of date")
    candidate_rows = []
    unmapped = 0
    excluded = 0
    for old in miner_rows:
        key = (old["source"], old["pr_number"])
        if knowledge_by_key[key] != "CANDIDATE":
            excluded += 1
            continue
        entry = mappings.get(key)
        if entry is None:
            unmapped += 1
            continue
        if entry["merged_at"] != old["merged_at"]:
            raise PatternError("curated evidence timestamp mismatch")
        candidate_rows.append({
            "source": old["source"], "pr_number": old["pr_number"],
            "canonical_pr_number": entry["canonical_pr_number"],
            "pattern_code": entry["pattern_id"],
            "evidence_sha256": old["evidence_sha256"],
            "status": "UNVERIFIED_CANDIDATE_ONLY",
        })
    grouped = group_patterns(candidate_rows)
    pack = candidate_rulepack(grouped)
    gate = approval_gate(pack)
    return {
        "schema": "UCIE_STAGE4_7_INTEGRATION_PREVIEW_V1",
        "miner_count": len(miner_rows),
        "knowledge_count": len(rows),
        "unmapped_count": unmapped,
        "quarantined_or_retracted_count": excluded,
        "pattern_preview": grouped,
        "rulepack_preview": pack,
        "approval_gate": gate,
        "database_writes": 0,
        "production_approved": False,
    }
