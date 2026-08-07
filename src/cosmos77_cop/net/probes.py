"""Probe semantics: 406 is the READY state, not an error (SPEC §8; playbook §7.7)."""

from __future__ import annotations

import httpx

READY = "ready"

_CODES = {
    406: READY,
    502: "edge-up-nothing-behind",
    421: "tunnel-host-header (fix at the tunnel, not in code)",
    530: "hostname-unrouted",
    400: "missing-mcp-session (the server IS there)",
}


def classify_status(code: int) -> str:
    """What a bare browser-shaped GET status means for an MCP endpoint."""
    if code in _CODES:
        return _CODES[code]
    if 300 <= code < 400:
        return "forwarder-not-peer (a redirected POST becomes a GET)"
    return f"unexpected-{code}"


def probe(url: str, timeout_s: float = 5.0) -> tuple[int | None, str]:
    """GET *url* like a browser would; return (status, classification)."""
    try:
        response = httpx.get(url, timeout=timeout_s, follow_redirects=False)
    except httpx.HTTPError as exc:
        return None, f"unreachable: {exc.__class__.__name__}"
    return response.status_code, classify_status(response.status_code)
