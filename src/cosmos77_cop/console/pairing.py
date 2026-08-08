"""Everything an opponent needs, derived once and formatted to paste — pure, no I/O.

Pairing is the most error-prone step of the whole league: the ``game_uid`` must be derived from
the flat signed terms (not the whole config), the ``game_id`` sorts the pair, the window map has
to say who dials whom, and the turn order has to be stated because no protocol lock covers it.
Getting any of those wrong is invisible until two reports are diffed, after the games are over.
So the console derives all of it and writes the message for you.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..protocol.canonical import canonical_hash
from ..protocol.ids import game_id, game_uid
from ..protocol.locks import OUR_LOCKS
from ..protocol.terms import terms_from_config

OUR_GID = "cosmos77"
TURN_ORDER = "thief moves first"
TIE_RULE = "series_add (+2 each, added to totals, on a tied series)"


@dataclass(frozen=True)
class PairingPacket:
    """The derived facts plus the ready-to-send first-contact message."""

    opponent: str
    game_id: str
    game_uid: str
    config_sha256: str
    windows: list[dict[str, str]]
    message: str

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly form for the console page."""
        return {
            "opponent": self.opponent,
            "game_id": self.game_id,
            "game_uid": self.game_uid,
            "config_sha256": self.config_sha256,
            "windows": self.windows,
            "message": self.message,
        }


def window_map(
    opponent: str, our_cop: str, our_thief: str, their_cop: str, their_thief: str
) -> list[dict[str, str]]:
    """Who plays which role, and which URL each side dials, for all six windows."""
    first, _second = sorted([OUR_GID, opponent])
    rows = []
    for window in range(1, 7):
        we_are_cop = (first == OUR_GID) == (window % 2 == 1)
        rows.append(
            {
                "window": f"g{window}",
                "us": "cop" if we_are_cop else "thief",
                "them": "thief" if we_are_cop else "cop",
                "we_dial": their_thief if we_are_cop else their_cop,
                "they_dial": our_cop if we_are_cop else our_thief,
            }
        )
    return rows


def build_packet(
    raw_config: dict[str, Any],
    *,
    opponent: str,
    our_cop: str,
    our_thief: str,
    their_cop: str = "(theirs)",
    their_thief: str = "(theirs)",
) -> PairingPacket:
    """Derive every shared identifier and render the Stage-1 message."""
    terms = terms_from_config(raw_config)
    gid = game_id(OUR_GID, opponent)
    uid = game_uid(terms, OUR_GID, opponent)
    rows = window_map(opponent, our_cop, our_thief, their_cop, their_thief)
    table = "\n".join(
        f"  {r['window']}: we play {r['us']:<5} · we dial {r['we_dial']}"
        f" · you dial {r['they_dial']}"
        for r in rows
    )
    message = f"""cosmos77 ↔ {opponent} — pairing proposal (kit-compatible)

IDENTITY
  group_id: cosmos77 · members: Tasneem Natour, Abdallah Khaldi
  repos:  cop   https://github.com/AbdallahKhaldi/COSMOS77-cop
          thief https://github.com/AbdallahKhaldi/COSMOS77-thief
  MCP:    cop   {our_cop}
          thief {our_thief}
  wire shape: reference-v3 ({OUR_LOCKS['wire_shape']})
  TURN ORDER: {TURN_ORDER} — stating it explicitly, no lock covers it.

CONSTITUTION (config/game.json attached — the file IS the agreement)
  config sha256:      {canonical_hash(raw_config)}
  scent model:        subtractive_chebyshev_v1 ({OUR_LOCKS['scent_model']})
  info mode:          belief ({OUR_LOCKS['info_mode']})
  tie rule:           {TIE_RULE}
  token budget:       200,000 read as PER SERIES (flagging the 6x ambiguity now)
  roles:              alphabetically-first group is cop on windows 1, 3, 5

DERIVED — please derive these independently and confirm before any window
  game_id:  {gid}
  game_uid: {uid}
  (If your uid differs, it was almost certainly derived from your whole config rather
   than the flat 14 signed terms — that is the classic silent mismatch.)

WINDOW MAP
{table}

MAIL & FAILURE POSTURE
  Friendlies report to our own inboxes only; a counted series sends one report per team to
  the league address. If a counted series suffers a technical death we finish all six
  sub-games regardless; discarding an attempt happens only by mutual written agreement.

PROPOSED FIRST FRIENDLY: [date] [HH:MM] [timezone]
  T-protocol: both launch at T, probe at T+30s, any problem -> kill everything, name a new T.
"""
    return PairingPacket(opponent, gid, uid, canonical_hash(raw_config), rows, message)
