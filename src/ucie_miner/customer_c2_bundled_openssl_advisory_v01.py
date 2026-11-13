"""UCIE C2: official advisory evidence for OpenSSL shipped INSIDE cryptography.

A per-version PyPI "vulnerabilities":[] response does NOT clear bundled
OpenSSL vulnerabilities. This is an offline, narrowly version-pinned
first-party security-review preflight, not an external code-mining source,
not a network client, and not a commercial release authorization.

Sources verified 2026-11-13:
  https://cryptography.io/en/50.0.2/changelog/
  https://www.openssl-library.org/news/vulnerabilities-4.0/
  https://www.openssl-library.org/news/timeline/
"""
from __future__ import annotations

import json
from datetime import date

SCHEMA = "UCIE_C2_PINNED_STATIC_OPENSSL_NOV10_ADVISORY_GATE_V01"
STATUS = "C2_EMBEDDED_OPENSSL_4_0_3_NOV10_SECURITY_DISPOSITION_REQUIRED_NO_GO"
CRYPTO_PIN = "50.0.2"
EMBEDDED_OPENSSL = "4.0.3"
DISCLOSED = "2026-11-10"
FIRST_PARTY_API_OBSERVATION = "NO_DIRECT_MATCH_IN_2026_11_13_UCIE_SOURCE_SEARCH_NOT_REACHABILITY_PROOF"
CVES = (
    ("CVE-2026-88822", "QUIC_AUTO_PEER_DETECTION"),
    ("CVE-2026-88823", "AES_GCM_SIV_FRAGMENTED_EMPTY_AAD"),
    ("CVE-2026-95691", "QUIC_RETRANSMITTED_CRYPTO_FRAMES"),
    ("CVE-2026-95692", "AES_GCM_SIV_NONSTANDARD_IV_LENGTH"),
    ("CVE-2026-107496", "CMS_ENCRYPT_EXPLICIT_EC_GROUP_ORDER_ONE"),
)
SOURCES = (
    "https://cryptography.io/en/50.0.2/changelog/",
    "https://www.openssl-library.org/news/vulnerabilities-4.0/",
    "https://www.openssl-library.org/news/timeline/",
)


class OpenSSLAdvisoryGateError(ValueError):
    """Unreviewed pinned vendor is never security-approved."""


def assess_current_embedded_openssl(
    *, cryptography_version: str = CRYPTO_PIN,
    pypi_versioned_advisories_observed: int | None = None,
) -> dict:
    """Report real known embedded advisories without implying exploitable UCIE paths."""
    if (type(cryptography_version) is not str or cryptography_version != CRYPTO_PIN
            or pypi_versioned_advisories_observed is not None
            and (type(pypi_versioned_advisories_observed) is not int
                 or not 0 <= pypi_versioned_advisories_observed <= 10000)):
        raise OpenSSLAdvisoryGateError("reviewed cryptography pin or PyPI count changed")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "vendor": "cryptography",
        "vendor_version": CRYPTO_PIN,
        "bundled_native_component": "OpenSSL",
        "embedded_openssl_version_declared_by_upstream": EMBEDDED_OPENSSL,
        "openssl_release_version_independently_inspected_in_actual_owner_binary": False,
        "official_advisory_published": DISCLOSED,
        "official_affected_openssl_series": "4.0.0 through 4.0.3 inclusive",
        "official_fix_version_in_openssl_4_0_series": "4.0.4",
        "openssl_4_0_4_release_and_fixed_cryptography_wheel_currently_verified": False,
        "known_embedded_openssl_advisory_count": len(CVES),
        "known_embedded_openssl_advisories": [
            {"cve": cve, "affected_feature": feature, "upstream_severity": "Low",
             "assessed_application_reachability": "UNVERIFIED"}
            for cve, feature in CVES
        ],
        "first_party_direct_call_string_review": FIRST_PARTY_API_OBSERVATION,
        "source_search_not_full_binary_transitive_reachability_review": True,
        "pypi_versioned_advisories_observed": pypi_versioned_advisories_observed,
        "pypi_zero_vulnerabilities_is_not_a_embedded_openssl_clearance": True,
        "publisher_signature_independently_verified": False,
        "human_owner_security_risk_disposition_approved": False,
        "security_clearance_for_customer_distribution": False,
        "customer_distribution_authorized": False,
        "external_network_requests": 0,
        "owner_private_material_accessed": False,
        "operating_database_writes": 0,
        "source_urls": list(SOURCES),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    a=argparse.ArgumentParser(description="UCIE exact pinned bundled OpenSSL security review")
    a.add_argument("--offline-c2-review",action="store_true")
    args=a.parse_args(argv)
    if not args.offline_c2_review:
        a.error("explicit offline-only review flag required")
    print(json.dumps(assess_current_embedded_openssl(),sort_keys=True))
    # Technical evidence obtained, but security/customer review is STILL HOLD.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
