"""Readiness checks and run bookkeeping for the console — no HTTP, no HTML."""

from __future__ import annotations

import json
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..hints.gemini import load_env_key
from ..repoinfo import OUR_REPO, SIBLING_REPO
from ..report.gmail import has_credentials
from ..report.ledger import Ledger

COUNTED_REFUSAL = (
    "A counted run can never be armed from the console. Arming needs config counted=true AND "
    "--counted on a local terminal, deliberately — so no web request can ever reach the "
    "lecturer's address (rules 37-38)."
)


def readiness(repo: Path) -> list[dict[str, Any]]:
    """Everything the console can check locally, as ok/label/detail rows."""
    sibling = repo.parent / SIBLING_REPO
    token = (repo / "token.json").exists()
    ledger = Ledger.load(repo / "artifacts" / "league_ledger.json")
    rows = [
        ("sibling repo beside us", sibling.is_dir(), str(sibling.name)),
        ("constitution present", (repo / "config" / "game.json").exists(), "config/game.json"),
        ("Gmail client", has_credentials(repo), "credentials.json"),
        ("Gmail consent", token, "token.json — re-consent if a send fails"),
        ("Gemini key", bool(load_env_key(repo / ".env")), "optional; templates otherwise"),
        ("counted games played", True, f"{ledger.counted_games_played} of max 10 (2 to pass)"),
    ]
    return [{"label": label, "ok": bool(ok), "detail": detail} for label, ok, detail in rows]


@dataclass
class RunLog:
    """One background run: its command, its streamed output, and its exit code."""

    label: str
    command: list[str]
    lines: list[str] = field(default_factory=list)
    returncode: int | None = None
    running: bool = True

    def snapshot(self) -> dict[str, Any]:
        """JSON-friendly view for polling."""
        return {
            "label": self.label,
            "command": " ".join(self.command),
            "lines": self.lines[-200:],
            "returncode": self.returncode,
            "running": self.running,
        }


class Runner:
    """Runs one game at a time, streaming output for the page to poll."""

    def __init__(self, repo: Path) -> None:
        """Bind to the repo whose CLI we shell out to."""
        self.repo = repo
        self.current: RunLog | None = None

    @property
    def busy(self) -> bool:
        """True while a run is in flight (the console refuses to start a second)."""
        return self.current is not None and self.current.running

    def start(self, label: str, command: list[str]) -> RunLog:
        """Launch *command* in the repo, streaming into a fresh :class:`RunLog`."""
        if any(arg == "--counted" for arg in command):
            raise PermissionError(COUNTED_REFUSAL)
        if self.busy:
            raise RuntimeError("a run is already in progress")
        log = RunLog(label=label, command=command)
        self.current = log
        threading.Thread(target=self._pump, args=(log,), daemon=True).start()
        return log

    def _pump(self, log: RunLog) -> None:
        import os

        env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
        try:
            process = subprocess.Popen(
                log.command, cwd=self.repo, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
            for line in process.stdout or []:
                stripped = line.rstrip()
                if stripped and "authlib" not in stripped.lower():
                    log.lines.append(stripped)
            log.returncode = process.wait()
        except Exception as exc:  # a broken launch is information, not a crash
            log.lines.append(f"console: could not run — {type(exc).__name__}: {exc}")
            log.returncode = 1
        finally:
            log.running = False


def latest_result(repo: Path) -> dict[str, Any] | None:
    """The most recent result artifact under ``runs/``, if any."""
    candidates = sorted(repo.glob("runs/*/result_*.json"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        return None
    body = json.loads(candidates[-1].read_text(encoding="utf-8"))
    return {
        "file": str(candidates[-1].relative_to(repo)),
        "final_result": body.get("final_result", {}),
        "sub_games": [
            {k: row.get(k) for k in ("sub_game_number", "result", "score", "audit")}
            for row in body.get("sub_games", [])
        ],
    }


def repo_label() -> str:
    """Which half of the team this console belongs to."""
    return OUR_REPO
