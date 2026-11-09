"""Isolated, source-pinned MCP SDK *method* behavior probe.

Only for disposable Linux GitHub CI (python -I -S). Accepts four tiny files
from the approved upstream repository. Exact Git blob SHA-1 is checked before
AST extraction. No upstream imports, dependencies, subprocesses or network
operations. This is NOT a full SDK client/server or wire-protocol test.
"""
from __future__ import annotations

import ast
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

SCHEMA = "UCIE_MCP_PINNED_UPSTREAM_METHOD_PROBE_V01"
BASE_COMMIT = "2118f14f8a19bc158d8a1cf90af58d85d187f849"
FIXED_COMMIT = "754254c08fe1c3eda18b69da3d336106fe8d72d6"
# One full file per variant, not bulk upstream source harvesting.
FILE_BLOBS = {
    "before_manager.py": "01a0823bf74c72c2197b846bf94a5f0ff00dfcea",
    "before_base.py": "a13b72f1aa0eb4f15dddc42b4442a4246479cf6b",
    "after_manager.py": "6ad5dfb8c654c2f965c5e25424a588a771e3c858",
    "after_base.py": "32372a527a6e9b7d352b5371d524288342fd99b2",
}
MAX_BYTES = 20_000
INVALID_PARAMS = -32602


class SourceGateError(ValueError):
    """Explicit fail-closed pinned source or AST mismatch."""


class MinimalMCPError(Exception):
    """UCIE-only exception surface for the extracted method sandbox."""

    def __init__(self, *, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(content)).encode("ascii") + b"\0" + content,
        usedforsecurity=False,
    ).hexdigest()


def check_source_payload(name: str, payload: bytes) -> ast.Module:
    if name not in FILE_BLOBS or type(payload) is not bytes:
        raise SourceGateError("UNREGISTERED_SOURCE")
    if not (1 <= len(payload) <= MAX_BYTES):
        raise SourceGateError("SOURCE_SIZE_INVALID")
    if git_blob_sha(payload) != FILE_BLOBS[name]:
        raise SourceGateError("GIT_BLOB_SHA_MISMATCH")
    try:
        parsed = ast.parse(payload.decode("utf-8"))
    except (UnicodeError, SyntaxError, ValueError) as exc:
        raise SourceGateError("PINNED_SOURCE_INVALID_AST") from exc
    return parsed


def source_method(parsed: ast.Module, owner: str, name: str) -> ast.AsyncFunctionDef:
    owners = [
        item for item in parsed.body
        if isinstance(item, ast.ClassDef) and item.name == owner
    ]
    if len(owners) != 1:
        raise SourceGateError("MISSING_EXACT_OWNER_CLASS")
    methods = [
        item for item in owners[0].body
        if isinstance(item, ast.AsyncFunctionDef) and item.name == name
    ]
    if len(methods) != 1:
        raise SourceGateError("MISSING_EXACT_ASYNC_METHOD")
    return methods[0]


def extract_vetted_manager_function(
    parsed: ast.Module, *, fixed: bool,
) -> Any:
    """Compile exactly the pinned manager's render_prompt body, no imports."""
    method = source_method(parsed, "PromptManager", "render_prompt")
    body = list(method.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    if len(body) != 3:
        raise SourceGateError("MANAGER_METHOD_STRUCTURE_DRIFT")
    assignment, missing, tail = body
    if not (isinstance(assignment, ast.Assign)
            and isinstance(missing, ast.If)
            and isinstance(tail, ast.Return)
            and len(missing.body) == 1
            and isinstance(missing.body[0], ast.Raise)
            and isinstance(tail.value, ast.Await)):
        raise SourceGateError("MANAGER_METHOD_PATH_DRIFT")
    if not (isinstance(assignment.value, ast.Call)
            and isinstance(assignment.value.func, ast.Attribute)
            and assignment.value.func.attr == "get_prompt"
            and isinstance(missing.test, ast.UnaryOp)
            and isinstance(missing.test.op, ast.Not)):
        raise SourceGateError("MANAGER_GET_PROMPT_GUARD_DRIFT")
    return _compile_bounded_method(method, body, "render_prompt")


def extract_vetted_prompt_guard(
    parsed: ast.Module, *, fixed: bool,
) -> Any:
    """Run just the real upstream argument guard, NOT Prompt.render execution."""
    method = source_method(parsed, "Prompt", "render")
    guard = next((s for s in method.body if isinstance(s, ast.If)), None)
    if guard is None or not isinstance(guard.test, ast.Attribute):
        raise SourceGateError("REQUIRED_ARGUMENT_GUARD_MISSING")
    if guard.test.attr != "arguments" or len(guard.body) != 4:
        raise SourceGateError("REQUIRED_ARGUMENT_GUARD_DRIFT")
    if (not isinstance(guard.body[-1], ast.If)
            or len(guard.body[-1].body) != 1
            or not isinstance(guard.body[-1].body[0], ast.Raise)):
        raise SourceGateError("REQUIRED_ARGUMENT_RAISE_DRIFT")
    body = [copy.deepcopy(guard), ast.Return(value=ast.Constant(value="ARGUMENT_GUARD_OK"))]
    return _compile_bounded_method(method, body, "render")


def _compile_bounded_method(
    source: ast.AsyncFunctionDef, body: list[ast.stmt], name: str,
) -> Any:
    """No upstream module imports; imports cannot be reached in the selected AST."""
    fn = copy.deepcopy(source)
    fn.name = name
    fn.decorator_list = []
    fn.returns = None
    fn.type_params = []
    fn.body = body
    for arg in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs):
        arg.annotation = None
    if fn.args.vararg:
        fn.args.vararg.annotation = None
    if fn.args.kwarg:
        fn.args.kwarg.annotation = None
    # Reject executable statements outside the exact reviewed, pinned paths.
    if any(isinstance(item, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal))
           for item in ast.walk(fn)):
        raise SourceGateError("UNSAFE_METHOD_IMPORT_OR_GLOBAL")
    module = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
    env = {
        "__builtins__": {"ValueError": ValueError, "set": set},
        "MCPError": MinimalMCPError,
        "INVALID_PARAMS": INVALID_PARAMS,
    }
    exec(compile(module, filename="<UCIE pinned approved upstream methods>",
                 mode="exec"), env)
    return env[name]


