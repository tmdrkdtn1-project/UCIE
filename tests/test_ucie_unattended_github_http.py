"""UCIE restricted GitHub HTTP transport: mock opener, zero network."""
import io
import json
import unittest
import urllib.error

from ucie_public.policy import PolicyError
from ucie_public.unattended_github import GH_API_REPO
from ucie_public.unattended_github_http import (
    HOST, UCIERestrictedGitHubHTTP,
)

TOKEN = "ucie_fake_test_token_X" + "a" * 30


class FakeResponse:
    def __init__(self, payload=b'{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}',
                 status=201, mime="application/json"):
        self.content = payload
        self.status = status
        self.headers = {"Content-Type": mime}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size=-1):
        return self.content[:size]


class FakeOpen:
    def __init__(self, response=None):
        self.requests = []
        self.response = response or FakeResponse()

    def open(self, req, timeout):
        self.requests.append((req, timeout))
        return self.response


class UCIERestrictedHTTPTests(unittest.TestCase):
    def test_denies_implicit_activation_and_invalid_owner_token(self):
        with self.assertRaises(PolicyError):
            UCIERestrictedGitHubHTTP(TOKEN)
        for t in ("", "short", "a\n" + "b"*25, "한글"*30):
            with self.subTest(token_type=len(t)):
                with self.assertRaises(PolicyError):
                    UCIERestrictedGitHubHTTP(t, allow_live=True, opener=FakeOpen())

    def test_fixed_get_and_post_go_to_one_https_repository_only(self):
        fake = FakeOpen()
        http = UCIERestrictedGitHubHTTP(TOKEN, allow_live=True, opener=fake)
        result = http("GET", GH_API_REPO + "/git/ref/heads/main")
        self.assertEqual(result["sha"], "a"*40)
        result = http("POST", GH_API_REPO + "/git/blobs",
                      {"content": "dGVzdA==", "encoding": "base64"})
        self.assertEqual(result["sha"], "a"*40)
        self.assertEqual(len(fake.requests), 2)
        for req, timeout in fake.requests:
            self.assertTrue(req.full_url.startswith(HOST + GH_API_REPO + "/"))
            self.assertEqual(timeout, 10)
            self.assertEqual(req.get_header("Authorization"), "Bearer " + TOKEN)
        self.assertNotIn(TOKEN, repr(http))

    def test_denies_other_project_endpoints_and_unsafe_methods(self):
        fake = FakeOpen()
        http = UCIERestrictedGitHubHTTP(TOKEN, allow_live=True, opener=fake)
        cases = (
            ("GET", "/repos/other/private/git/ref/heads/main", None),
            ("DELETE", GH_API_REPO + "/git/refs/heads/main", None),
            ("POST", GH_API_REPO + "/git/refs/heads/main", {}),
            ("POST", GH_API_REPO + "/actions/workflows", {}),
            ("GET", GH_API_REPO + "/contents/.env", None),
            ("GET", GH_API_REPO + "/git/ref/heads/main?token=x", None),
            ("GET", GH_API_REPO + "/git/ref/heads/automation/ucie-../../main", None),
            ("GET", GH_API_REPO + "/git/ref/heads/main", {}),
            ("POST", GH_API_REPO + "/git/blobs", "raw code"),
        )
        for method, path, body in cases:
            with self.subTest(method=method, path=path), self.assertRaises(PolicyError):
                http(method, path, body)
        self.assertEqual(fake.requests, [])

    def test_accepts_only_404_branch_nonexistence(self):
        fake = FakeOpen()
        fake.response = None
        def simulated_404(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, None)
        fake.open = simulated_404
        http = UCIERestrictedGitHubHTTP(TOKEN, allow_live=True, opener=fake)
        self.assertEqual(http("GET", GH_API_REPO +
                         "/git/ref/heads/automation/ucie-valid"), {"http_status":404})
        with self.assertRaises(PolicyError):
            http("GET", GH_API_REPO + "/git/ref/heads/main")

    def test_bounds_bodies_and_responses_before_data_trust(self):
        for response in (
            FakeResponse(status=302),
            FakeResponse(mime="text/html"),
            FakeResponse(payload=b"not json"),
            FakeResponse(payload=b'{"a":1,"a":2}'),
            FakeResponse(payload=b"[" + b"x"*200000 + b"]"),
            FakeResponse(payload=b"[]"),
        ):
            fake = FakeOpen(response)
            http = UCIERestrictedGitHubHTTP(TOKEN, allow_live=True, opener=fake)
            with self.subTest(status=response.status, body=response.content[:10]):
                with self.assertRaises(PolicyError):
                    http("GET", GH_API_REPO + "/git/ref/heads/main")
        http = UCIERestrictedGitHubHTTP(TOKEN, allow_live=True, opener=FakeOpen())
        with self.assertRaises(PolicyError):
            http("POST", GH_API_REPO + "/git/blobs", {"content": "x"*400000})


if __name__ == "__main__":
    unittest.main()
