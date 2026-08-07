"""The dialing MCP client: one held session, re-established once per call on failure (SPEC §8).

Both sides dial each other. The async fastmcp client lives on a dedicated event-loop thread;
every call carries a hard deadline — expiry raises instead of hanging (rule 6).
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
from collections.abc import Callable
from typing import Any

from fastmcp import Client


class PeerCallError(RuntimeError):
    """A tool call that failed or blew its deadline (controlled, never a hang)."""


class PeerClient:
    """Synchronous facade over one held async MCP session."""

    def __init__(
        self,
        url: str,
        *,
        transport_factory: Callable[[], Client] | None = None,
    ) -> None:
        """Dial *url*; tests may inject an in-memory fastmcp transport instead."""
        self._factory = transport_factory or (lambda: Client(url))
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client: Client | None = None

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            thread = threading.Thread(target=self._loop.run_forever, daemon=True)
            thread.start()
        return self._loop

    async def _acquire(self) -> Client:
        if self._client is None:
            client = self._factory()
            await client.__aenter__()
            self._client = client
        return self._client

    async def _teardown(self) -> None:
        if self._client is not None:
            client, self._client = self._client, None
            with contextlib.suppress(Exception):
                await client.__aexit__(None, None, None)

    async def _call_once(self, tool: str, args: dict[str, Any]) -> object:
        client = await self._acquire()
        return await client.call_tool(tool, args)

    async def _call_with_reopen(self, tool: str, args: dict[str, Any]) -> object:
        try:
            return await self._call_once(tool, args)
        except Exception:
            await self._teardown()
            return await self._call_once(tool, args)

    def call(self, tool: str, args: dict[str, Any], *, deadline_s: float) -> object:
        """Call *tool* with *args*; raise :class:`PeerCallError` on failure or deadline expiry."""
        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(self._call_with_reopen(tool, args), loop)
        try:
            return future.result(timeout=deadline_s)
        except TimeoutError as exc:
            future.cancel()
            raise PeerCallError(f"{tool}: deadline of {deadline_s}s expired") from exc
        except Exception as exc:
            raise PeerCallError(f"{tool}: {exc}") from exc

    def close(self) -> None:
        """Tear the session and stop the loop thread (idempotent)."""
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._teardown(), self._loop).result(timeout=5)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._loop = None
