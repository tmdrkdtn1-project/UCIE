"""UCIE Stage 7/8: bind read-only evidence, pattern and regression receipts.

This is a structural cross-check of bounded public, candidate-only metadata,
not authentication, code execution, regression reproduction, or approval.
A SHA-256 receipt is a change detector, NEVER a digital signature.
"""
from __future__ import annotations

import hashlib
import json

from .license_review import LICENSE_DOCS
from .patterns import PatternError
from .provenance_review import _validate as _validate_rows
from .regression_plans import create_regression_matrix
from .review import ALLOWED
from .rule_candidates import approval_gate, candidate_rulepack

STATES = frozenset((
    "NOT_CHECKED", "SOURCE_MISMATCH", "SOURCE_UNAVAILABLE",
    "PUBLIC_API_METADATA_MATCHED", "SYNTHETIC_METADATA_MATCHED",
))
LICENSE_STATES = frozenset((
    "NOT_CHECKED", "MARKER_ABSENT", "UNAVAILABLE_OR_OVERSIZED",
    "PUBLIC_TAG_MARKER_PRESENT", "SYNTHETIC_TAG_MARKER_PRESENT",
))
MAX_ITEMS = 40


def _digest(obj):
    try:
        data = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False)
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise PatternError("unserializable public evidence receipt") from exc
    return hashlib.sha256(data.encode("ascii")).hexdigest()


