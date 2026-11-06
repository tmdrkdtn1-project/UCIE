"""UCIE SkillBook Phase 01: source-bound editorial draft compiler.

Reuses W01 Source Registry, W02 LibraryEntry, the SkillBook Blueprint and first-party claims.
This is offline, inert, unapproved review material: not verification of
supplied source digest, technical truth, executable skill or release.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape as html_escape
import json
import re
import unicodedata

from .library_entry import ALLOWED_INPUT_FIELDS, build_library_entry, LibraryEntryError
from .skillbook_blueprint import compose_blueprint, SkillBookBlueprintError

SCHEMA = "UCIE_SKILLBOOK_EDITORIAL_PRODUCTION_DRAFT_V01"
TOKEN = re.compile(r"[A-Z][A-Z0-9_]{2,63}\Z")
VERSION = re.compile(r"(?:0|[1-9]\d{0,2})\.(?:0|[1-9]\d{0,2})\.(?:0|[1-9]\d{0,2})-draft\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
ORDER = (
    "MECHANISM", "SAFE_PRECONDITIONS", "BOUNDED_APPLICATION",
    "COUNTEREXAMPLES", "VERSION_AND_QA_LIMITATIONS",
)
HEADINGS = dict(zip(ORDER, (
    "작동 원리와 공식 근거", "안전한 입력과 사전조건",
    "제한된 실행 설계 및 정보 노출", "반례·실패 처리",
    "버전·적용 한계·검증 필요사항",
)))
INPUT_KEYS = frozenset({
    "topic", "draft_version", "sources", "chapters",
    "machine_contract", "previous_revision", "revision_note",
})
CHAPTER_KEYS = frozenset({"chapter_id", "body", "source_ids"})
MACHINE_KEYS = frozenset({
    "interface_name", "input_contract", "output_contract",
    "failure_contract", "limits",
})
REVIEW_GATES = (
    "VERIFY_EXACT_PUBLIC_REVISION_AND_SOURCE_SHA",
    "VERIFY_ORIGINAL_CLAIM_AND_ATTRIBUTION",
    "VERIFY_VERSION_AND_NEGATIVE_TESTS",
    "VERIFY_SECURITY_AND_PRIVACY_SCOPE",
    "VERIFY_LICENSE_AND_REDISTRIBUTION_RIGHTS",
    "VERIFY_INDEPENDENT_QA",
    "VERIFY_OWNER_RELEASE_AUTHORIZATION",
)


class EditorialDraftError(ValueError):
    """Fail closed when authoring, provenance or revision claims are unsafe."""


def _text(value: object, *, limit: int = 1400, minimum: int = 15) -> str:
    if (type(value) is not str or not minimum <= len(value) <= limit
            or value != value.strip()
            or any(unicodedata.category(ch).startswith("C") for ch in value)):
        raise EditorialDraftError("bounded plain editorial data required")
    return value


def _normal_input(raw: object) -> tuple[dict, list[dict], dict]:
    if type(raw) is not dict or set(raw) != INPUT_KEYS:
        raise EditorialDraftError("fixed source-linked editorial contract required")
    topic, version, previous = raw["topic"], raw["draft_version"], raw["previous_revision"]
    if type(topic) is not str or TOKEN.fullmatch(topic) is None:
        raise EditorialDraftError("invalid topic")
    if type(version) is not str or VERSION.fullmatch(version) is None:
        raise EditorialDraftError("draft-only semantic version required")
    if previous is not None and (type(previous) is not str or HEX64.fullmatch(previous) is None):
        raise EditorialDraftError("invalid revision parent fingerprint")
    note = _text(raw["revision_note"], limit=320, minimum=12)
    candidates = raw["sources"]
    if type(candidates) is not list or not 1 <= len(candidates) <= 4:
        raise EditorialDraftError("bounded 1-4 sources required")
    entries, sources, seen = [], [], set()
    for candidate in candidates:
        if (type(candidate) is not dict or set(candidate) != ALLOWED_INPUT_FIELDS
                or candidate.get("kind") != "REUSABLE_SKILL"):
            raise EditorialDraftError("unexpected evidence fields or category")
        try:
            entry = build_library_entry(candidate)
        except (LibraryEntryError, ValueError, TypeError, KeyError) as exc:
            raise EditorialDraftError("invalid/unauthorized public source") from exc
        sid = entry["source_id"]
        if (sid in seen or entry["approval_status"] != "NOT_APPROVED"
                or entry["entry_status"] != "UNVERIFIED_CANDIDATE_ONLY"
                or entry["export_allowed"] is not False
                or entry["version_applicability_verified"] is not False):
            raise EditorialDraftError("duplicate or implicitly promoted source")
        seen.add(sid)
        entries.append(entry)
        sources.append({
            "kind": entry["kind"], "source_id": sid,
            "evidence_reference": entry["evidence_reference"],
            "evidence_sha256": entry["evidence_sha256"],
            "purpose_code": entry["purpose_code"],
            "version_scope": entry["version_scope_claim"],
            "dependencies": list(entry["dependencies"]),
        })
    entries.sort(key=lambda x: x["source_id"])
    sources.sort(key=lambda x: x["source_id"])
    try:
        blueprint = compose_blueprint(topic, sources)
    except (SkillBookBlueprintError, ValueError, KeyError, TypeError) as exc:
        raise EditorialDraftError("upstream public blueprint mismatch") from exc
    if (blueprint["chapter_count"] != len(entries)
            or {s["library_item_id"] for s in blueprint["chapters"]}
               != {e["library_item_id"] for e in entries}
            or blueprint["status"] != "UNVERIFIED_METADATA_ONLY"
            or blueprint["export_allowed"] is not False):
        raise EditorialDraftError("noncanonical blueprint")
    chapters = raw["chapters"]
    if type(chapters) is not list or len(chapters) != len(ORDER):
        raise EditorialDraftError("five original editorial chapters mandatory")
    normalized = []
    for ch in chapters:
        if type(ch) is not dict or set(ch) != CHAPTER_KEYS:
            raise EditorialDraftError("unknown chapter field")
        cid = ch["chapter_id"]
        if (type(cid) is not str or cid not in ORDER
                or any(x["chapter_id"] == cid for x in normalized)):
            raise EditorialDraftError("duplicated/unknown chapter ID")
        body = _text(ch["body"])
        refs = ch["source_ids"]
        if (type(refs) is not list or not 1 <= len(refs) <= len(seen)
                or any(type(s) is not str or s not in seen for s in refs)
                or len(set(refs)) != len(refs)):
            raise EditorialDraftError("unregistered or repeated chapter attribution")
        normalized.append({"chapter_id": cid, "body": body, "source_ids": sorted(refs)})
    normalized.sort(key=lambda x: ORDER.index(x["chapter_id"]))
    if (tuple(x["chapter_id"] for x in normalized) != ORDER
            or seen != {sid for c in normalized for sid in c["source_ids"]}):
        raise EditorialDraftError("missing chapter or unused source")
    machine = raw["machine_contract"]
    if type(machine) is not dict or set(machine) != MACHINE_KEYS:
        raise EditorialDraftError("unknown contract or claimed approval field")
    interface = machine["interface_name"]
    if type(interface) is not str or TOKEN.fullmatch(interface) is None:
        raise EditorialDraftError("invalid non-executable interface ID")
    clean_machine = {"interface_name": interface}
    for key in ("input_contract", "output_contract", "failure_contract", "limits"):
        clean_machine[key] = _text(machine[key], limit=600)
    material = {
        "topic": topic, "draft_version": version,
        "sources": sources, "chapters": normalized,
        "machine_contract": clean_machine,
        "previous_revision": previous, "revision_note": note,
    }
    if len(json.dumps(material, ensure_ascii=True).encode("ascii")) > 17000:
        raise EditorialDraftError("source manuscript byte budget exceeded")
    return material, entries, blueprint


def compile_review_draft(record: dict) -> dict:
    """Produce inspectable human/machine content *pending* manual review."""
    material, entries, blueprint = _normal_input(record)
    hash_material = {"blueprint_id": blueprint["blueprint_id"], "editorial": material}
    digest = sha256(json.dumps(
        hash_material, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")).hexdigest()
    if material["previous_revision"] == digest:
        raise EditorialDraftError("self-referential revision")
    items = [{
        "library_item_id": e["library_item_id"],
        "source_id": e["source_id"],
        "public_url": e["public_url"],
        "evidence_sha256": e["evidence_sha256"],
        "revision_hint": e["revision_hint"],
        "version_scope_claim": e["version_scope_claim"],
        "source_license_status": e["source_license_status"],
        "approval_status": "NOT_APPROVED",
        "source_content_hash_independently_checked": False,
        "rights_cleared": False,
    } for e in entries]
    result = {
        "schema": SCHEMA,
        "status": "EDITORIAL_CANDIDATE_REVIEW_PENDING_NO_GO",
        "topic": material["topic"], "draft_version": material["draft_version"],
        "draft_sha256": digest, "blueprint_id": blueprint["blueprint_id"],
        "authoring_input": material, "sources": items,
        "chapters": [{
            "chapter_id": c["chapter_id"], "heading": HEADINGS[c["chapter_id"]],
            "text": c["body"], "source_ids": c["source_ids"],
            "claim_type": "EDITOR_SUBMITTED_UNVERIFIED_ORIGINAL_TEXT",
            "technical_fact_review": "PENDING",
        } for c in material["chapters"]],
        "machine_contract": {
            **material["machine_contract"],
            "contract_kind": "DESIGN_ONLY_NO_EXECUTABLE",
            "callable_implemented": False,
            "independent_test_verified": False,
        },
        "revision": {
            "current_draft_sha256": digest,
            "previous_draft_sha256_claim": material["previous_revision"],
            "previous_revision_persistently_verified": False,
            "change_note": material["revision_note"], "published": False,
        },
        "manual_review_checklist": [
            {"gate": gate, "status": "PENDING"} for gate in REVIEW_GATES
        ],
        "public_source_route_registered": True,
        "source_digest_independently_verified": False,
        "technical_claim_verified": False,
        "human_approved": False,
        "independent_qa_verified": False,
        "security_review_approved": False,
        "license_redistribution_approved": False,
        "signed": False, "export_allowed": False, "released": False,
        "auto_promoted": False, "model_trained": False,
        "network_requests": 0, "operating_database_writes": 0,
        "other_project_access": False,
    }
    if len(json.dumps(result, ensure_ascii=True).encode("ascii")) > 25000:
        raise EditorialDraftError("assembled review draft byte budget exceeded")
    return result


# The user-authored prose may contain HTML or Markdown directives. It remains
# *untrusted literal text* in a review document, never an instruction to UCIE.
_MD_SPECIAL = frozenset("\\*_{}[]()#+-.!|>~") | {chr(96)}


def _md_literal(value: str) -> str:
    safe = html_escape(value, quote=True)
    return "".join("\\" + ch if ch in _MD_SPECIAL else ch for ch in safe)


def render_review_markdown(draft: dict) -> str:
    """Revalidate exact source/approval state before inert Markdown rendering."""
    if (type(draft) is not dict or type(draft.get("authoring_input")) is not dict
            or compile_review_draft(draft["authoring_input"]) != draft):
        raise EditorialDraftError("modified or forged review draft")
    lines = [
        "# UCIE SkillBook 검토 후보 — " + draft["topic"], "",
        "> 편집자 제출 기술 내용 / 근거 사실·사용권·안전성 미검증",
        "> 실행 가능한 기술이나 서명·배포·사람 승인 상태가 아닙니다.", "",
        "**초안 버전:** " + draft["draft_version"],
        "**초안 SHA-256:** " + draft["draft_sha256"], "",
        "## 출처와 수동 검증 필요사항", "",
    ]
    for src in draft["sources"]:
        lines.extend([
            "- " + _md_literal(src["source_id"]) + ": " + _md_literal(src["public_url"]),
            "  - 제출된 해시: " + src["evidence_sha256"],
            "  - 버전 주장: " + _md_literal(src["version_scope_claim"]),
            "  - 문서 원문 검증/라이선스 승인: 미완료",
        ])
    for chapter in draft["chapters"]:
        lines.extend([
            "", "## " + chapter["heading"], "",
            "**저작/검증:** 편집자 제출 / 사실 독립 검증 전",
            "**관련 출처:** " + ", ".join(_md_literal(s) for s in chapter["source_ids"]),
            "", "> " + _md_literal(chapter["text"]),
        ])
    lines.extend(["", "## 기계 계약 초안 (실행 불가)", "",
                  "**식별자:** " + draft["machine_contract"]["interface_name"]])
    for field, label in (("input_contract", "입력"), ("output_contract", "출력"),
                         ("failure_contract", "실패"), ("limits", "제한")):
        lines.append("**" + label + ":** " + _md_literal(draft["machine_contract"][field]))
    lines.extend(["", "## 수동 인수 게이트", ""])
    lines.extend("- " + item["gate"] + ": PENDING"
                 for item in draft["manual_review_checklist"])
    lines.extend(["", "**출시: NO_GO / 반출·서명·자동 승격 금지**", ""])
    text = "\n".join(lines)
    if len(text.encode("utf-8")) > 25000:
        raise EditorialDraftError("human review document byte budget exceeded")
    return text


def compare_review_revisions(previous: dict, candidate: dict) -> dict:
    """Compare two locally supplied draft snapshots, not trusted lineage."""
    for doc in (previous, candidate):
        if (type(doc) is not dict or type(doc.get("authoring_input")) is not dict
                or compile_review_draft(doc["authoring_input"]) != doc):
            raise EditorialDraftError("exact source-bound drafts required")
    if (previous["topic"] != candidate["topic"]
            or previous["draft_sha256"] == candidate["draft_sha256"]
            or candidate["revision"]["previous_draft_sha256_claim"]
               != previous["draft_sha256"]):
        raise EditorialDraftError("unlinked/identical revision")
    old = {c["chapter_id"]: c for c in previous["chapters"]}
    new = {c["chapter_id"]: c for c in candidate["chapters"]}
    old_sources = {x["library_item_id"] for x in previous["sources"]}
    new_sources = {x["library_item_id"] for x in candidate["sources"]}
    return {
        "schema": SCHEMA, "status": "LOCAL_DIFF_REQUIRES_FRESH_MANUAL_REVIEW",
        "topic": previous["topic"], "previous_draft_sha256": previous["draft_sha256"],
        "candidate_draft_sha256": candidate["draft_sha256"],
        "changed_chapter_ids": [k for k in ORDER if old[k] != new[k]],
        "added_public_evidence_ids": sorted(new_sources - old_sources),
        "removed_public_evidence_ids": sorted(old_sources - new_sources),
        "machine_contract_changed": previous["machine_contract"] != candidate["machine_contract"],
        "version_changed": previous["draft_version"] != candidate["draft_version"],
        "source_content_rechecked": False,
        "persistent_lineage_attested": False,
        "independent_review_completed": False,
        "approval_or_export_allowed": False,
        "operating_database_writes": 0,
    }



def build_review_handoff(record: dict) -> dict:
    """Build two reproducible *in-memory* review assets with a SHA receipt.

    No disk output, authorization, signed package, runtime skill or publish.
    Output bytes are for UCIE-internal human review; their existence is not
    proof that human fact-checking, source revision or rights review happened.
    """
    draft = compile_review_draft(record)
    human = render_review_markdown(draft).encode("utf-8")
    machine = (json.dumps(
        draft, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ) + "\n").encode("ascii")
    if not 0 < len(human) <= 25000 or not 0 < len(machine) <= 25000:
        raise EditorialDraftError("review handoff output exceeds bounded budget")
    return {
        "human_markdown": human,
        "machine_json": machine,
        "receipt": {
            "schema": SCHEMA,
            "status": "IN_MEMORY_REVIEW_HANDOFF_PENDING_NO_GO",
            "draft_sha256": draft["draft_sha256"],
            "human_markdown_sha256": sha256(human).hexdigest(),
            "machine_json_sha256": sha256(machine).hexdigest(),
            "source_count": len(draft["sources"]),
            "chapter_count": len(draft["chapters"]),
            "human_review_completed": False,
            "source_content_verified": False,
            "independent_qa_verified": False,
            "human_approved": False,
            "rights_approved": False,
            "signed": False, "export_allowed": False,
            "files_written": 0, "network_requests": 0,
            "operating_database_writes": 0, "other_project_access": False,
        },
    }

def compose_curated_two_book_pilot() -> dict:
    """Real UCIE authored chapters through the generic manual-review contract."""
    from .skillbook_product_v01 import build_skillbook as python_book
    from .skillbook_git_porcelain_product_v01 import build_skillbook as git_book
    from .skillbook_principle_composer_v01 import compose_bounded_metadata_principle
    sources = []
    for book in (python_book(), git_book()):
        entry = book["library_entry"]
        sources.append({
            "kind": entry["kind"], "source_id": entry["source_id"],
            "evidence_reference": entry["evidence_reference"],
            "evidence_sha256": entry["evidence_sha256"],
            "purpose_code": entry["purpose_code"],
            "version_scope": entry["version_scope_claim"],
            "dependencies": list(entry["dependencies"]),
        })
    principle = compose_bounded_metadata_principle()
    return compile_review_draft({
        "topic": "BOUNDED_METADATA_COMPARISON_REVIEW",
        "draft_version": "0.1.0-draft", "sources": sources,
        "chapters": [{
            "chapter_id": key, "body": chapter["text"],
            "source_ids": sorted(s["source_id"] for s in sources),
        } for key, chapter in zip(ORDER, principle["chapters"])],
        "machine_contract": {
            "interface_name": "BOUNDED_METADATA_REVIEW_CONTRACT",
            "input_contract": "An explicitly authorized directory or caller-supplied Git status bytes are distinct inputs.",
            "output_contract": "Python returns bounded sorted filenames; the Git parser returns counts only without names.",
            "failure_contract": "Reject unknown source, unsupported state, insufficient budget and incomplete Git delimiter.",
            "limits": "First-party synthetic comparison only, not an independently proven filesystem or Git security boundary.",
        },
        "previous_revision": None,
        "revision_note": "First unapproved editorial intake of two existing UCIE authored SkillBooks.",
    })