def _outcome(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, MinimalMCPError):
        return {"kind": "MCPError", "code": exc.code}
    if type(exc) is ValueError:
        return {"kind": "ValueError", "code": None}
    if type(exc) is RuntimeError:
        return {"kind": "RuntimeError", "code": None}
    raise SourceGateError("UNEXPECTED_EXCEPTION_TYPE") from exc


async def check_variant(manager: Any, prompt_guard: Any) -> dict[str, Any]:
    class FakePrompt:
        def __init__(self):
            self.arguments = [SimpleNamespace(name="name", required=True)]

        async def render(self, arguments: dict[str, Any], context: Any):
            return await prompt_guard(self, arguments, context)

    async def exploder(arguments: Any, context: Any) -> None:
        raise RuntimeError("FIRST_PARTY_CONTROL_ONLY")

    outcomes: dict[str, Any] = {}
    # Invoke the original pinned PromptManager.render_prompt body with an
    # UCIE-owned fake prompt registry; no external prompt code can execute.
    for case, name, arguments, resolved in (
        ("unknown", "unknown", {}, None),
        ("missing", "greet", {}, FakePrompt()),
        ("valid_guard", "greet", {"name": "Ada"}, FakePrompt()),
        ("function_exception_control", "boom", {}, SimpleNamespace(render=exploder)),
    ):
        stub = SimpleNamespace(get_prompt=lambda requested, p=resolved: p)
        try:
            result = await manager(stub, name, arguments, None)
            outcomes[case] = {"kind": "RESULT", "value": result}
        except (MinimalMCPError, ValueError, RuntimeError) as exc:
            outcomes[case] = _outcome(exc)
    return outcomes


def compare_sources(items: dict[str, bytes]) -> dict[str, Any]:
    if type(items) is not dict or set(items) != set(FILE_BLOBS):
        raise SourceGateError("REQUIRED_FOUR_EXACT_SNAPSHOTS")
    parsed = {
        name: check_source_payload(name, items[name]) for name in FILE_BLOBS
    }
    outcomes = {}
    for stage in ("before", "after"):
        manager = extract_vetted_manager_function(
            parsed[stage + "_manager.py"], fixed=(stage == "after"),
        )
        guard = extract_vetted_prompt_guard(
            parsed[stage + "_base.py"], fixed=(stage == "after"),
        )
        outcomes[stage] = asyncio.run(check_variant(manager, guard))
    prior, after = outcomes["before"], outcomes["after"]
    for case in ("unknown", "missing"):
        if prior[case] != {"kind": "ValueError", "code": None}:
            raise SourceGateError("PRE_FIX_EXPECTED_VALUEERROR")
        if after[case] != {"kind": "MCPError", "code": INVALID_PARAMS}:
            raise SourceGateError("FIX_EXPECTED_INVALID_PARAMS")
    for stage in ("before", "after"):
        if outcomes[stage]["valid_guard"] != {
            "kind": "RESULT", "value": "ARGUMENT_GUARD_OK"
        }:
            raise SourceGateError("VALID_GUARD_FAILED")
        if outcomes[stage]["function_exception_control"] != {
            "kind": "RuntimeError", "code": None
        }:
            raise SourceGateError("FUNCTION_ERROR_CONTROL_CHANGED")
    return {
        "schema": SCHEMA,
        "status": "PINNED_UPSTREAM_METHOD_PATHS_OBSERVED",
        "before_sdk_tag_commit": BASE_COMMIT,
        "after_upstream_merge_commit": FIXED_COMMIT,
        "exact_upstream_git_blobs": dict(FILE_BLOBS),
        "method_paths_executed": 8,
        "outcomes": outcomes,
        "sdk_imported": False,
        "sdk_transports_tested": False,
        "entire_prompt_renderer_tested": False,
        "independent_sdk_integration_verified": False,
        "first_fixed_release": "NOT_VERIFIED",
        "rights_and_release_approved": False,
        "network_requests_by_method_probe": 0,
        "operating_data_writes": 0,
    }


def load_source_dir(directory: Path) -> dict[str, bytes]:
    if not directory.is_dir() or directory.is_symlink():
        raise SourceGateError("SOURCE_DIR_INVALID")
    result = {}
    for name in FILE_BLOBS:
        path = directory / name
        if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_BYTES:
            raise SourceGateError("SOURCE_FILE_MISSING_OR_UNSAFE")
        result[name] = path.read_bytes()
    return result


def main(argv: list[str] | None = None) -> int:
    # This probe is forbidden from silently running on the Windows owner host.
    args = argv if argv is not None else sys.argv[1:]
    if (len(args) != 1 or os.name != "posix" or
            not sys.flags.isolated or not sys.flags.no_site or
            os.environ.get("UCIE_DISPOSABLE_PINNED_QA") != "1"):
        raise SystemExit("DISPOSABLE_ISOLATED_LINUX_RUNNER_REQUIRED")
    report = compare_sources(load_source_dir(Path(args[0])))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
