"""The live local-truth window (rules 8-9). Tk imported lazily; the model does the thinking.

What it draws is exactly :class:`~cosmos77_cop.gui.model.LiveView` — our cell, the barriers we
have seen declared, our posterior over the opponent, the scent field we perceive, and the hints
we received. There is no code path that can render the opponent's true position, because the
opponent's true position is never given to this module.
"""

from __future__ import annotations

from .model import LOCKED, LiveView
from .render import BARRIER, BELIEF, CELL, PAD, SCENT, SELF


class LiveWindow:
    """A Tk window fed one :class:`LiveView` at a time."""

    def __init__(self, title: str = "cosmos77 — local truth") -> None:
        """Create the window lazily; nothing opens until :meth:`open` is called."""
        self.title = title
        self._root = None
        self._canvas = None
        self._status = None
        self.last: LiveView | None = None

    def open(self, grid_size: int) -> None:  # pragma: no cover - requires a display
        """Open the window sized for a *grid_size* board."""
        import tkinter as tk

        span = grid_size * CELL
        self._root = tk.Tk()
        self._root.title(self.title)
        size = PAD * 2 + span
        self._canvas = tk.Canvas(self._root, width=size, height=size, bg="#fbfcfd")
        self._canvas.pack(side="left")
        self._status = tk.Label(
            self._root, text="", font=("Helvetica", 13), justify="left", anchor="nw", width=44
        )
        self._status.pack(side="right", fill="both", expand=True, padx=10, pady=10)

    def update(self, view: LiveView) -> None:  # pragma: no cover - requires a display
        """Redraw for *view* (no-op when the window was never opened)."""
        self.last = view
        if self._canvas is None or self._root is None or self._status is None:
            return
        canvas = self._canvas
        canvas.delete("all")
        peak = max(view.posterior.values()) if view.posterior else 0.0
        for cell, value in view.perceived_scent.items():
            self._fill(cell, SCENT, min(0.55, 0.12 + value * 0.5))
        for cell, prob in view.posterior.items():
            if peak > 0:
                self._fill(cell, BELIEF, min(0.85, 0.10 + 0.75 * (prob / peak)))
        for cell in view.barriers:
            self._fill(cell, BARRIER, 1.0)
        for index in range(view.grid_size + 1):
            pos = PAD + index * CELL
            span = view.grid_size * CELL
            canvas.create_line(PAD, pos, PAD + span, pos, fill="#c8ced6")
            canvas.create_line(pos, PAD, pos, PAD + span, fill="#c8ced6")
        x, y = PAD + view.self_pos[1] * CELL, PAD + view.self_pos[0] * CELL
        canvas.create_oval(
            x + 10, y + 10, x + CELL - 10, y + CELL - 10, fill=SELF, outline=""
        )
        canvas.create_text(x + CELL // 2, y + CELL // 2, text="US", fill="white")
        peak_cell = view.belief_peak
        self._status.configure(
            text="\n".join(
                [
                    view.banner,
                    "",
                    f"role         {view.role}",
                    f"sub-game     {view.sub_game}   step {view.step}",
                    f"our cell     {view.self_pos}",
                    f"barriers     {len(view.barriers)} seen, {view.barriers_left} left",
                    f"tracking     {view.confidence}",
                    f"belief peak  {peak_cell[0]} p={peak_cell[1]:.2f}" if peak_cell else "",
                    "",
                    "hints received:",
                    *[f"  · {h}" for h in view.hints[-5:]],
                    "",
                    view.caption,
                ]
            ),
            fg="#7a8290" if view.banner == LOCKED else "#101418",
        )
        self._root.update_idletasks()
        self._root.update()

    def _fill(self, cell: tuple[int, int], colour: str, opacity: float) -> None:  # pragma: no cover
        x, y = PAD + cell[1] * CELL, PAD + cell[0] * CELL
        shade = _blend(colour, opacity)
        self._canvas.create_rectangle(x, y, x + CELL, y + CELL, fill=shade, outline="")

    def close(self) -> None:  # pragma: no cover - requires a display
        """Close the window if it is open."""
        if self._root is not None:
            self._root.destroy()
            self._root = None


def _blend(colour: str, opacity: float, background: tuple[int, int, int] = (251, 252, 253)) -> str:
    """Tk canvases have no alpha, so blend against the page colour ourselves."""
    raw = colour.lstrip("#")
    rgb = tuple(int(raw[i : i + 2], 16) for i in (0, 2, 4))
    pairs = zip(rgb, background, strict=True)
    mixed = [round(c * opacity + b * (1 - opacity)) for c, b in pairs]
    return "#{:02x}{:02x}{:02x}".format(*mixed)
