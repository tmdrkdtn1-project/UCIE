"""UCIE-only GitHub REST HTTP transport, NEVER auto-activated.

Provides fixed endpoints only. Owner installer must separately authenticate the
Windows principal, token origin, owner signed task and external replay anchor
BEFORE constructing the live transport. No module import side effects.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from .policy import PolicyError
from .rulepack import canonical_json
from .unattended_github import GH_API_REPO
from .unattended_ops import BRANCH, SHA40, _path_allowed

HOST = "https://api.github.com"
MAX_RESPONSE_BYTES = 180000
MAX_REQUEST_BYTES = 300000
_ALLOWED_POST = frozenset({
    "/git/blobs", "/git/trees", "/git/commits", "/git/refs", "/pulls"
})


class _DenyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        return None


def _allowed_route(method: object, path: object) -> bool:
    if type(method) is not str or type(path) is not str:
        return False
    if not path.startswith(GH_API_REPO + "/"):
        return False
    suffix = path[len(GH_API_REPO):]
    if method == "POST":
        return suffix in _ALLOWED_POST
    if method != "GET":
        return False
    if suffix == "/git/ref/heads/main":
        return True
    if suffix.startswith("/git/ref/heads/"):
        return bool(BRANCH.fullmatch(suffix[len("/git/ref/heads/"):]))
    if suffix.startswith("/git/commits/"):
        return bool(SHA40.fullmatch(suffix[len("/git/commits/"):]))
    return False


def _json_unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate untrusted GitHub JSON key")
        out[key] = value
    return out


def _safe_body(method: str, path: str, payload: object, branch: str,
               base_sha: str) -> bool:
    """Refuse a protected ref even through an allowed REST endpoint."""
    if method == "GET":
        return payload is None
    if type(payload) is not dict:
        return False
    suffix = path[len(GH_API_REPO):]
    if suffix == "/git/blobs":
        if set(payload) != {"content", "encoding"} or payload["encoding"] != "base64":
            return False
        try:
            import base64
            body = base64.b64decode(payload["content"], validate=True)
            return 1 <= len(body) <= 65536
        except (ValueError, TypeError, UnicodeError):
            return False
    if suffix == "/git/trees":
        if (set(payload) != {"base_tree", "tree"} or
                type(payload["base_tree"]) is not str or
                SHA40.fullmatch(payload["base_tree"]) is None or
                type(payload["tree"]) is not list or
                not 1 <= len(payload["tree"]) <= 25):
            return False
        names = []
        for part in payload["tree"]:
            if (type(part) is not dict or set(part) != {"path", "mode", "type", "sha"}
                    or not _path_allowed(part["path"]) or
                    part["mode"] != "100644" or part["type"] != "blob" or
                    type(part["sha"]) is not str or
                    SHA40.fullmatch(part["sha"]) is None):
                return False
            names.append(part["path"])
        return len(names) == len(set(names))
    if suffix == "/git/commits":
        return (set(payload) == {"message", "tree", "parents"} and
                type(payload["message"]) is str and
                payload["message"].startswith("ucie(automation): ") and
                "\n" not in payload["message"] and
                type(payload["tree"]) is str and
                SHA40.fullmatch(payload["tree"]) is not None and
                type(payload["parents"]) is list and
                payload["parents"] == [base_sha])
    if suffix == "/git/refs":
        return (set(payload) == {"ref", "sha"} and
                payload["ref"] == "refs/heads/" + branch and
                type(payload["sha"]) is str and
                SHA40.fullmatch(payload["sha"]) is not None)
    if suffix == "/pulls":
        return (set(payload) == {
                    "title", "head", "base", "draft", "body",
                    "maintainer_can_modify"} and
                payload["head"] == branch and payload["base"] == "main" and
                payload["draft"] is True and
                payload["maintainer_can_modify"] is False and
                type(payload["title"]) is str and
                payload["title"].startswith("UCIE automation: ") and
                type(payload["body"]) is str and
                len(payload["body"]) < 600)
    return False


class UCIERestrictedGitHubHTTP:
    """Explicitly supplied owner-scoped token; no environment fallback.

    A request is NEVER authorized merely because allow_live=True; the
    independent trusted host runner must enforce owner grants/ACL/anti-replay.
    This class only constrains URL/method/body/response to one UCIE repo.
    """

    ucie_synthetic_only = False

    def __init__(self, bearer_token: str, *, branch: str, base_sha: str,
                 allow_live: bool = False, opener=None):
        if allow_live is not True:
            raise PolicyError("UCIE GitHub live HTTP disabled by default")
        if (type(bearer_token) is not str or
                not 20 <= len(bearer_token) <= 1200 or
                not bearer_token.isascii() or
                any(c.isspace() or ord(c) < 33 for c in bearer_token)):
            raise PolicyError("owner-scoped UCIE GitHub token unavailable")
        if (type(branch) is not str or BRANCH.fullmatch(branch) is None or
                type(base_sha) is not str or SHA40.fullmatch(base_sha) is None):
            raise PolicyError("owner-bound UCIE branch and base SHA required")
        self.__branch = branch
        self.__base_sha = base_sha
        self.__token = bearer_token
        self.__opener = opener if opener is not None else urllib.request.build_opener(_DenyRedirect)
        if not hasattr(self.__opener, "open"):
            raise PolicyError("invalid HTTPS transport")
    
    def __repr__(self):
        return "<UCIERestrictedGitHubHTTP redacted>"

    def __call__(self, method: str, path: str, payload: object = None) -> dict:
        if not _allowed_route(method, path):
            raise PolicyError("GitHub request path or method outside UCIE allowlist")
        if not _safe_body(method, path, payload, self.__branch, self.__base_sha):
            raise PolicyError("UCIE GitHub REST body outside approved branch intent")
        if method == "GET":
            if path.startswith(GH_API_REPO + "/git/ref/heads/automation/") and path != GH_API_REPO + "/git/ref/heads/" + self.__branch:
                raise PolicyError("unapproved automation branch lookup")
            if path.startswith(GH_API_REPO + "/git/commits/") and path != GH_API_REPO + "/git/commits/" + self.__base_sha:
                raise PolicyError("unapproved base commit lookup")
            body = None
        else:
            if type(payload) is not dict:
                raise PolicyError("bounded GitHub POST JSON object required")
            body = canonical_json(payload)
            if len(body) > MAX_REQUEST_BYTES:
                raise PolicyError("GitHub REST request too large")
        req = urllib.request.Request(
            HOST + path, data=body, method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "UCIE-Owner-GitPublisher/1",
                "Authorization": "Bearer " + self.__token,
                "Cache-Control": "no-store",
            })
        try:
            with self.__opener.open(req, timeout=10) as response:
                status = response.status
                mime = response.headers.get("Content-Type", "").lower()
                result_bytes = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            # Only the exact branch collision probe can accept 404; avoid
            # leaking response bodies, token-bearing URLs or credentials.
            if (method == "GET" and path.startswith(GH_API_REPO + "/git/ref/heads/automation/")
                    and exc.code == 404):
                return {"http_status": 404}
            raise PolicyError("UCIE GitHub HTTP request rejected") from None
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            raise PolicyError("UCIE GitHub HTTP unavailable") from None
        if status not in (200, 201) or "json" not in mime or len(result_bytes) > MAX_RESPONSE_BYTES:
            raise PolicyError("UCIE GitHub HTTP unexpected bounded response")
        try:
            data = json.loads(result_bytes.decode("utf-8"), object_pairs_hook=_json_unique)
        except (ValueError, UnicodeError) as exc:
            raise PolicyError("UCIE GitHub HTTP response malformed") from exc
        if type(data) is not dict:
            raise PolicyError("UCIE GitHub HTTP object expected")
        return data
