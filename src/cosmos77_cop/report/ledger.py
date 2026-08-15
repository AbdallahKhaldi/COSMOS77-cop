"""The rule-52 counted-game ledger: one counted series per opponent, advanced only by settlement.

Committed to the repo (it is the evidence behind every ``counted_games_played`` we declare), and
advanced ONLY by a settled counted run. A friendly must never touch it — arming an uncounted game
is project-fatal under rules 37-38.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..engine.config import GAME_CONFIG, signed_value

LEDGER_FILE = "artifacts/league_ledger.json"


def ledger_file(root: str | Path = ".") -> Path:
    """Where the ledger LIVES for this process: env override first, repo file otherwise.

    On the hub, runtime advances must land on the data volume (they survive redeploys)
    and must NOT touch the repo working tree: a counted run arms behind a clean-tree
    gate (rule 53), and any in-repo mutation — even a symlink swap — reads as dirty
    and refuses the very game that produced it.  ``COSMOS_LEDGER_FILE`` points the
    whole module at the volume twin; unset (a laptop), the committed repo file is it.
    """
    import os

    override = os.environ.get("COSMOS_LEDGER_FILE")
    return Path(override) if override else Path(root) / LEDGER_FILE
LEAGUE = "network_and_league"


def league_limits(config_path: str | Path = GAME_CONFIG) -> tuple[int, int]:
    """``(min_games_to_pass, max_games_per_team)`` — read from the SIGNED constitution.

    App. F fixes both numbers and `game.json` carries them; restating them as module literals
    was a §0.14 violation waiting to drift away from the file the opponents agreed.
    """
    return (
        int(signed_value(LEAGUE, "min_games_to_pass", config_path)),
        int(signed_value(LEAGUE, "max_games_per_team", config_path)),
    )


class LedgerError(RuntimeError):
    """A ledger operation that the league rules forbid."""


@dataclass
class Ledger:
    """The counted games we have played, keyed by opponent group id."""

    path: Path
    entries: dict[str, dict[str, object]]
    limits: tuple[int, int] = field(default_factory=league_limits)

    @property
    def min_to_pass(self) -> int:
        """The rule-31 floor of counted games against different teams (signed)."""
        return self.limits[0]

    @property
    def max_games(self) -> int:
        """The rule-31 cap on counted games (signed)."""
        return self.limits[1]

    @classmethod
    def load(
        cls, path: str | Path = LEDGER_FILE, config_path: str | Path = GAME_CONFIG
    ) -> Ledger:
        """Load the ledger (an absent file is an empty ledger, not an error)."""
        target = Path(path)
        raw = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
        return cls(
            path=target,
            entries=dict(raw.get("counted_games") or {}),
            limits=league_limits(config_path),
        )

    @property
    def counted_games_played(self) -> int:
        """The rule-37 declaration, EXCLUSIVE of any game now being played."""
        return len(self.entries)

    def has_played(self, opponent: str) -> bool:
        """True when a counted series against *opponent* already settled (rule 52)."""
        return opponent in self.entries

    def first_meeting(self, opponent: str) -> bool:
        """Whether a counted series against *opponent* would be their first."""
        return not self.has_played(opponent)

    def record(
        self, *, opponent: str, game_id: str, game_uid: str, won: bool, settled_at: str
    ) -> None:
        """Advance the ledger by exactly one settled counted series."""
        if self.has_played(opponent):
            raise LedgerError(
                f"rule 52: a counted game against {opponent} is already recorded "
                f"({self.entries[opponent]['game_id']}); only one counts"
            )
        if self.counted_games_played >= self.max_games:
            raise LedgerError(
                f"rule 31: the league cap of {self.max_games} counted games is reached"
            )
        self.entries[opponent] = {
            "game_id": game_id,
            "game_uid": game_uid,
            "won": won,
            "settled_at": settled_at,
        }
        self.save()

    def save(self) -> Path:
        """Write the ledger back (committed evidence, so plain readable JSON)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = {
            "_schema": "rule-52 counted-game ledger: one counted series per opponent, advanced "
            "only by a settled counted run.",
            "counted_games": self.entries,
            "counted_games_played": self.counted_games_played,
            "min_to_pass": self.min_to_pass,
            "max_games": self.max_games,
        }
        self.path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return self.path

    @property
    def passes_minimum(self) -> bool:
        """Whether we have met the rule-31 floor of counted games against different teams."""
        return self.counted_games_played >= self.min_to_pass
