"""C3.1: explicitly pinned, offline, read-only LOCAL preview of signed PUBLIC PR metadata.

Not customer entitlement, redistribution, source-code import or independent
upstream verification. This module never creates, loads or exports a private key.
A separately accepted owner public-key ID and serial floor are REQUIRED at
process startup, not obtained from an untrusted envelope, URL or form.

The existing owner Local V04 handler remains unchanged. A signed sidecar still
fails closed on ordinary unsigned /local/library and /local/evolution pages.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import quote, urlsplit

from . import local_public_pr_capsule_v01 as capsule
from . import local_public_pr_owner_auth_v01 as auth
from . import local_v1_app_v01 as local
from .local_portable_official_reference_v01 import reference_only
from .local_v1_priority_v01 import require_local_work

SCHEMA = "UCIE_C31_EXPLICIT_TRUSTED_LOCAL_PUBLIC_METADATA_VIEW_V01"
STATUS = "CRYPTOGRAPHIC_OWNER_KEY_MATCH_PUBLIC_METADATA_REVIEW_ONLY_NO_GO"
FAIL = "UCIE_C31_TRUST_FAIL_CLOSED_NO_GO"
ROUTE = "/local/trusted-public"


def read_signed_public_review(root: Path, *, expected_owner_key_id: str,
                              min_serial: int,
                              now: datetime | None = None) -> tuple[dict, dict]:
    """Load exactly three fixed review files plus one separately pinned public PEM.

    The public PEM under .build_keys is never inferred from capsule/signature.
    This function does not establish that the person controlling the key ID
    approved its out-of-band provision; the result explicitly retains false.
    """
    if (not isinstance(root, Path) or not root.is_absolute()
            or type(expected_owner_key_id) is not str
            or auth.KEYID.fullmatch(expected_owner_key_id) is None
            or type(min_serial) is not int
            or not 1 <= min_serial <= auth.MAX_SERIAL):
        raise auth.OwnerMetadataAuthError("explicit external owner trust policy required")
    capsule._root(root)
    # Never let a recipient with a nonempty or symlinked runtime bypass
    # existing authoritative owner-operating-data readers.
    if reference_only(root) is not True:
        raise auth.OwnerMetadataAuthError("recipient must have empty UCIE runtime")
    pem = auth._safe_small(root / ".build_keys" / auth.TRUST_NAME,
                           max_bytes=auth.MAX_PEM)
    data = auth._safe_small(root / capsule.FILE, max_bytes=capsule.MAX_BYTES)
    pin = auth._safe_small(root / capsule.PIN, max_bytes=65)
    if pin != (sha256(data).hexdigest() + "\n").encode("ascii"):
        raise auth.OwnerMetadataAuthError("adjacent checksum inconsistent with signed capsule")
    signature = auth._safe_small(root / auth.SIGNATURE_FILE,
                                 max_bytes=auth.MAX_ATTESTATION)
    checked_time = datetime.now(timezone.utc) if now is None else now
    verified = auth.verify_owner_metadata_bytes(
        data, signature, pem, expected_owner_key_id=expected_owner_key_id,
        min_serial=min_serial, now=checked_time)
    inspected = capsule.inspect_capsule(data, sha256(data).hexdigest())
    if (inspected.get("status") != capsule.RECEIVER_STATUS
            or inspected.get("signature_verified") is not False
            or inspected.get("human_approved") is not False
            or inspected.get("customer_distribution_authorized") is not False
            or verified.get("signature_cryptographically_verified") is not True
            or verified.get("out_of_band_owner_approval_independently_proven") is not False
            or verified.get("customer_distribution_authorized") is not False):
        raise auth.OwnerMetadataAuthError("trusted metadata status boundary changed")
    return inspected, verified


def render_signed_public_review(root: Path, *, expected_owner_key_id: str,
                                min_serial: int, raw_query: str = "",
                                now: datetime | None = None) -> str:
    """Existing V04 shell and existing B2 unverified row renderer, no promotion."""
    args = local._params(raw_query, ("q", "page"))
    q = args.get("q", "")
    if local.QUERY.fullmatch(q) is None:
        raise local.LocalProductError("invalid trusted public review query")
    page = local._page_number(args)
    snapshot, verification = read_signed_public_review(
        root, expected_owner_key_id=expected_owner_key_id,
        min_serial=min_serial, now=now)
    search = capsule.search_capsule(
        snapshot, query=q, limit=local.PAGE_SIZE,
        offset=(page - 1) * local.PAGE_SIZE)
    if page > 1 and not search["items"]:
        raise local.LocalProductError("trusted public review page not found")
    rows = local._evidence_rows(
        search, query=q, page=page, route="/local/library")
    total = search["total_matches"]
    omitted = snapshot["omitted_count"]
    safe_q = local._e(q)
    # The authenticated envelope is separate from the B2 capsule. B2 rows
    # remain UNVERIFIED_CANDIDATE_ONLY; /local/review stays unavailable.
    main = (
        '<section class="workbench-note" data-c31-owner-signature="verified" '
        'data-c31-customer-release="false">'
        '<h1>공개 메타데이터 서명 검증</h1>'
        '<p><strong>Ed25519 서명 검증 성공</strong> · '
        '실행자가 별도로 제공한 공개키 및 키 식별자와 일치합니다.</p>'
        '<p>단, 소유자가 이 신뢰키의 등록을 승인했다는 사실, '
        '상위 공개 PR의 수정 효과와 라이선스, 고객 배포권은 '
        '<strong>독립적으로 입증되지 않았습니다.</strong></p>'
        '<p>서명 순번: ' + str(verification["signed_serial"]) +
        ' · 만료 UTC: ' + local._e(verification["expiry_utc"]) +
        ' · 키 식별자: <code>' +
        local._e(verification["owner_key_id"]) + '</code></p>'
        '<p>검증 범위: 공개 메타데이터의 내용 무결성과 제공된 키의 소지 증명만. '
        '모든 후보는 여전히 UNVERIFIED_CANDIDATE_ONLY입니다.</p>'
        '</section>'
        '<section class="workbench-note"><h2>공개 후보 검토</h2>'
        '<form action="' + ROUTE + '" method="get">'
        '<label for="ucie-c31-q">공개 출처 또는 기술 검색</label>'
        '<input id="ucie-c31-q" name="q" value="' + safe_q +
        '" maxlength="80" autocomplete="off">'
        '<button type="submit">읽기 전용 검색</button></form>'
        '<p>검색 결과 ' + str(total) + '건 · 캡슐 선택 외 제외 ' +
        str(omitted) + '건. 개별 승인·자동 적용은 불가합니다.</p>'
        '</section>' + rows
    )
    if total > page * local.PAGE_SIZE:
        href = ROUTE + "?q=" + quote(q, safe="") + "&amp;page=" + str(page + 1)
        main += ('<p><a href="' + local._e(href) +
                 '">다음 공개 후보 보기</a></p>')
    if page > 1:
        href = ROUTE + "?q=" + quote(q, safe="") + "&amp;page=" + str(page - 1)
        main += ('<p><a href="' + local._e(href) +
                 '">이전 공개 후보 보기</a></p>')
    # Existing V04 shell accepts only its registered page keys. Reuse the
    # reviewed library envelope; our signed review heading stays in main.
    return local._page("통합 가상도서관", main)


def make_trusted_handler(root: Path, *, expected_owner_key_id: str,
                         min_serial: int):
    """One new GET-only local route; existing V04 unsigned paths remain strict."""
    if not isinstance(root, Path) or not root.is_absolute():
        raise auth.OwnerMetadataAuthError("absolute recipient UCIE root required")
    if (type(expected_owner_key_id) is not str
            or auth.KEYID.fullmatch(expected_owner_key_id) is None
            or type(min_serial) is not int
            or not 1 <= min_serial <= auth.MAX_SERIAL):
        raise auth.OwnerMetadataAuthError("trusted recipient policy missing")
    parent = local.make_handler(root)

    class TrustedRecipientHandler(parent):
        def do_GET(self):
            parts = urlsplit(self.path)
            if parts.path != ROUTE:
                return super().do_GET()
            if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                return self.reply(403, "LOOPBACK_ONLY",
                                  "text/plain; charset=utf-8")
            if (len(self.path) > 300 or parts.fragment or parts.scheme
                    or parts.netloc):
                return self.reply(400, FAIL, "text/plain; charset=utf-8")
            try:
                html = render_signed_public_review(
                    root, expected_owner_key_id=expected_owner_key_id,
                    min_serial=min_serial, raw_query=parts.query)
                return self.reply(200, html)
            except (ValueError, TypeError, KeyError, OSError):
                return self.reply(400, FAIL, "text/plain; charset=utf-8")

    return TrustedRecipientHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="C3.1 offline UCIE public metadata trusted read-only preview")
    parser.add_argument("--recipient-ucie-root", type=Path, required=True)
    parser.add_argument("--expected-owner-key-id", required=True)
    parser.add_argument("--min-serial", type=int, required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        require_local_work("LOCAL_APP")
        if (args.port != 0 and not 1024 <= args.port <= 65535):
            raise auth.OwnerMetadataAuthError("local port invalid")
        # Fail before opening a listener when any signed trust input is invalid.
        snapshot, verified = read_signed_public_review(
            args.recipient_ucie_root,
            expected_owner_key_id=args.expected_owner_key_id,
            min_serial=args.min_serial)
        handler = make_trusted_handler(
            args.recipient_ucie_root,
            expected_owner_key_id=args.expected_owner_key_id,
            min_serial=args.min_serial)
        with local.LOCAL_SERVER_CLASS(("127.0.0.1", args.port), handler) as server:
            print(json.dumps({
                "schema": SCHEMA, "status": STATUS,
                "local_preview_url": "http://127.0.0.1:" +
                                     str(server.server_port) + ROUTE,
                "selected_unverified_public_rows": snapshot["selected_count"],
                "signature_cryptographically_verified_at_start": True,
                "owner_public_key_matches_supplied_trust_pin":
                    verified["owner_public_key_matches_supplied_trust_pin"],
                "out_of_band_owner_approval_independently_proven": False,
                "customer_distribution_authorized": False,
                "private_key_accessed": False,
                "customer_package_created": False,
            }, sort_keys=True), flush=True)
            server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        return 0
    except (ValueError, TypeError, KeyError, OSError):
        print(json.dumps({
            "schema": SCHEMA, "status": FAIL,
            "private_key_accessed": False,
            "customer_distribution_authorized": False,
        }, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
