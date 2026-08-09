"""Reach + contract doctor stages (all network I/O injected, so tests never touch a socket).

Reach reuses ``net/probes`` classification verbatim (406 IS the ready state — the same
semantics ``scripts/warmup.py`` polls for). Contract opens an MCP session per URL, lists the
tools, and pins the reference names and the message/payload argument asymmetry.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..net.probes import READY
from .report import GREEN, RED, YELLOW, Stage, skipped, worst

Prober = Callable[[str], tuple[int | None, str]]
Lister = Callable[[str], list[tuple[str, list[str]]]]
Caller = Callable[[str, dict[str, Any]], object]

EXPECTED_TOOLS = {
    "negotiate": "message",
    "receive_turn": "message",
    "receive_control": "message",
    "submit_audit": "payload",
}

_REACH_FIXES: dict[object, tuple[str, str | None]] = {
    406: (GREEN, None),
    400: (YELLOW, "an HTTP server answered 400 (server-no-session) where the reference answers "
                  "406 — likely alive; the contract stage decides"),
    421: (RED, "your tunnel sends the wrong Host header — rewrite it at the tunnel "
               "(originRequest.httpHostHeader / --host-header=rewrite)"),
    502: (RED, "edge is up but no agent behind it — start your agent process behind the tunnel"),
    530: (RED, "hostname unrouted — your tunnel is down; restart it and re-send the URL"),
    200: (RED, "a webpage answered, not an MCP endpoint — check the /mcp path is included"),
    None: (RED, "unreachable — check DNS/https, and that the service is awake"),
}

_REDIRECT_FIX = ("serve the MCP endpoint directly at this URL — no redirects "
                 "(a redirected POST becomes a GET)")


def reach_stage(urls: dict[str, str], prober: Prober) -> Stage:
    """Stage 1: bare-GET classify every URL exactly like net/probes + scripts/warmup."""
    if not urls:
        return skipped("reach", "no opponent URL given")
    rows, statuses, fixes = [], [], []
    for label, url in urls.items():
        code, kind = prober(url)
        status, fix = _REACH_FIXES.get(code, (RED, None))
        if code is not None and 300 <= code < 400:
            status, fix = RED, _REDIRECT_FIX
        verdict = "ready" if kind == READY else kind
        rows.append({"role": label, "url": url, "http": code, "classification": verdict})
        statuses.append(status)
        if fix and status != GREEN:
            fixes.append(f"{label}: {fix}")
    lines = "; ".join(f"{r['role']} {r['url']} -> {r['http']} ({r['classification']})"
                      for r in rows)
    return Stage("reach", worst(statuses), lines,
                 fix_line="; ".join(fixes) if fixes else None, detail={"probes": rows})


def _tool_problems(label: str, tools: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    """(problems, fixes) for one endpoint's tool listing against the reference contract."""
    problems, fixes = [], []
    for tool, param in EXPECTED_TOOLS.items():
        if tool not in tools:
            problems.append(f"missing tool `{tool}`")
            fixes.append(f'{label}: add tool `{tool}({param}: dict)` returning {{"ok": true}}')
        elif param not in tools[tool]:
            got = ", ".join(tools[tool]) or "<none>"
            problems.append(f"`{tool}` takes ({got}) not `{param}`")
            fixes.append(f"{label}: rename `{tool}`'s parameter to `{param}` (the reference "
                         "asymmetry: submit_audit takes payload, the other three take message)")
    return problems, fixes


def contract_stage(urls: dict[str, str], lister: Lister) -> Stage:
    """Stage 2: open an MCP session per URL, list tools, pin names and parameter names."""
    if not urls:
        return skipped("contract", "no opponent URL given")
    rows, statuses, fixes = [], [], []
    for label, url in urls.items():
        try:
            tools = dict(lister(url))
        except Exception as exc:
            statuses.append(RED)
            rows.append({"role": label, "url": url, "error": str(exc)})
            fixes.append(f"{label}: could not open an MCP session — the endpoint must speak "
                         "MCP streamable-http at this exact URL")
            continue
        problems, tool_fixes = _tool_problems(label, tools)
        fixes.extend(tool_fixes)
        statuses.append(RED if problems else GREEN)
        rows.append({"role": label, "url": url, "tools": tools, "problems": problems,
                     "extra_tools": sorted(set(tools) - set(EXPECTED_TOOLS))})
    ok = all(s == GREEN for s in statuses)
    finding = ("all four reference tools present with correct parameter names" if ok
               else "; ".join([p for r in rows for p in r.get("problems", [])]
                              + [r["error"] for r in rows if "error" in r]))
    return Stage("contract", worst(statuses), finding,
                 fix_line="; ".join(fixes) if fixes else None, detail={"endpoints": rows})
