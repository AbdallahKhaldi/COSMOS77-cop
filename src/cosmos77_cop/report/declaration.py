"""The pre-game declaration artifact: identity, hardware, commits, truthful counts."""

from __future__ import annotations

from typing import Any

from ..orchestrator.series import SeriesDriver
from .artifacts import sign_group_block


def _group_block(
    gid: str,
    identity: dict[str, Any],
    hardware: dict[str, Any],
    commit: str,
    counted_played: int | None,
) -> dict[str, Any]:
    return sign_group_block(
        {
            "group_id": gid,
            "group_name": identity.get("group_name", gid),
            "members": identity.get("members", []),
            "repos": identity.get("repos", {}),
            "mcp_servers": identity.get("mcp_servers", {}),
            "llm_model": identity.get("llm_model", "template"),
            "hardware_spec": hardware,
            "github_commit": commit,
            "counted_games_played": counted_played,
            "code_version": commit,
        }
    )



def _peer_hardware(driver: SeriesDriver) -> dict[str, Any]:
    for report in driver.reports:
        for record in report.opp_records:
            payload = record.get("payload", {})
            if payload.get("step") != 0:
                continue
            # both live dialects: MOAAMOHA writes hardware_spec, the reference spec
            spec = payload.get("hardware_spec") or payload.get("spec")
            if isinstance(spec, dict):
                return spec
    return {}


def _peer_commit(driver: SeriesDriver) -> str | None:
    for report in driver.reports:
        for record in report.opp_records:
            payload = record.get("payload", {})
            if payload.get("step") == 0:
                found = payload.get("github_commit") or payload.get("code_version")
                if found:
                    return str(found)
    return None
