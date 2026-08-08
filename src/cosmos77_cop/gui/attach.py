"""Attaching the live view to a running sub-game — the ONLY seam between UI and game logic.

Everything here is observation: it reads the state the brain already has and pushes it at a
window and/or an SVG snapshot. Nothing it does can influence a move.
"""

from __future__ import annotations

from pathlib import Path

from .live import LiveWindow
from .model import HintTicker, build_view
from .render import write_live_svg


class ViewAttachment:
    """Installs an ``on_view`` sink on a brain bridge."""

    def __init__(
        self,
        *,
        window: LiveWindow | None = None,
        snapshot_dir: str | Path | None = None,
        snapshot_steps: tuple[int, ...] = (1, 8, 20),
        extra: object | None = None,
    ) -> None:
        """Any of the sinks may be absent (all absent makes attaching a no-op).

        *extra* is a duck-typed second window — anything with ``.update(view)``, e.g. the
        JSONL :class:`~cosmos77_cop.gui.stream.EventSink` the hub viewer tails.
        """
        self.window = window
        self.snapshot_dir = Path(snapshot_dir) if snapshot_dir else None
        self.snapshot_steps = snapshot_steps
        self.extra = extra
        self.ticker = HintTicker()
        self.written: list[Path] = []

    def attach(self, bridge: object, sub_game: int) -> None:
        """Give *bridge* an ``on_view`` callback for this sub-game."""
        if self.window is None and self.snapshot_dir is None and self.extra is None:
            return

        def on_view(state: object, kit: object, banner: str, step: int) -> None:
            self.render(bridge, state, kit, banner, step, sub_game)

        bridge.on_view = on_view

    def render(
        self, bridge: object, state: object, kit: object, banner: str, step: int, sub_game: int
    ) -> None:
        """Build the view and push it to whichever sinks exist."""
        hints = tuple(self.ticker.lines)
        view = build_view(state, kit, bridge, banner=banner, step=step, hints=hints)
        view = _with_sub_game(view, sub_game)
        if self.window is not None:
            self.window.update(view)
        if self.extra is not None:
            self.extra.update(view)
        if self.snapshot_dir is not None and step in self.snapshot_steps:
            name = f"live_g{sub_game:02d}_step{step:02d}_{view.confidence}.svg"
            self.written.append(write_live_svg(view, self.snapshot_dir / name))

    def note_hint(self, hint: str) -> None:
        """Record a received hint for the ticker."""
        self.ticker.push(hint)


def _with_sub_game(view: object, sub_game: int) -> object:
    from dataclasses import replace

    return replace(view, sub_game=sub_game)
