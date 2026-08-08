"""The local console: a stdlib HTTP server bound to loopback. No new dependencies.

It binds 127.0.0.1 only — this is our own ops panel, never a public surface — and it physically
cannot arm a counted run (see :mod:`.state`).
"""

from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from .page import page_html
from .pairing import build_packet
from .state import Runner, latest_result, readiness, repo_label


def _our_tool() -> str:
    """Our own CLI name, derived so the cop/thief token swap cannot invert it."""
    from ..repoinfo import OUR_REPO

    return "cosmos-" + OUR_REPO.rsplit("-", 1)[-1]


def build_command(repo: Path, kind: str, peer: str, opponent: str) -> tuple[str, list[str]]:
    """Translate a console button into a CLI invocation."""
    tool = _our_tool()
    if kind == "kill":
        return "kill ports", ["uv", "run", tool, "kill"]
    if kind == "selfplay" or not peer:
        return "selfplay x6", ["uv", "run", tool, "selfplay", "--windows", "6"]
    windows = "1" if kind == "f1" else "6"
    gid = opponent or "opponent"
    out = f"runs/{kind}-{gid}"
    return (
        f"{kind.upper()} vs {gid}",
        ["uv", "run", tool, "serve", "--port", "8801", "--peer-url", peer,
         "--gid-a", "cosmos77", "--gid-b", gid, "--windows", windows, "--out", out],
    )


class ConsoleHandler(BaseHTTPRequestHandler):
    """Serves the page and a tiny JSON API."""

    repo: Path
    runner: Runner

    def log_message(self, *args: object) -> None:  # noqa: D102 - silence per-request noise
        return

    def _send(self, code: int, body: bytes, kind: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: dict[str, Any], code: int = 200) -> None:
        self._send(code, json.dumps(payload).encode("utf-8"), "application/json")

    def do_GET(self) -> None:
        """Serve the page, the status snapshot, or the running job."""
        if self.path == "/":
            self._send(200, page_html().encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/api/status":
            self._json(
                {
                    "repo": repo_label(),
                    "readiness": readiness(self.repo),
                    "result": latest_result(self.repo),
                }
            )
        elif self.path == "/api/run":
            current = self.runner.current
            self._json(current.snapshot() if current else {})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        """Start a run, or build a pairing packet."""
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/run":
            label, command = build_command(
                self.repo, payload.get("kind", ""), payload.get("peer", ""),
                payload.get("opponent", ""),
            )
            try:
                self.runner.start(label, command)
            except (PermissionError, RuntimeError) as exc:
                self._json({"error": str(exc)}, 409)
                return
            self._json({"started": label})
        elif self.path == "/api/pair":
            self._json(self._pair(payload))
        else:
            self._json({"error": "not found"}, 404)

    def _pair(self, payload: dict[str, Any]) -> dict[str, Any]:
        opponent = (payload.get("opponent") or "").strip()
        if not opponent:
            return {"error": "enter the opponent's group id first"}
        raw = json.loads((self.repo / "config" / "game.json").read_text(encoding="utf-8"))
        ours = (payload.get("ours") or "https://cosmos77.onrender.com/mcp").strip()
        packet = build_packet(
            raw,
            opponent=opponent,
            our_cop=ours,
            our_thief=ours.replace("cosmos77.", "cosmos77-thief."),
            their_cop=(payload.get("their_cop") or "(their cop URL)").strip(),
            their_thief=(payload.get("their_thief") or "(their thief URL)").strip(),
        )
        return packet.as_dict()


def run_console(repo: str | Path = ".", port: int = 8000, open_browser: bool = True) -> int:
    """Serve the console on loopback until interrupted."""
    root = Path(repo).resolve()
    handler = type(
        "BoundConsoleHandler", (ConsoleHandler,), {"repo": root, "runner": Runner(root)}
    )
    server = HTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"console: {url}  (loopback only; Ctrl-C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nconsole: stopped")
    return 0
