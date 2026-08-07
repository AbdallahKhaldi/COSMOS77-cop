"""The interactive replay viewer (rule 20): step forward/back, per-step Verified OK / TAMPERED.

Tk is imported lazily so the verification core stays importable — and testable — with no display.
"""

from __future__ import annotations

from pathlib import Path

from .render import BAD_RED, OK_GREEN
from .verify import ReplayResult, verify_log


class ReplayViewer:
    """A window over one verified log."""

    def __init__(self, result: ReplayResult) -> None:
        """Open on the first record."""
        self.result = result
        self.index = 0

    def step(self, delta: int) -> int:
        """Move the cursor and return the new index (clamped)."""
        self.index = max(0, min(len(self.result.verdicts) - 1, self.index + delta))
        return self.index

    def current(self) -> object:
        """The verdict under the cursor."""
        return self.result.verdicts[self.index]

    def run(self) -> int:  # pragma: no cover - requires a display
        """Open the Tk window; returns 0 on a clean log, 1 when anything was tampered."""
        import tkinter as tk

        root = tk.Tk()
        root.title(f"cosmos77 replay — {Path(self.result.path).name}")
        banner = tk.Label(root, text="", font=("Helvetica", 20, "bold"), fg="white", pady=10)
        banner.pack(fill="x")
        body = tk.Label(root, text="", font=("Courier", 12), justify="left", padx=14, pady=10)
        body.pack(fill="both", expand=True)
        controls = tk.Frame(root)
        controls.pack(pady=8)

        def refresh() -> None:
            verdict = self.current()
            banner.configure(text=verdict.stamp, bg=OK_GREEN if verdict.ok else BAD_RED)
            body.configure(
                text=(
                    f"record {self.index + 1}/{len(self.result.verdicts)}  ({verdict.side})\n"
                    f"sealed step   {verdict.step}\n"
                    f"declared      {verdict.declared}\n"
                    f"recomputed    {verdict.recomputed}\n\n"
                    f"log verdict   {self.result.stamp}"
                )
            )

        def move(delta: int) -> None:
            self.step(delta)
            refresh()

        tk.Button(controls, text="< prev", command=lambda: move(-1)).pack(side="left", padx=6)
        tk.Button(controls, text="next >", command=lambda: move(1)).pack(side="left", padx=6)
        root.bind("<Left>", lambda _e: move(-1))
        root.bind("<Right>", lambda _e: move(1))
        refresh()
        root.mainloop()
        return 0 if self.result.clean else 1


def open_log(path: str | Path) -> ReplayViewer:
    """Verify *path* and build a viewer over it."""
    return ReplayViewer(verify_log(path))
