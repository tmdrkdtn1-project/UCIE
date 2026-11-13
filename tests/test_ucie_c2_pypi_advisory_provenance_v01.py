"""C2 pinned PyPI official advisory/provenance metadata: no owner wheel/keys."""
from __future__ import annotations

from base64 import b64encode
from io import BytesIO, StringIO
from contextlib import redirect_stdout
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from ucie_miner import customer_c2_pypi_advisory_provenance_v01 as c2


def release(name="cryptography", version="50.0.2",
            filename=None, digest=None, vulnerabilities=None):
    filename = filename or c2.PUBLIC_TEST_ONLY[name]
    digest = digest or "a"*64
    return {
        "info": {"name": name, "version": version},
        "urls": [{"packagetype": "bdist_wheel", "filename": filename,
                  "digests": {"sha256": digest}, "yanked": False}],
        "vulnerabilities": [] if vulnerabilities is None else vulnerabilities,
    }


def provenance(name="cryptography", filename=None, digest="a"*64):
    filename = filename or c2.PUBLIC_TEST_ONLY[name]
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": filename, "digest": {"sha256": digest}}],
        "predicateType": "https://docs.pypi.org/attestations/publish/v1",
        "predicate": None,
    }
    encoded = b64encode(json.dumps(statement, sort_keys=True).encode()).decode()
    return {
        "version": 1,
        "attestation_bundles": [
            {"publisher": {"kind": "GitHub", "repository": "pyca/cryptography",
                           "workflow": "pypi-publish.yml"},
             "attestations": [
                 {"envelope": {"statement": encoded, "signature": "synthetic-not-verified"}}
             ]},
        ],
    }


