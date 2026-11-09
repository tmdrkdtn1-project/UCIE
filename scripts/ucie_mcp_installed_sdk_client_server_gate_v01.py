"""UCIE pinned installed MCP SDK Client <-> MCPServer integration gate.

Runs only in the disposable Linux CI environment with the approved SDK
repository checked out at exact immutable commits and uv-locked dependencies.
No external sockets or user/workspace files are used by the test scenarios.
This does not replace rights review, product approval, or first fixed release.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
import os
from pathlib import Path
import sys

SCHEMA = "UCIE_MCP_FULL_SDK_CLIENT_SERVER_GATE_V01"
COMMITS = {
    "before": "2118f14f8a19bc158d8a1cf90af58d85d187f849",
    "after": "754254c08fe1c3eda18b69da3d336106fe8d72d6",
}
PROTOCOL_MODES = ("legacy", "2026-07-28")
INVALID_PARAMS = -32602


def preflight(stage: str, expected_root: str) -> tuple[str, str]:
    if (os.name != "posix" or not sys.flags.isolated
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("UCIE_DISPOSABLE_SDK_GATE") != "1"):
        raise RuntimeError("DISPOSABLE_LINUX_CI_REQUIRED")
    if stage not in COMMITS:
        raise ValueError("UNRECOGNIZED_UPSTREAM_STAGE")
    root = Path(expected_root).resolve(strict=True)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("INVALID_ROOT")
    if os.environ.get("UCIE_EXACT_UPSTREAM_COMMIT") != COMMITS[stage]:
        raise ValueError("PINNED_COMMIT_ENV_MISMATCH")
    # Do not import an SDK from another checkout or host environment.
    mcp_path = root / ".venv"
    if not mcp_path.is_dir():
        raise ValueError("LOCKED_SDK_VENV_ABSENT")
    # venv/bin/python is routinely a symlink to the base interpreter.
    # The active sys.prefix and *invoked* executable path must belong to
    # this exact stage's virtual environment; resolving the executable
    # symlink would incorrectly point outside the venv on hosted runners.
    expected_env = mcp_path.resolve()
    if (Path(sys.prefix).resolve() != expected_env
            or sys.prefix == sys.base_prefix
            or not Path(sys.executable).absolute().is_relative_to(mcp_path)):
        raise ValueError("PYTHON_NOT_FROM_OWN_PINNED_ENV")
    return str(root), COMMITS[stage]


async def _case_error(client, prompt: str, arguments=None) -> int:
    from mcp import MCPError
    try:
        await asyncio.wait_for(client.get_prompt(prompt, arguments), timeout=12)
    except MCPError as exc:
        if type(exc.code) is not int:
            raise AssertionError("SDK_ERROR_CODE_NOT_INT") from exc
        return exc.code
    raise AssertionError("SDK_INPUT_OR_CONTROL_CASE_DID_NOT_ERROR")


async def _one_mode(mode: str, stage: str) -> dict[str, object]:
    from mcp import Client
    from mcp.server.mcpserver import MCPServer

    server = MCPServer("UCIE synthetic integration server")

    @server.prompt()
    async def greet(name: str) -> str:
        return f"Hello, {name}"

    @server.prompt()
    async def explode() -> str:
        raise RuntimeError("UCIE_INERT_TEST_EXCEPTION")

    async with Client(server, mode=mode) as client:
        result = await asyncio.wait_for(
            client.get_prompt("greet", {"name": "Ada"}), timeout=12
        )
        if (len(result.messages) != 1
                or getattr(result.messages[0].content, "text", None)
                != "Hello, Ada"):
            raise AssertionError("SDK_NORMAL_PROMPT_RESULT_MISMATCH")
        unknown = await _case_error(client, "unknown_prompt")
        missing = await _case_error(client, "greet")
        control = await _case_error(client, "explode")

    if stage == "before":
        if unknown == INVALID_PARAMS or missing == INVALID_PARAMS:
            raise AssertionError("PRE_FIX_INPUT_ERRORS_ALREADY_CORRECT")
    elif unknown != INVALID_PARAMS or missing != INVALID_PARAMS:
        raise AssertionError("PATCHED_INPUT_ERROR_NOT_INVALID_PARAMS")
    if control == INVALID_PARAMS:
        raise AssertionError("NON_INPUT_CONTROL_MISCLASSIFIED")
    return {
        "mode": mode,
        "valid": "RESULT_MATCH",
        "unknown_prompt_code": unknown,
        "missing_argument_code": missing,
        "function_error_control_code": control,
        "real_sdk_client_server_called": True,
    }


async def _run(stage: str) -> list[dict[str, object]]:
    output = []
    for mode in PROTOCOL_MODES:
        output.append(await asyncio.wait_for(_one_mode(mode, stage), timeout=40))
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE disposable real SDK integration QA")
    parser.add_argument("--stage", choices=tuple(COMMITS), required=True)
    parser.add_argument("--checkout", required=True)
    options = parser.parse_args(argv)
    checkout, commit = preflight(options.stage, options.checkout)

    import mcp
    from mcp import Client, MCPError
    from mcp.server.mcpserver import MCPServer
    if not (Client and MCPError and MCPServer):
        raise AssertionError("FULL_SDK_IMPORT_FAILED")
    if not Path(mcp.__file__).resolve().is_relative_to(Path(checkout) / ".venv"):
        raise AssertionError("SDK_IMPORT_OUTSIDE_EXACT_VENV")

    cases = asyncio.run(_run(options.stage))
    receipt = {
        "schema": SCHEMA,
        "status": "INSTALLED_SDK_CLIENT_SERVER_IN_MEMORY_OBSERVED",
        "stage": options.stage,
        "upstream_commit": commit,
        "installed_sdk_distribution": importlib.metadata.version("mcp"),
        "installed_types_distribution": importlib.metadata.version("mcp-types"),
        "protocol_modes": list(PROTOCOL_MODES),
        "cases": cases,
        "case_count": len(cases) * 4,
        "client_and_server_sdk_loaded": True,
        "real_in_memory_client_server_integration": True,
        "http_transport_tested": False,
        "stdio_transport_tested": False,
        "all_upstream_tests_run": False,
        "fixed_published_version_verified": False,
        "license_and_dependency_rights_approved": False,
        "customer_release_authorized": False,
        "persistent_writes_by_probe": 0,
    }
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
