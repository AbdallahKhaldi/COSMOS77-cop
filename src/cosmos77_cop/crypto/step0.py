"""The sealed Step-0 system declaration (rules 24 + 53): hardware, model, commit, game count.

The book requires the CPU frequency; the sealed schema is not an interop constraint, so the
extra key is safe — and rule 24 gates the computational-fairness bonus on a complete record.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
from typing import Any

import psutil


def _measured_spec() -> dict[str, Any]:
    freq = psutil.cpu_freq()
    memory = psutil.virtual_memory()
    return {
        "os": platform.system(),
        "cpu_type": platform.machine(),
        "cpu_cores": psutil.cpu_count(logical=False) or psutil.cpu_count() or 0,
        "cpu_freq_ghz": round((freq.max or freq.current) / 1000, 2) if freq else 0.0,
        "ram_gb": round(memory.total / 2**30, 1),
        "gpu_type": "none",
        "vram_gb": 0.0,
    }


def hardware_spec() -> dict[str, Any]:
    """Real host hardware via ``platform`` + ``psutil`` (mocked in tests).

    The machine actually playing must be the one declared (rule 24). Inside a hosted
    container ``psutil`` sees the host kernel, so ``HUB_HARDWARE_DESC`` lets the operator
    state the provisioned truth: a JSON object overlays the measured fields, any other
    non-empty text is recorded as a ``description`` field. Unset = measured behavior.
    """
    spec = _measured_spec()
    override = os.environ.get("HUB_HARDWARE_DESC", "").strip()
    if not override:
        return spec
    try:
        parsed = json.loads(override)
    except ValueError:
        parsed = None
    if isinstance(parsed, dict):
        return {**spec, **parsed}
    return {**spec, "description": override}


def current_commit(repo_root: str = ".") -> str:
    """The bare 40-hex commit being played (``git rev-parse HEAD``), per rule 53."""
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def is_dirty(repo_root: str = ".") -> bool:
    """True when the working tree differs from the declared commit (refused for counted runs)."""
    out = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True, check=True
    )
    return bool(out.stdout.strip())


def build_step0(
    *,
    sub_game_number: int,
    group_name: str,
    model: str,
    code_version: str,
    num_games_declared: int | None,
    spec: dict[str, Any],
) -> dict[str, Any]:
    """The step-0 payload sealed like any other record and revealed at audit."""
    return {
        "step": 0,
        "type": "system_spec",
        "sub_game_number": sub_game_number,
        "group_name": group_name,
        "model": model,
        "code_version": code_version,
        "num_games_declared": num_games_declared,
        "spec": spec,
    }
