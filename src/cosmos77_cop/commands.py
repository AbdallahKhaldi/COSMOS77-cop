"""Command facade — the single import surface for the CLI and for tests.

The implementations live beside this module (``commands_play``, ``commands_ops``,
``commands_report``); this file keeps one import path stable so the CLI never has to know which
file a command moved to.
"""

from __future__ import annotations

from .commands_ops import compare_cmd, doctor_cmd, kill_cmd, replay_cmd
from .commands_play import serve_cmd
from .commands_report import report_cmd
from .commands_selfplay import selfplay_cmd
from .repoinfo import OUR_REPO, SIBLING_REPO, SIBLING_TOOL

__all__ = [
    "OUR_REPO",
    "SIBLING_REPO",
    "SIBLING_TOOL",
    "compare_cmd",
    "doctor_cmd",
    "kill_cmd",
    "replay_cmd",
    "report_cmd",
    "selfplay_cmd",
    "serve_cmd",
]
