"""
CDP Minimal Connection Pattern

Demonstrates the core Chrome DevTools Protocol connection pattern
used throughout VECTRA-PLAYER for browser automation.

Usage:
    from cdp_minimal import CDPConnection

    conn = CDPConnection(port=9222)
    result = conn.execute("Runtime.evaluate", expression="document.title")
"""

import asyncio
import json
from typing import Any

import websockets


class CDPConnection:
    """
    Minimal Chrome DevTools Protocol connection.

    Connects to Chrome via WebSocket and sends CDP commands.

    Example:
        conn = CDPConnection(port=9222)
        # Evaluate JavaScript
        result = conn.execute("Runtime.evaluate", expression="1 + 1")
        # Click element
        conn.execute("Runtime.evaluate", expression="document.querySelector('button').click()")
    """

    def __init__(self, host: str = "localhost", port: int = 9222):
        self.host = host
        self.port = port
        self._ws_url: str | None = None
        self._ws: Any = None
        self._msg_id = 0

    def _get_ws_url(self) -> str:
        """Get WebSocket URL from Chrome's debug endpoint."""
        import urllib.request

        url = f"http://{self.host}:{self.port}/json"
        with urllib.request.urlopen(url, timeout=5) as response:
            targets = json.loads(response.read())

        # Find page target
        for target in targets:
            if target.get("type") == "page":
                return target["webSocketDebuggerUrl"]

        raise RuntimeError("No page target found")

    async def _send_command(self, method: str, **params) -> dict:
        """Send CDP command and wait for response."""
        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method, "params": params}

        await self._ws.send(json.dumps(msg))

        # Wait for matching response
        while True:
            response = await self._ws.recv()
            data = json.loads(response)
            if data.get("id") == self._msg_id:
                return data

    async def _execute_async(self, method: str, **params) -> dict:
        """Execute command with connection management."""
        if self._ws_url is None:
            self._ws_url = self._get_ws_url()

        async with websockets.connect(self._ws_url) as ws:
            self._ws = ws
            return await self._send_command(method, **params)

    def execute(self, method: str, **params) -> dict:
        """
        Execute CDP command synchronously.

        Args:
            method: CDP method name (e.g., "Runtime.evaluate")
            **params: Method parameters

        Returns:
            CDP response dict

        Example:
            result = conn.execute("Runtime.evaluate", expression="document.title")
            title = result["result"]["result"]["value"]
        """
        return asyncio.get_event_loop().run_until_complete(self._execute_async(method, **params))


class CDPSession:
    """
    Session-based CDP connection (persistent WebSocket).

    Better for multiple commands to the same page.
    """

    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self._ws: Any = None
        self._msg_id = 0
        self._loop = asyncio.new_event_loop()

    async def _connect(self):
        self._ws = await websockets.connect(self.ws_url)

    async def _send_and_receive(self, method: str, **params) -> dict:
        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method, "params": params}
        await self._ws.send(json.dumps(msg))

        while True:
            response = await self._ws.recv()
            data = json.loads(response)
            if data.get("id") == self._msg_id:
                return data

    def connect(self):
        """Establish persistent connection."""
        self._loop.run_until_complete(self._connect())

    def execute(self, method: str, **params) -> dict:
        """Execute command on persistent connection."""
        return self._loop.run_until_complete(self._send_and_receive(method, **params))

    def close(self):
        """Close connection."""
        if self._ws:
            self._loop.run_until_complete(self._ws.close())


# Example usage
if __name__ == "__main__":
    # Simple connection
    conn = CDPConnection(port=9222)

    # Get page title
    result = conn.execute("Runtime.evaluate", expression="document.title")
    print(f"Page title: {result['result']['result']['value']}")

    # Navigate
    result = conn.execute("Page.navigate", url="https://rugs.fun")
    print(f"Navigation: {result}")
