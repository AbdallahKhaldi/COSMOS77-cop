"""The httpx client the MCP transport dials with — narrowed to obey our CONNECT budget.

``connect_timeout_s`` is a negotiated-adjacent private budget (``reconcile_budgets`` enforces
``connect <= turn``), and that invariant only protects a turn if the connect phase actually obeys
its number: a peer whose tunnel is cold must fail fast enough to leave the turn deadline room to
retry, instead of consuming it inside a TCP handshake.

This wrapper narrows exactly ONE dimension of the timeout and is otherwise transparent — the MCP
layer calls it with keywords of its own (``follow_redirects`` today, more tomorrow), and a factory
that rejects one of them fails every dial with "Client failed to connect", i.e. a handshake
failure in every real game rather than a test-visible error.
"""

from __future__ import annotations

from collections.abc import Callable

import httpx
from mcp.shared._httpx_utils import MCP_DEFAULT_SSE_READ_TIMEOUT, MCP_DEFAULT_TIMEOUT


def base_timeout(timeout: httpx.Timeout | float | None) -> httpx.Timeout:
    """Whatever the MCP layer asked for, defaulted exactly as ``create_mcp_http_client`` does."""
    if isinstance(timeout, httpx.Timeout):
        return timeout
    if timeout is None:
        return httpx.Timeout(MCP_DEFAULT_TIMEOUT, read=MCP_DEFAULT_SSE_READ_TIMEOUT)
    return httpx.Timeout(timeout)


def http_client_factory(connect_timeout_s: float) -> Callable[..., httpx.AsyncClient]:
    """An MCP http-client factory whose CONNECT phase obeys the private budget."""

    def build(
        headers: dict[str, str] | None = None,
        timeout: httpx.Timeout | float | None = None,
        auth: httpx.Auth | None = None,
        **kwargs: object,
    ) -> httpx.AsyncClient:
        base = base_timeout(timeout)
        kwargs.setdefault("follow_redirects", True)
        if headers is not None:
            kwargs["headers"] = headers
        if auth is not None:
            kwargs["auth"] = auth
        return httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=connect_timeout_s, read=base.read, write=base.write, pool=base.pool
            ),
            **kwargs,
        )

    return build
