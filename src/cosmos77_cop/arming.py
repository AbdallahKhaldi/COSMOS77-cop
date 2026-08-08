"""Run-side counted arming — our PRIVATE posture; the shared constitution never changes.

Opponents agree on ``config/game.json`` (its canonical hash is part of pairing), so counted-ness
never lives there: whether WE count a series is read from the private peer layer
(``config/peer.toml`` ``[league] counted``) AND the ``serve --counted`` flag, mirroring the
mail-side double switch in :mod:`.report.recipients`. Half-armed refuses at startup, and a
fully armed run refuses when it could not deliver its report — so the lecturer address stays
structurally unreachable from any single mistake, and no web surface can ever reach this path
(the console rejects ``--counted`` argv outright).
"""

from __future__ import annotations

from pathlib import Path

from .report.gmail import has_credentials
from .report.ledger import LEDGER_FILE, Ledger
from .report.recipients import ArmingError, Posture, assert_deliverable

__all__ = ["ArmingError", "declared_count", "serve_posture"]


def serve_posture(*, config_counted: bool, cli_counted: bool, root: str = ".") -> Posture:
    """Resolve the run posture, refusing half-armed or undeliverable counted runs."""
    posture = Posture(config_counted=config_counted, cli_counted=cli_counted)
    assert_deliverable(posture, has_credentials=has_credentials(root), settled=True)
    return posture


def declared_count(root: str = ".") -> int:
    """The rule-37 truthful ``counted_games_played``, live-read from the committed ledger."""
    return Ledger.load(Path(root) / LEDGER_FILE).counted_games_played
