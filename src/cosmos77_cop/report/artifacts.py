"""Counted-format artifact writing: canonical bytes + newline, kit example shapes (§2.10).

What you publish is what you hashed — every artifact is written as the exact compact canonical
serialization plus one newline, never a pretty-print.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..protocol.canonical import canonical_bytes, canonical_hash
from ..protocol.ids import artifact_filenames

TIMEZONE = "Asia/Jerusalem"
SCHEMA_VERSION = "1.1"


def write_canonical(path: str | Path, obj: dict[str, Any]) -> Path:
    """Write *obj* as canonical bytes + newline; return the path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_bytes(obj) + b"\n")
    return target


def links_block(gid: str, github: dict[str, dict[str, str]]) -> dict[str, Any]:
    """The four artifact filenames + both teams' repo links (rule 49)."""
    names = artifact_filenames(gid)
    return {
        "declaration": names["declaration"],
        "config": names["config"],
        "log": names["log"],
        "result": names["result"],
        "github": github,
    }


def league_block(*, counted: bool, reason: str) -> dict[str, Any]:
    """The league arming block; friendlies carry it DISARMED (rules 37-38)."""
    return {
        "authority": "book App. E rule 52 - the one counted series of this pairing",
        "counted": counted,
        "reason": reason,
    }


def sign_group_block(block: dict[str, Any]) -> dict[str, Any]:
    """Sign-then-insert over a declaration group block: sha256 of the compact canonical form."""
    body = {k: v for k, v in block.items() if k != "signature"}
    signed = dict(body)
    signed["signature"] = f"sha256:{canonical_hash(body)}"
    return signed


class ArtifactWriter:
    """Writes one series' artifact set under one directory."""

    def __init__(
        self,
        out_dir: str | Path,
        *,
        gid: str,
        uid: str,
        github: dict[str, dict[str, str]],
        counted: bool,
        reason: str,
    ) -> None:
        """Bind the series identity every artifact carries."""
        self.out_dir = Path(out_dir)
        self.gid = gid
        self.uid = uid
        self.links = links_block(gid, github)
        self.league = league_block(counted=counted, reason=reason)

    def base_envelope(self, schema: str) -> dict[str, Any]:
        """The identity header every artifact of this series shares."""
        return {
            "_schema": schema,
            "schema_version": SCHEMA_VERSION,
            "game_id": self.gid,
            "game_uid": self.uid,
            "links": self.links,
            "league": self.league,
        }

    def write_config(self, window: int, raw_cfg: dict[str, Any]) -> Path:
        """The crypto-locked per-window constitution copy."""
        name = artifact_filenames(self.gid, window)["config"]
        return write_canonical(self.out_dir / name, raw_cfg)

    def write_log(
        self,
        window: int,
        *,
        summary: dict[str, Any],
        records: list[dict[str, Any]],
        opponent_records: list[dict[str, Any]],
    ) -> Path:
        """The per-sub-game sealed log (our reveals + theirs, post-audit)."""
        schema = "Per-sub-game log: every step sealed commit-reveal; join by game_uid."
        log = self.base_envelope(schema)
        log["sub_game_number"] = window
        log["summary"] = summary
        log["records"] = records
        log["opponent_records"] = opponent_records
        name = artifact_filenames(self.gid, window)["log"]
        return write_canonical(self.out_dir / name, log)

    def write_declaration(self, declaration: dict[str, Any]) -> Path:
        """The pre-game declaration (identity, hardware, commits, truthful counts)."""
        name = artifact_filenames(self.gid)["declaration"]
        return write_canonical(self.out_dir / name, declaration)

    def write_result(self, result: dict[str, Any]) -> Path:
        """The final series result — the exact bytes a counted run would email."""
        name = artifact_filenames(self.gid)["result"]
        return write_canonical(self.out_dir / name, result)
