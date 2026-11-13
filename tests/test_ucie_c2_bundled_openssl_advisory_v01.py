"""C2 official OpenSSL embedded advisory vs. PyPI top-level zero count, offline."""
from __future__ import annotations

import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from ucie_miner import customer_c2_bundled_openssl_advisory_v01 as c2


class C2EmbeddedNativeAdvisoryTests(unittest.TestCase):
    def test_01_actual_pinned_openssl_advisories_not_hidden(self):
        report=c2.assess_current_embedded_openssl(
            cryptography_version="50.0.2",
            pypi_versioned_advisories_observed=0)
        self.assertEqual(report["embedded_openssl_version_declared_by_upstream"],"4.0.3")
        self.assertEqual(report["known_embedded_openssl_advisory_count"],5)
        self.assertEqual(report["pypi_versioned_advisories_observed"],0)
        self.assertEqual(report["official_advisory_published"],"2026-11-10")
        self.assertTrue(report["pypi_zero_vulnerabilities_is_not_a_embedded_openssl_clearance"])
        self.assertFalse(report["human_owner_security_risk_disposition_approved"])
        self.assertFalse(report["customer_distribution_authorized"])
        self.assertEqual(report["external_network_requests"],0)

    def test_02_all_five_official_cves_distinct(self):
        report=c2.assess_current_embedded_openssl()
        actual={x["cve"] for x in report["known_embedded_openssl_advisories"]}
        self.assertEqual(actual,{
            "CVE-2026-88822","CVE-2026-88823",
            "CVE-2026-95691","CVE-2026-95692",
            "CVE-2026-107496"})
        self.assertEqual({x["upstream_severity"]
                          for x in report["known_embedded_openssl_advisories"]},{"Low"})
        self.assertEqual({x["assessed_application_reachability"]
                          for x in report["known_embedded_openssl_advisories"]},{"UNVERIFIED"})

    def test_03_unreviewed_vendor_version_rejected(self):
        for other in ("50.0.3","50.0.1","51.0.0","../../bad",""):
            with self.subTest(other=other),self.assertRaises(ValueError):
                c2.assess_current_embedded_openssl(cryptography_version=other)

    def test_04_untrusted_advisory_counts_rejected(self):
        for x in (True,False,-1,"0",1.1,10001,[],{}):
            with self.subTest(x=x),self.assertRaises(ValueError):
                c2.assess_current_embedded_openssl(
                    pypi_versioned_advisories_observed=x)

    def test_05_offline CLI_returns_intentional_no_go_exit2(self):
        output=StringIO()
        with redirect_stdout(output):
            status=c2.main(["--offline-c2-review"])
        value=json.loads(output.getvalue())
        self.assertEqual(status,2)
        self.assertFalse(value["security_clearance_for_customer_distribution"])

    def test_06_never_reads_owner_private_files_or_runs_network(self):
        with patch("urllib.request.urlopen",side_effect=AssertionError("network used")):
            with patch("builtins.open",side_effect=AssertionError("owner file opened")):
                r=c2.assess_current_embedded_openssl()
        self.assertFalse(r["owner_private_material_accessed"])
        self.assertFalse(r["customer_distribution_authorized"])


if __name__=="__main__":
    unittest.main()
