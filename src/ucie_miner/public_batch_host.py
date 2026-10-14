"""Stage 9.8: explicit read-only UCIE host readiness preview.

A fixture may simulate Windows, but that NEVER proves the owner's Windows
checkout was inspected. This is a local preflight with NO_GO by definition,
not an install, scheduler action, migration, or live collection.
"""
from __future__ import annotations

from pathlib import Path

from .host_preflight import inspect_ucie_host


def inspect_public_batch_host(root: Path, *, is_windows: bool,
                              python_version: tuple) -> dict:
    path = Path(root)
    if (path.name.casefold() != "ucie" or path.is_symlink()
            or not path.is_dir()
            or (path / "runtime").is_symlink()
            or (path / ".venv").is_symlink()):
        raise ValueError("invalid or unsafe dedicated UCIE checkout")
    if type(is_windows) is not bool or not isinstance(python_version, tuple):
        raise ValueError("invalid host type")
    if (len(python_version) != 2
            or any(type(v) is not int for v in python_version)):
        raise ValueError("invalid Python version")
    python_bin = path / ".venv" / "Scripts" / "python.exe"
    if python_bin.is_symlink():
        raise ValueError("symlinked UCIE virtual environment executable")
    if (path / "runtime").is_dir():
        previous = inspect_ucie_host(
            path, is_windows=is_windows, python_version=python_version)
        miner_state = previous["miner"]["state"]
        knowledge_state = previous["knowledge"]["state"]
        integrity = {
            "miner": previous["miner"]["integrity"],
            "knowledge": previous["knowledge"]["integrity"],
        }
    else:
        miner_state = "ABSENT"
        knowledge_state = "ABSENT"
        integrity = {"miner": "NOT_INSPECTED", "knowledge": "NOT_INSPECTED"}
    env_ready = is_windows and python_version == (3, 15)
    records_read_only = (
        miner_state == "READ_ONLY_INSPECTED"
        and knowledge_state == "READ_ONLY_INSPECTED")
    # This is a technical preflight only. Even a green mock/preflight may
    # not assert authorized operator signoff or working scheduled cycle.
    return {
        "schema": "UCIE_PUBLIC_BATCH_HOST_PRECHECK_V1",
        "status": "READ_ONLY_PRECHECK_NO_GO",
        "windows_python_315_compatible": env_ready,
        "venv_python_executable_present": python_bin.is_file(),
        "miner_database_state": miner_state,
        "knowledge_database_state": knowledge_state,
        "database_integrity_observation": integrity,
        "readonly_existing_db_precheck_complete": records_read_only,
        "operating_windows_host_identity_attested": False,
        "actual_public_batch_run_observed": False,
        "task_scheduler_binding_verified": False,
        "external_public_api_authenticity_attested": False,
        "independent_regression_passed": False,
        "manual_operator_approval": False,
        "permanent_database_writes": 0,
        "scheduler_registered_or_changed": False,
        "rulepack_promoted": False,
        "production_approved": False,
    }
