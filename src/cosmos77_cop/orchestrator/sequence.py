"""Cross-process window choreography for parity-split series (the F2 lesson).

A real opponent plays the six sub-games strictly in order, one at a time.  Our cop and
thief processes each own only their parity windows and share ONE out dir — so the order
lives in the artifact set: window w's log seals exactly when w settles.  Playing window
w while an earlier window is still open burns the handshake budget against an opponent
whose series pointer is behind (f2-20260819-203304: five of six windows zeroed exactly
this way).  The barrier holds each window, and the series close, until the artifacts say
it is that window's turn; a stalled sibling degrades to the old behavior after the
timeout instead of hanging the series forever.
"""

from __future__ import annotations

import time
from pathlib import Path

POLL_S = 2.0


def todo_windows(spec: str | None, windows: int) -> list[int]:
    """The window list one serve plays: the ``--windows-spec`` split, or all of them."""
    return [int(w) for w in spec.split(",")] if spec else list(range(1, windows + 1))


def sealed_windows(out_dir: str | Path) -> set[int]:
    """Window numbers with a sealed log artifact in *out_dir* (either role wrote it)."""
    found: set[int] = set()
    for path in Path(out_dir).glob("log_*_g[0-9][0-9].json"):
        try:
            found.add(int(path.stem[-2:]))
        except ValueError:  # a foreign file shaped like ours is not a window seal
            continue
    return found


def await_predecessors(
    out_dir: str | Path, window: int, timeout_s: float, poll_s: float = POLL_S
) -> bool:
    """Block until every window below *window* is sealed; ``False`` on timeout."""
    needed = set(range(1, window))
    deadline = time.monotonic() + timeout_s
    while True:
        if needed <= sealed_windows(out_dir):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll_s)


def gate(out_dir: str | Path, window: int, *, armed: bool, timeout_s: float) -> None:
    """serve-loop hook: hold *window* until its predecessors seal.

    ``armed`` is the parity split (``--windows-spec``); selfplay and single-window runs
    pass straight through, so league-legacy behavior stays byte-identical there.
    """
    if not armed or window <= 1:
        return
    if not await_predecessors(out_dir, window, timeout_s):
        print(
            f"g{window:02d} barrier: earlier windows unsealed after {timeout_s:.0f}s "
            "— playing anyway",
            flush=True,
        )
