"""``doctor`` opponent probe command: run the staged compatibility report end-to-end.

All real I/O lives in the three seams (``prober``/``lister``/``caller``) so tests inject fakes;
the greeting is friendly and clearly labeled — truthful counted_games_played, no counted fields,
nothing written to disk. Exit 0 always: the report itself carries the verdicts.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any

from .arming import declared_count
from .doctor.forensics import forensics_stage
from .doctor.knownlocks import locks_stage
from .doctor.report import build_report, render
from .doctor.spar import handshake_stage
from .doctor.stages import Caller, Lister, Prober, contract_stage, reach_stage
from .doctor.uidtopo import topology_stage, uid_stage
from .net.client import PeerClient
from .net.probes import probe
from .orchestrator.brainbridge import ROLE
from .orchestrator.identity import GROUP_ID, GROUP_NAME, LLM_MODEL, MEMBER_IDS, TEAM_REPOS
from .orchestrator.peerconf import load_peer_config
from .protocol.ids import game_uid
from .protocol.locks import OUR_LOCKS
from .protocol.terms import terms_from_config, terms_signature


def build_probe_greeting(raw_cfg: dict[str, Any], their_gid: str | None) -> dict[str, Any]:
    """Our ONE friendly greeting: labeled as a probe, counts truthful, never counted."""
    terms = terms_from_config(raw_cfg)
    nonce = secrets.token_hex(16)
    greeting: dict[str, Any] = {
        "terms": terms,
        "nonce": nonce,
        "signature": terms_signature(terms, nonce),
        "group_id": GROUP_ID,
        "role": ROLE,
        "sub_game_number": 1,
        "identity": {
            "group_id": GROUP_ID, "group_name": GROUP_NAME, "llm_model": LLM_MODEL,
            "mcp_servers": {"self": "doctor://no-callback"}, "repos": dict(TEAM_REPOS),
            "members": list(MEMBER_IDS), "counted_games_played": declared_count(),
            "note": "FRIENDLY DIAGNOSTIC PROBE (cosmos-cop doctor) — uncounted, no game "
            "intended; a refusal with a SPAR code is a welcome answer",
        },
    }
    for family, digest in OUR_LOCKS.items():
        greeting[f"{family}_sha256"] = digest
    if their_gid:
        greeting["game_uid"] = game_uid(terms, GROUP_ID, their_gid)
    return greeting


def _list_tools(url: str, deadline_s: float) -> list[tuple[str, list[str]]]:
    """Real MCP tools/list through the held-session client machinery."""
    client = PeerClient(url)
    try:
        tools = client.session(lambda c: c.list_tools(), deadline_s=deadline_s)
        return [
            (t.name, sorted((t.inputSchema or {}).get("properties") or {}))
            for t in tools  # type: ignore[union-attr]
        ]
    finally:
        client.close()


def _call_negotiate(url: str, greeting: dict[str, Any], deadline_s: float) -> object:
    """Real ``negotiate`` call; the stage renders errors, so close() must always run."""
    client = PeerClient(url)
    try:
        return client.call("negotiate", {"message": greeting}, deadline_s=deadline_s)
    finally:
        client.close()


def _load_json(path: str | None) -> dict[str, Any] | None:
    """Parse a JSON object file; ``None`` path stays ``None``; junk raises for the usage guard."""
    if path is None:
        return None
    loaded = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} is not a JSON object")
    return loaded


def doctor_probe_cmd(
    *,
    url: str | None,
    cop_url: str | None,
    thief_url: str | None,
    their_config: str | None,
    their_gid: str | None,
    their_greeting: str | None,
    public_base: str,
    config_path: str | None = "config/game.json",
    prober: Prober | None = None,
    lister: Lister | None = None,
    caller: Caller | None = None,
) -> int:
    """Run every stage against the opponent and print ONE canonical JSON report."""
    try:
        raw_cfg = _load_json(config_path)
        observed = _load_json(their_greeting)
    except (OSError, ValueError) as exc:
        print(f"doctor: unreadable input file — {exc}")
        return 2
    if raw_cfg is None:
        print(f"doctor: no game config at {config_path} — run from the repo root")
        return 2
    budget = load_peer_config("config/peer.toml").turn_timeout_s
    urls = {"single": url} if url else {}
    if cop_url and thief_url:
        urls = {"cop_role": cop_url, "thief_role": thief_url}
    peer_key = "thief_role" if ROLE == "police" else "cop_role"
    dial = url or urls.get(peer_key)
    greeting = build_probe_greeting(raw_cfg, their_gid)
    negotiate = caller or (lambda u, g: _call_negotiate(u, g, budget))
    handshake = handshake_stage(dial, negotiate, greeting)
    if observed is None and isinstance((handshake.detail or {}).get("data"), dict):
        observed = (handshake.detail or {})["data"]
    sample = observed if observed and "signature" in observed else None
    stages = [
        reach_stage(urls, prober or probe),
        contract_stage(urls, lister or (lambda u: _list_tools(u, budget))),
        locks_stage(observed),
        handshake,
        uid_stage(their_config, their_gid, our_raw=raw_cfg, our_gid=GROUP_ID),
        forensics_stage(sample),
        topology_stage(single=bool(url) if urls else None, public_base=public_base),
    ]
    report = build_report(
        stages=stages,
        target={"mode": "single-endpoint-both-roles" if url else "per-role" if urls else "offline",
                "urls": urls, "their_gid": their_gid, "their_config": their_config},
        generated_by=f"cosmos-cop doctor (group {GROUP_ID}, role {ROLE})",
    )
    print(render(report))
    return 0