def bind_candidate_receipts(source_rows, manifest, chain, provenance,
                            licenses, regression) -> dict:
    """Cross-check all input identities, fingerprints and candidate status."""
    try:
        rows = _validate_rows(source_rows)
        if (not isinstance(manifest, dict)
                or manifest.get("schema") != "UCIE_PR_REVIEW_EVIDENCE_V1"
                or not isinstance(manifest.get("entries"), list)
                or len(manifest["entries"]) > MAX_ITEMS
                or not isinstance(chain, dict)
                or chain.get("schema") != "UCIE_STAGE4_7_INTEGRATION_PREVIEW_V1"
                or type(chain.get("miner_count")) is not int
                or chain["miner_count"] != len(rows)
                or chain.get("knowledge_count") != len(rows)
                or chain.get("database_writes") != 0
                or chain.get("production_approved") is not False
                or not isinstance(provenance, dict)
                or provenance.get("schema") != "UCIE_PUBLIC_PR_PROVENANCE_INSPECTION_V1"
                or provenance.get("count") != len(rows)
                or provenance.get("persistent_writes") != 0
                or provenance.get("production_approved") is not False
                or not isinstance(provenance.get("items"), list)
                or not isinstance(licenses, dict)
                or licenses.get("schema") != "UCIE_PINNED_LICENSE_MARKER_AUDIT_V1"
                or licenses.get("license_approved") is not False
                or licenses.get("persistent_writes") != 0
                or licenses.get("production_approved") is not False
                or not isinstance(licenses.get("items"), list)):
            raise PatternError("invalid or incomplete candidate receipts")
        identity = {(r["source"], r["pr_number"]): r for r in rows}
        ref = {}
        for m in manifest["entries"]:
            if not isinstance(m, dict):
                raise PatternError("invalid pinned manifest")
            key = (m.get("source"), m.get("pr_number"))
            if not isinstance(key[0], str) or type(key[1]) is not int or key in ref:
                raise PatternError("duplicate/invalid pinned manifest identity")
            if (key[0] not in ALLOWED
                    or type(m.get("canonical_pr_number")) is not int
                    or not isinstance(m.get("pattern_id"), str)
                    or not isinstance(m.get("release_tag"), str)
                    or m["release_tag"] not in ALLOWED[key[0]]["tags"]
                    or m.get("license") != LICENSE_DOCS[key[0]][2]):
                raise PatternError("pinned source or tag mismatch")
            ref[key] = m
        observed = {}
        for p in provenance["items"]:
            if not isinstance(p, dict):
                raise PatternError("malformed provenance item")
            key = (p.get("source"), p.get("pr_number"))
            if (not isinstance(key[0], str) or type(key[1]) is not int
                    or key not in identity or key in observed
                    or p.get("merged_at") != identity[key]["merged_at"]
                    or p.get("miner_evidence_sha256") != identity[key]["evidence_sha256"]
                    or p.get("source_check") not in STATES
                    or p.get("metadata_check_only") is not True
                    or p.get("approved") is not False
                    or p.get("license_verified") is not False
                    or p.get("security_review_passed") is not False
                    or p.get("fix_independently_reproduced") is not False):
                raise PatternError("stale or inconsistent provenance")
            raw = {
                "source": key[0], "pr_number": key[1],
                "merged_at": p["merged_at"],
                "miner_evidence_sha256": p["miner_evidence_sha256"],
                "observed_merge_commit_sha": p.get("observed_merge_commit_sha"),
                "source_check": p["source_check"],
            }
            if p.get("comparison_sha256") != _digest(raw):
                raise PatternError("provenance comparison hash mismatch")
            observed[key] = p
        if set(observed) != set(identity):
            raise PatternError("incomplete provenance coverage")
        license_items = {}
        expected_licenses = {(m["source"], m["release_tag"])
                             for m in ref.values()}
        for item in licenses["items"]:
            if not isinstance(item, dict):
                raise PatternError("malformed license observation")
            key = (item.get("source"), item.get("release_tag"))
            if (not isinstance(key[0], str) or not isinstance(key[1], str)
                    or key not in expected_licenses or key in license_items):
                raise PatternError("unexpected license document")
            source, tag = key
            doc, _, SPDX = LICENSE_DOCS[source]
            if (item.get("document_url") !=
                    f"https://raw.githubusercontent.com/{source}/{tag}/{doc}"
                    or item.get("declared_license") != SPDX
                    or item.get("tag_is_not_merge_commit") is not True
                    or item.get("independent_commit_license_reviewed") is not False
                    or item.get("legal_approval") is not False
                    or item.get("marker_status") not in LICENSE_STATES):
                raise PatternError("invalid license marker/approval")
            digest = item.get("body_sha256")
            if (digest is not None and
                    (not isinstance(digest, str) or len(digest) != 64
                     or any(c not in "0123456789abcdef" for c in digest))):
                raise PatternError("invalid license content digest")
            if item["marker_status"] == "NOT_CHECKED" and digest is not None:
                raise PatternError("unchecked license cannot contain a digest")
            license_items[key] = item
        if (set(license_items) != expected_licenses
                or licenses.get("count") != len(expected_licenses)):
            raise PatternError("pinned license coverage mismatch")
        grouped = chain.get("pattern_preview")
        pack = chain.get("rulepack_preview")
        if (not isinstance(grouped, dict) or not isinstance(pack, dict)
                or pack != candidate_rulepack(grouped)
                or chain.get("approval_gate") != approval_gate(pack)
                or regression != create_regression_matrix(pack)):
            raise PatternError("candidate chain or regression digest mismatch")
        used = set()
        for family in grouped["families"]:
            source, canonical = family["source"], family["canonical_pr_number"]
            members = family["pr_numbers"]
            if (not isinstance(members, list) or not members
                    or members != sorted(set(members))
                    or (source, canonical) not in identity
                    or canonical not in members):
                raise PatternError("missing canonical pattern anchor")
            sha = []
            for n in members:
                key = (source, n)
                if (key not in identity or key not in ref or key in used
                        or ref[key]["pattern_id"] != family["pattern_code"]
                        or ref[key]["canonical_pr_number"] != canonical
                        or ref[key]["merged_at"] != identity[key]["merged_at"]):
                    raise PatternError("stale or conflicting family binding")
                used.add(key)
                sha.append(identity[key]["evidence_sha256"])
            expected = _digest([source, canonical,
                                [family["pattern_code"]], sorted(sha)])
            if family["fingerprint_sha256"] != expected:
                raise PatternError("pattern fingerprint mismatch")
        skipped = chain.get("unmapped_count")
        excluded = chain.get("quarantined_or_retracted_count")
        if (type(skipped) is not int or type(excluded) is not int
                or min(skipped, excluded) < 0
                or len(used) + skipped + excluded != len(rows)):
            raise PatternError("unexplained source evidence gap")
        links = [{
            "source": row["source"], "pr_number": row["pr_number"],
            "miner_evidence_sha256": row["evidence_sha256"],
            "metadata_check": observed[(row["source"], row["pr_number"])]["source_check"],
            "review_release_tag": ref.get((row["source"], row["pr_number"]), {})
                                      .get("release_tag"),
        } for row in rows]
        return {
            "schema": "UCIE_CANDIDATE_BINDING_V1",
            "status": "STRUCTURALLY_CONSISTENT_CANDIDATES",
            "receipt_sha256": _digest({
                "entries": links,
                "family_fingerprints": sorted(
                    x["fingerprint_sha256"] for x in grouped["families"]),
                "regression_cases": regression["candidate_count"],
                "license_markers": sorted(
                    (x["source"], x["release_tag"], x["marker_status"],
                     x["body_sha256"]) for x in license_items.values()),
            }),
            "source_count": len(rows),
            "mapped_pr_count": len(used),
            "family_count": len(grouped["families"]),
            "source_metadata_authenticated": False,
            "licenses_independently_verified": False,
            "regressions_reproduced": False,
            "receipt_cryptographically_signed": False,
            "deploy_allowed": False,
            "persistent_writes": 0,
            "production_approved": False,
        }
    except (TypeError, KeyError, IndexError, AttributeError) as exc:
        raise PatternError("malformed evidence-chain identity") from exc