class C2OfficialPinnedParserTests(unittest.TestCase):
    def test_release_and_matching_provenance_are_claims_not_signatures(self):
        filename = c2.PUBLIC_TEST_ONLY["cryptography"]
        r = c2.assess_pinned_release(
            "cryptography", "50.0.2", filename, "a"*64,
            release(filename=filename), provenance(filename=filename))
        self.assertTrue(r["official_pypi_sha256_matches_supplied_pin"])
        self.assertTrue(r["pypi_integrity_endpoint_has_attestation"])
        self.assertTrue(r["pypi_attestation_subject_digest_matches"])
        self.assertEqual(r["pypi_publisher_claim"], ["GitHub:pyca/cryptography"])
        self.assertFalse(r["publisher_signature_cryptographically_verified_by_ucie"])
        self.assertFalse(r["vendor_license_legal_review_completed"])
        self.assertFalse(r["customer_distribution_authorized"])

    def test_version_specific_zero_advisories_never_claims_security(self):
        r = c2.assess_pinned_release(
            "cryptography", "50.0.2",
            c2.PUBLIC_TEST_ONLY["cryptography"], "a"*64,
            release(), None)
        self.assertEqual(r["pypi_versioned_advisory_count"], 0)
        self.assertTrue(r["no_reported_vulnerabilities_does_not_prove_security"])
        self.assertFalse(r["publisher_signature_cryptographically_verified_by_ucie"])
        self.assertFalse(r["pypi_integrity_endpoint_has_attestation"])

    def test_active_and_withdrawn_vuln_distinguished(self):
        r = c2.assess_pinned_release(
            "cryptography", "50.0.2",
            c2.PUBLIC_TEST_ONLY["cryptography"], "a"*64,
            release(vulnerabilities=[
                {"id": "PYSEC-2026-1", "withdrawn": None},
                {"id": "CVE-2026-12345", "withdrawn": "2026-10-14T12:00:00Z"},
            ]), None)
        self.assertEqual(r["pypi_versioned_advisory_count"], 1)
        self.assertEqual(r["pypi_versioned_advisory_ids"], ["PYSEC-2026-1"])
        self.assertEqual(r["withdrawn_advisory_count"], 1)
        self.assertFalse(r["customer_distribution_authorized"])

    def test_wrong_version_name_wheel_or_digest_rejected(self):
        base = release()
        filename = c2.PUBLIC_TEST_ONLY["cryptography"]
        variants = (
            ("cffi", "50.0.2", filename, "a"*64, base),
            ("cryptography", "99", filename, "a"*64, base),
            ("cryptography", "50.0.2", filename, "b"*64, base),
            ("cryptography", "50.0.2", "../evil.whl", "a"*64, base),
            ("cryptography", "50.0.2", filename, "A"*64, base),
            ("cryptography", "50.0.2", filename, "a"*64, {**base, "urls": []}),
            ("cryptography", "50.0.2", filename, "a"*64, {**base, "info": {"name": "cffi", "version": "50.0.2"}}),
        )
        for name, ver, fn, digest, body in variants:
            with self.subTest(name=name, ver=ver, fn=fn, digest=digest):
                with self.assertRaises(ValueError):
                    c2.assess_pinned_release(name, ver, fn, digest, body, None)

    def test_yanked_and_duplicate_wheel_metadata_rejected(self):
        r = release()
        r["urls"][0]["yanked"] = True
        with self.assertRaises(ValueError):
            c2.assess_pinned_release(
                "cryptography", "50.0.2",
                c2.PUBLIC_TEST_ONLY["cryptography"], "a"*64, r, None)
        r = release()
        r["urls"].append(dict(r["urls"][0]))
        with self.assertRaises(ValueError):
            c2.assess_pinned_release(
                "cryptography", "50.0.2",
                c2.PUBLIC_TEST_ONLY["cryptography"], "a"*64, r, None)

    def test_advisory_invalid_id_duplicate_or_missing_array_denied(self):
        for entries in (
            [{"id": "bad <tag>", "withdrawn": None}],
            [{"id": "GHSA-1", "withdrawn": None},
             {"id": "GHSA-1", "withdrawn": None}],
            [{"id": "PYSEC-2026-7", "withdrawn": 8}],
        ):
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                c2.assess_pinned_release(
                    "cryptography", "50.0.2",
                    c2.PUBLIC_TEST_ONLY["cryptography"], "a"*64,
                    release(vulnerabilities=entries), None)
        x = release()
        x.pop("vulnerabilities")
        with self.assertRaises(ValueError):
            c2.assess_pinned_release(
                "cryptography", "50.0.2",
                c2.PUBLIC_TEST_ONLY["cryptography"], "a"*64, x, None)

    def test_provenance_subject_sha_tamper_and_publisher_injection_denied(self):
        filename = c2.PUBLIC_TEST_ONLY["cryptography"]
        with self.assertRaises(ValueError):
            c2._parse_pypi_provenance(
                provenance(filename=filename, digest="b"*64),
                filename=filename, expected_sha256="a"*64)
        modified = provenance()
        modified["attestation_bundles"][0]["publisher"]["repository"] = "https://unapproved.example/bad"
        with self.assertRaises(ValueError):
            c2._parse_pypi_provenance(
                modified, filename=filename, expected_sha256="a"*64)
        modified = provenance()
        modified["attestation_bundles"][0]["attestations"][0]["envelope"]["statement"] = "???"
        with self.assertRaises(ValueError):
            c2._parse_pypi_provenance(
                modified, filename=filename, expected_sha256="a"*64)

    def test_attestation_absence_not_malicious_or_safety_pass(self):
        info = c2._parse_pypi_provenance(
            None, filename=c2.PUBLIC_TEST_ONLY["cffi"], expected_sha256="a"*64)
        self.assertFalse(info["pypi_integrity_endpoint_has_attestation"])
        self.assertTrue(info["attestation_absent_or_unavailable_at_query"])
        self.assertFalse(info["publisher_signature_cryptographically_verified_by_ucie"])

    def test_duplicate_json_fields_and_nan_denied(self):
        for raw in (b'{"a":1,"a":2}', b'{"bad": NaN}', b"[]", b"{}" * 50000):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                c2._parse(raw, 1_000)

    def test_unapproved_release_and_integrity_url_denied(self):
        for name, version in (("unknown", "1"), ("cffi", "1.0"),
                              ("pycparser", "../3.12")):
            with self.assertRaises(ValueError):
                c2._official_release_url(name, version)
        for fn in ("other-1.whl", "../escape", "cffi-2.1.1-evil?.whl"):
            with self.assertRaises(ValueError):
                c2._provenance_url("cffi", "2.1.1", fn)
        self.assertEqual(
            c2._official_release_url("cffi", "2.1.1"),
            "https://pypi.org/pypi/cffi/2.1.1/json")

    def test_direct_transport_rejects_external_host(self):
        for url in ("http://pypi.org/pypi/cffi/2.1.1/json",
                    "https://pypi.org.evil/pypi/cffi/2.1.1/json",
                    "https://example.net/report"):
            with self.assertRaises(ValueError):
                c2._get_json(url)

    def test_reject_unapproved_pypi_routes_and_disable_redirects(self):
        from urllib.request import Request
        for url, integrity in (
            ("https://pypi.org/pypi/unapproved/1/json", False),
            ("https://pypi.org/pypi/cryptography/50.0.1/json", False),
            ("https://pypi.org/integrity/other/1/other-1.whl/provenance", True),
            ("https://pypi.org/integrity/cryptography/50.0.2/../x/provenance", True),
            ("https://pypi.org/pypi/cffi/2.1.1/json", True),
        ):
            with self.subTest(url=url, integrity=integrity):
                with self.assertRaises(ValueError):
                    c2._get_json(url, integrity=integrity)
        req = Request("https://pypi.org/pypi/cffi/2.1.1/json")
        self.assertIsNone(c2._NoRedirect().redirect_request(
            req, None, 302, "Moved", {}, "https://offsite.example/payload"))

    def test_all_three_fixed_public_pins_true_identity_with_mocked_transport(self):
        def mocked(url, *, integrity=False):
            for name, version in c2.PINNED:
                fn = c2.PUBLIC_TEST_ONLY[name]
                if url == c2._official_release_url(name, version):
                    return release(name, version, filename=fn)
                if url == c2._provenance_url(name, version, fn):
                    return provenance(name, fn) if name == "cryptography" else None
            raise AssertionError("unlisted network endpoint")
        with patch.object(c2, "_get_json", side_effect=mocked):
            report = c2.review_once()
        self.assertEqual(report["packages_checked"], 3)
        self.assertFalse(report["actual_owner_wheel_captured_and_crosschecked"])
        self.assertEqual(report["pypi_published_attestation_objects_observed"], 1)
        self.assertEqual(report["pypi_versioned_advisories_observed"], 0)
        self.assertFalse(report["signatures_cryptographically_independently_verified"])
        self.assertFalse(report["customer_distribution_authorized"])
        self.assertEqual({x["distribution"] for x in report["packages"]},
                         {"cryptography", "cffi", "pycparser"})

    def test_owner_captured_digest_mismatch_must_fail_closed(self):
        captured = {
            name: {"filename": c2.PUBLIC_TEST_ONLY[name], "sha256": "b"*64}
            for name, _ in c2.PINNED
        }
        def mocked(url, *, integrity=False):
            for name, version in c2.PINNED:
                if url == c2._official_release_url(name, version):
                    return release(name, version)
                if url == c2._provenance_url(name, version, c2.PUBLIC_TEST_ONLY[name]):
                    return None
            raise AssertionError("unlisted network endpoint")
        with patch.object(c2, "_get_json", side_effect=mocked):
            with self.assertRaises(ValueError):
                c2.review_once(owner_capture=captured)

    def test_owner_key_wheelhouse_never_read_by_public_one_shot(self):
        with patch.object(c2, "_owner_capture", side_effect=AssertionError("owner file read")):
            with patch.object(c2, "review_once", return_value={
                "status": c2.STATUS, "customer_distribution_authorized": False,
            }) as review:
                out = StringIO()
                with redirect_stdout(out):
                    exit_code = c2.main(["--public-one-shot"])
                self.assertEqual(exit_code, 0)
                self.assertEqual(review.call_count, 1)
                self.assertFalse(json.loads(out.getvalue())["customer_distribution_authorized"])

    def test_default_is_zero_network_without_real_local_file_reads(self):
        with patch.object(c2, "_get_json", side_effect=AssertionError("network used")):
            with patch.object(c2, "_owner_capture", side_effect=AssertionError("owner accessed")):
                out = StringIO()
                with redirect_stdout(out):
                    code = c2.main([])
                self.assertEqual(code, 0)
                result = json.loads(out.getvalue())
                self.assertEqual(result["status"], c2.OFFLINE_STATUS)
                self.assertEqual(result["network_requests"], 0)
                self.assertFalse(result["customer_distribution_authorized"])

    def test_owner_mode_requires_consent_before_any_wheel_file_read(self):
        with patch.object(c2, "verify_local", side_effect=AssertionError("owner wheel scanned")):
            for denied in ("", "yes", c2.CONSENT + "!"):
                with self.subTest(denied=denied), self.assertRaises(ValueError):
                    c2._owner_capture(consent=denied)
            with patch("builtins.input", return_value="not-approved"):
                output = StringIO()
                with redirect_stdout(output):
                    code = c2.main(["--owner-existing-c1-once"])
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(output.getvalue())["status"], c2.FAIL_STATUS)


if __name__ == "__main__":
    unittest.main()
