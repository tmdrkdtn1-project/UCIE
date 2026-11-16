"""UCIE W09: original signed manual consumer and portable draft acceptance.

Never signs, exports, deploys, re-arms P11, executes external PR source,
scans unrelated projects, changes operating DB, or grants new approvals.

An isolated UCIE-authored DRAFT ZIP QA is distinct from distribution;
an existing owner-risk signed manual rule is distinct from QA/licensing.
If selected, the real W09 manual consumer independently re-verifies the
original signed package/trust/expiry in a separate -I Python process.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from .portable_consumer_qa import (
    SCHEMA as PORTABLE_SCHEMA, check_portable_engine_qa,
)
from .product_v1 import (
    SCHEMA as PRODUCT_SCHEMA, integrated_product_preview,
    ProductIntegrationError,
)
from .signed_rule_library import SignedLibraryError
from .w07_w08_independent_readiness_v01 import (
    SCHEMA as REVIEW_SCHEMA, independent_review_board, ReadinessError,
    CLOSED as REVIEW_COMPLETE, PARTIAL as REVIEW_PARTIAL,
)

SCHEMA = "UCIE_W09_INDEPENDENT_CONSUMER_ACCEPTANCE_READONLY_V01"
NO_SIGNED = "W09_NO_EXISTING_SIGNED_RULE_SELECTION_RELEASE_NO_GO"
NO_SELECTION = "W09_SIGNED_OWNER_RULE_SELECTION_REQUIRED_NO_GO"
REVERIFIED = "W09_ORIGINAL_MANUAL_CONSUMER_REVERIFIED_RELEASE_NO_GO"
RELEASE_BLOCKERS = (
    "INDEPENDENT_HUMAN_RULE_QA_NOT_ATTESTED",
    "SOURCE_VERSION_AND_LEGAL_REDISTRIBUTION_RIGHTS_NOT_SIGNED_OFF",
    "SECURITY_AND_NEGATIVE_REGRESSION_ACCEPTANCE_NOT_ATTESTED",
    "OWNER_CUSTOMER_RELEASE_AUTHORIZATION_NOT_PROVIDED",
    "PRODUCTION_CONSUMER_HOST_ACCEPTANCE_NOT_COMPLETE",
)
HASH64 = re.compile(r"[a-f0-9]{64}\Z")
MANUAL_SCHEMA = "UCIE_V1_MANUAL_W09_CONSUMER_REVERIFICATION_V1"
MANUAL_STATUS = "ORIGINAL_SIGNED_RULE_REVERIFIED_MANUAL_REFERENCE_ONLY"
REFERENCE_SCHEMA = "UCIE_V1_SELECTED_EXISTING_W09_MANUAL_CONSUMER_REFERENCE_V1"
REFERENCE_STATUS = "EXISTING_SIGNED_MANUAL_REFERENCE_VERIFIED_NOT_RELEASED"

# ONLY pre-reviewed first-party code. Not a user controlled module or script.
_CHILD = (
    "import runpy,sys\n"
    "sys.path.insert(0,sys.argv[1])\n"
    "sys.argv=['manual_consumer_v1',*sys.argv[2:]]\n"
    "runpy.run_module('ucie_miner.manual_consumer_v1',run_name='__main__')\n"
)


class W09AcceptanceError(ValueError):
    pass


def _hash(value: dict) -> str:
    return sha256(json.dumps(
        value, ensure_ascii=True, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("ascii")).hexdigest()


def _root(root: Path) -> Path:
    if (not isinstance(root, Path) or root.is_symlink()
            or not root.is_dir() or root.name.casefold() != "ucie"
            or (root/"runtime").is_symlink()
            or not (root/"runtime").is_dir()):
        raise W09AcceptanceError("dedicated UCIE root and runtime required")
    root=root.resolve()
    # No automatic access to any other user's or company's codebase.
    # Offline synthetic roots must opt in via a literal UCIE test marker.
    win_owner = (os.name == "nt" and
                 root == Path("D:/UCIE").resolve() and
                 (root/".git").is_dir())
    marker = root/"runtime"/"UCIE_W09_CONSUMER_SYNTH_ONLY.marker"
    synthetic = (
        root.is_relative_to(Path(tempfile.gettempdir()).resolve())
        and marker.is_file() and not marker.is_symlink()
        and marker.read_text(encoding="ascii") ==
            "UCIE_W09_CONSUMER_SYNTHETIC_ONLY_V01"
    )
    if not (win_owner or synthetic):
        raise W09AcceptanceError("outside approved owner UCIE or test fixture")
    return root


def _portable(root: Path) -> dict:
    result=check_portable_engine_qa(root)
    if (type(result) is not dict
            or result.get("schema") != PORTABLE_SCHEMA
            or result.get("status") !=
                "FIRST_PARTY_ISOLATED_CONSUMER_QA_PASS_NOT_RELEASED"
            or result.get("portable_engine") !=
                "UCIE_PORTABLE_EXACT_PUBLIC_METADATA"
            or result.get("independent_python_process_executed") is not True
            or result.get("standalone_zip_without_ucie_install_executed") is not True
            or type(result.get("standalone_zip_exact_parity_cases")) is not int
            or result["standalone_zip_exact_parity_cases"] < 3
            or result.get("portable_source_exact_byte_match") is not True
            or result.get("exact_result_parity_verified") is not True
            or result.get("zero_match_control_verified") is not True
            or result.get("temporary_first_party_module_removed_after_qa") is not True
            or result.get("standalone_zip_external_qa_attested") is not False
            or result.get("independent_external_qa_attested") is not False
            or result.get("owner_release_approved") is not False
            or result.get("upstream_public_code_included_or_executed") is not False
            or result.get("user_or_other_project_source_scanned") is not False
            or result.get("full_public_universe_covered") is not False
            or result.get("network_requests") != 0
            or result.get("operating_database_writes") != 0
            or result.get("new_signatures_created") != 0
            or result.get("auto_promoted") is not False
            or result.get("package_released") is not False
            or result.get("v1_accepted") is not False):
        raise W09AcceptanceError("independent draft consumer trust scope drift")
    if (type(result.get("package_sha256")) is not str
            or HASH64.fullmatch(result["package_sha256"]) is None
            or type(result.get("first_party_source_sha256")) is not str
            or HASH64.fullmatch(result["first_party_source_sha256"]) is None
            or type(result.get("public_candidate_records_tested")) is not int
            or not 0 <= result["public_candidate_records_tested"] <= 20):
        raise W09AcceptanceError("draft SHA or bounded public cohort malformed")
    return {
        "status": result["status"],
        "draft_package_sha256":result["package_sha256"],
        "first_party_source_sha256":result["first_party_source_sha256"],
        "engine_version":result["engine_version"],
        "independent_python_process_executed":True,
        "standalone_zip_without_ucie_install_executed":True,
        "standalone_parity_cases":result["standalone_zip_exact_parity_cases"],
        "public_unverified_metadata_records_tested":
            result["public_candidate_records_tested"],
        "no_upstream_public_source_executed":True,
        "only_temporary_first_party_draft_tested":True,
        "portable_distribution_rights_approved":False,
        "package_released":False,
    }


def _producer(root: Path, *, serial4: Path, trust: Path,
              serial5: Path | None, selected: str) -> dict:
    # This is the ORIGINAL W09 product producer, not a fabricated reference.
    result=integrated_product_preview(
        root,limit=20,include_demo=False,
        signed_serial4=serial4,owner_public_trust=trust,
        signed_serial5=serial5,select_item_id=selected,
        include_consumer_reference=True)
    reuse=result.get("reuse_eligibility")
    signed=result.get("signed_rules")
    ref=result.get("selected_existing_w09_consumer_reference")
    if (result.get("schema") != PRODUCT_SCHEMA
            or result.get("status") != "P9_INTEGRATED_READ_ONLY_PRODUCT_PREVIEW_NO_GO"
            or result.get("network_requests") != 0
            or result.get("operating_database_writes") != 0
            or result.get("new_signatures_created") != 0
            or result.get("candidate_auto_promoted") is not False
            or result.get("package_released") is not False
            or result.get("v1_accepted") is not False
            or type(reuse) is not dict
            or type(reuse.get("selected_item")) is not dict
            or reuse["selected_item"].get("selection_status") !=
                "EXISTING_OWNER_SIGNED_MANUAL_REFERENCE_ONLY"
            or reuse["selected_item"].get("new_generic_package_export_allowed") is not False
            or type(signed) is not dict
            or signed.get("status") != "EXISTING_OWNER_SIGNED_VERIFIED_READ_ONLY"
            or signed.get("independent_qa_signed_off") is not False
            or type(ref) is not dict
            or ref.get("schema") != REFERENCE_SCHEMA
            or ref.get("status") != REFERENCE_STATUS
            or ref.get("selected_library_item_id") != selected
            or ref.get("original_pack_reverified_at_handoff") is not True
            or ref.get("independent_qa_approved") is not False
            or ref.get("legal_license_signoff") is not False
            or ref.get("consumer_signature_verified_after_handoff") is not False
            or ref.get("new_generic_package_export_allowed") is not False
            or ref.get("automatic_rule_application_allowed") is not False
            or ref.get("source_code_executed") is not False
            or ref.get("pack_bytes_copied") is not False
            or ref.get("new_signature_created") is not False
            or ref.get("network_requests") != 0
            or ref.get("operating_database_writes") != 0
            or ref.get("package_released") is not False
            or ref.get("v1_accepted") is not False):
        raise W09AcceptanceError("original producer did not create safe signed reference")
    return ref


def _separate_process_consumer(
        root: Path, *, reference: dict,
        serial4: Path, trust: Path,
        serial5: Path | None) -> dict:
    # Code comes ONLY from our current UCIE checkout, not from the
    # caller-provided synthetic package root. A disposable TEMP/UCIE
    # fixture deliberately contains no imported Python source.
    source_root=Path(__file__).resolve().parents[1]
    source_file=source_root/"ucie_miner"/"manual_consumer_v1.py"
    if (source_root.is_symlink()
            or (source_root/"ucie_miner").is_symlink()
            or source_file.is_symlink() or not source_file.is_file()
            or not 2000 <= source_file.stat().st_size <= 20000
            or (os.name == "nt" and root == Path("D:/UCIE").resolve()
                and source_root.parent != root)):
        raise W09AcceptanceError("exact current UCIE first-party consumer required")
    raw=json.dumps(reference,ensure_ascii=True,
                   sort_keys=True,separators=(",",":"),
                   allow_nan=False).encode("ascii")
    if len(raw)>4096:
        raise W09AcceptanceError("original manual reference too large")
    command=[
        sys.executable,"-I","-B","-c",_CHILD,str(source_root),
        "--ucie-root",str(root),
        "--serial4-pack",str(serial4),
        "--owner-public-trust",str(trust),
    ]
    if serial5 is not None:
        command.extend(("--serial5-pack",str(serial5)))
    try:
        child=subprocess.run(
            command,input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            cwd=root,check=False,timeout=40)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise W09AcceptanceError("original manual consumer execution failed closed") from exc
    if (child.returncode!=0 or not 0<len(child.stdout)<=8192
            or len(child.stderr)>8192):
        raise W09AcceptanceError("original independent consumer denied handoff")
    try:
        reply=json.loads(child.stdout.decode("utf-8-sig"))
    except (UnicodeError,ValueError) as exc:
        raise W09AcceptanceError("child emitted invalid bounded JSON") from exc
    return reply


def _consumer_receipt(reference: dict, observed: dict,
                      signed_qa: dict) -> dict:
    hashes=signed_qa.get("source_pack_sha256s")
    if (type(reference) is not dict or type(observed) is not dict
            or type(hashes) is not dict
            or reference.get("source_package_sha256") not in hashes.values()
            or reference.get("parent_serial4_sha256") != hashes.get("serial4")
            or reference.get("selected_library_item_id") not in (
                sha256((code+":"+digest).encode("ascii")).hexdigest()
                for code in signed_qa.get("rule_ids",[])
                for digest in hashes.values())
            or observed.get("schema") != MANUAL_SCHEMA
            or observed.get("status") != MANUAL_STATUS
            or observed.get("original_signature_trust_and_expiry_reverified_in_consumer") is not True
            or observed.get("selected_library_item_id") != reference.get("selected_library_item_id")
            or observed.get("rule_id") != reference.get("rule_id")
            or observed.get("pack_serial") != reference.get("pack_serial")
            or observed.get("source_pack_sha256") != reference.get("source_package_sha256")
            or observed.get("parent_serial4_sha256") != reference.get("parent_serial4_sha256")
            or observed.get("w09_descriptor_sha256") != reference.get("existing_w09_descriptor_sha256")
            or observed.get("handoff_reference_sha256") != _hash(reference)
            or observed.get("owner_risk_only") is not True
            or observed.get("consumer_action") != "INSPECT_EXISTING_SIGNED_RULE_IDENTITY_ONLY"
            or observed.get("actual_rule_scan_executed") is not False
            or observed.get("runtime_version_applicability_verified") is not False
            or observed.get("independent_qa_approved") is not False
            or observed.get("legal_license_signoff") is not False
            or observed.get("new_generic_package_export_allowed") is not False
            or observed.get("automatic_rule_application_allowed") is not False
            or observed.get("pack_bytes_copied") is not False
            or observed.get("external_project_files_read") is not False
            or observed.get("network_requests") != 0
            or observed.get("operating_database_writes") != 0
            or observed.get("new_signature_created") is not False
            or observed.get("package_released") is not False
            or observed.get("v1_accepted") is not False):
        raise W09AcceptanceError("consumer result does not match original signed references")
    return {
        "status":MANUAL_STATUS,
        "selected_library_item_id":reference["selected_library_item_id"],
        "rule_id":reference["rule_id"],
        "pack_serial":reference["pack_serial"],
        "original_pack_sha256":reference["source_package_sha256"],
        "original_w09_descriptor_sha256":reference["existing_w09_descriptor_sha256"],
        "reference_sha256":_hash(reference),
        "consumer_subprocess_reverified_signature":True,
        "consumer_subprocess_ran_signed_rule_scan":False,
        "independent_rule_quality_QA_approved":False,
        "new_package_export_allowed":False,
    }


def inspect_w09_consumer_acceptance(
        root: Path, *,
        serial4_pack: Path | None=None,
        owner_public_trust: Path | None=None,
        serial5_pack: Path | None=None,
        select_item_id: str | None=None,
        queries: int=32, repeats: int=3) -> dict:
    root=_root(root)
    if (type(queries) is not int or not 8<=queries<=96
            or type(repeats) is not int or not 1<=repeats<=5
            or select_item_id is not None and (
                type(select_item_id) is not str or
                HASH64.fullmatch(select_item_id) is None)
            or (serial4_pack is None)!=(owner_public_trust is None)
            or serial5_pack is not None and serial4_pack is None
            or select_item_id is not None and serial4_pack is None):
        raise W09AcceptanceError("bounded exact original W09 source selection required")
    # W07/W08 is a fresh first-party measurement + optional genuine
    # cryptographic verification, not a caller-provided approval receipt.
    board=independent_review_board(
        root,queries=queries,repeats=repeats,
        serial4_pack=serial4_pack,owner_public_trust=owner_public_trust,
        serial5_pack=serial5_pack)
    signed=board.get("existing_w07_signed_manual_rule_references")
    if (board.get("schema")!=REVIEW_SCHEMA
            or board.get("status") not in (REVIEW_COMPLETE,REVIEW_PARTIAL)
            or type(signed) is not dict
            or board.get("independent_human_qa_approved") is not False
            or board.get("license_and_rights_signoff") is not False
            or board.get("explicit_owner_new_release_approval") is not False
            or board.get("new_production_rulepack_signed") is not False
            or board.get("new_generic_package_export_allowed") is not False
            or board.get("network_requests")!=0
            or board.get("operating_database_writes")!=0
            or board.get("auto_promoted") is not False
            or board.get("customer_release_authorized") is not False):
        raise W09AcceptanceError("W07/W08 real owner QA boundary drift")
    portable=_portable(root)
    manual=None
    if select_item_id is not None:
        if (board["status"]!=REVIEW_COMPLETE
                or signed.get("original_crypto_reverified") is not True):
            raise W09AcceptanceError("cannot consume unsigned or unlinked owner Rulepack")
        original=_producer(
            root,serial4=serial4_pack,trust=owner_public_trust,
            serial5=serial5_pack,selected=select_item_id)
        verified=_separate_process_consumer(
            root,reference=original,serial4=serial4_pack,
            trust=owner_public_trust,serial5=serial5_pack)
        manual=_consumer_receipt(original,verified,signed)
    status=(REVERIFIED if manual is not None else
            NO_SELECTION if signed.get("original_crypto_reverified") is True
            else NO_SIGNED)
    payload={
        "schema":SCHEMA, "status":status,
        "w07_w08_review_status":board["status"],
        "w07_w08_qa_handoff_sha256":board["qa_handoff_evidence_sha256"],
        "w08_first_party_real_metadata_rows":board[
            "real_metadata_benchmark"]["metadata_rows"],
        "w08_heldout_query_count":board[
            "first_party_independent_oracle"]["heldout_query_count"],
        "w08_heldout_mismatched_results":board[
            "first_party_independent_oracle"]["mismatched_expected_results"],
        "portable_first_party_draft_independent_QA":portable,
        "signed_rule_manual_consumer":manual,
        "owner_signed_original_supplied":signed["original_crypto_reverified"],
        "manual_selection_present":select_item_id is not None,
        "independent_human_qa_approved":False,
        "source_license_and_redistribution_signoff":False,
        "production_consumer_host_accepted":False,
        "owner_new_release_approved":False,
        "remaining_release_gates":list(RELEASE_BLOCKERS),
        "unsigned_candidates_promoted":0,
        "new_package_created_or_exported":False,
        "new_signature_created":False,
        "automatic_rule_execution":False,
        "upstream_public_candidate_code_executed":False,
        "network_requests":0,"operating_database_writes":0,
        "scheduler_modified":False,"model_weights_changed":False,
        "auto_promoted":False,"v1_accepted":False,
        "customer_release_authorized":False,
    }
    # Unsigned, bounded reproducibility handle only. NOT a release token.
    payload["review_digest_sha256"]=_hash({
        "schema":SCHEMA,"status":status,
        "w07_w08_qa_handoff_sha256":payload["w07_w08_qa_handoff_sha256"],
        "portable_draft_sha256":portable["draft_package_sha256"],
        "selected_rule_id":manual["selected_library_item_id"]
                           if manual else None,
        "consumer_reference_sha256":manual["reference_sha256"]
                                  if manual else None,
    })
    payload["review_digest_is_release_authorization"]=False
    return payload


def main()->int:
    p=argparse.ArgumentParser(
        description="UCIE W09 independent consumers, owner manual-scope only")
    p.add_argument("--ucie-root",type=Path,required=True)
    p.add_argument("--serial4-pack",type=Path)
    p.add_argument("--owner-public-trust",type=Path)
    p.add_argument("--serial5-pack",type=Path)
    p.add_argument("--select-item",dest="select_item_id")
    p.add_argument("--queries",type=int,default=32)
    p.add_argument("--repeats",type=int,default=3)
    a=p.parse_args()
    try:
        out=inspect_w09_consumer_acceptance(
            a.ucie_root,serial4_pack=a.serial4_pack,
            owner_public_trust=a.owner_public_trust,
            serial5_pack=a.serial5_pack,
            select_item_id=a.select_item_id,
            queries=a.queries,repeats=a.repeats)
    except (W09AcceptanceError,ReadinessError,ProductIntegrationError,
            SignedLibraryError,OSError,TypeError,ValueError) as exc:
        print(json.dumps({
            "schema":SCHEMA,"status":"W09_CONSUMER_ACCEPTANCE_FAIL_CLOSED",
            "error_type":type(exc).__name__,
            "network_requests":0,"operating_database_writes":0,
            "new_package_created_or_exported":False,
            "auto_promoted":False,"customer_release_authorized":False,
        },sort_keys=True))
        return 2
    print(json.dumps(out,sort_keys=True,ensure_ascii=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
