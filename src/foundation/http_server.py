"""HTTP server for Foundation monitoring UI."""

import logging
import time
from pathlib import Path

from aiohttp import web

from foundation.config import FoundationConfig

logger = logging.getLogger(__name__)


class FoundationHTTPServer:
    """
    HTTP server for Foundation monitoring dashboard and artifact tools.

    Serves:
    - GET /health - Health check endpoint
    - GET / - Monitoring dashboard
    - GET /static/* - Static assets (JS, CSS)
    - GET /artifacts/* - HTML artifact tools (prediction engine, seed bruteforce, etc.)
    """

    def __init__(self, config: FoundationConfig | None = None):
        self.config = config or FoundationConfig()
        self._start_time = time.time()

        # Static files directory
        self.static_dir = Path(__file__).parent / "static"

        # Artifacts directory (HTML tools: prediction engine, seed bruteforce, etc.)
        self.artifacts_dir = Path(__file__).parent.parent / "artifacts"

        # Create aiohttp app
        self.app = web.Application()
        self._setup_routes()

        logger.info(f"FoundationHTTPServer initialized (port={self.config.http_port})")

    def _setup_routes(self) -> None:
        """Configure HTTP routes."""
        self.app.router.add_get("/health", self._handle_health)
        self.app.router.add_get("/", self._handle_dashboard)

        # Static files (create dir if needed)
        if self.static_dir.exists():
            self.app.router.add_static("/static", self.static_dir)

        # Artifacts directory - HTML tools (prediction engine, seed bruteforce, etc.)
        # Served at /artifacts/* - e.g., /artifacts/orchestrator/index.html
        if self.artifacts_dir.exists():
            self.app.router.add_static("/artifacts", self.artifacts_dir)
            logger.info(f"Serving artifacts from {self.artifacts_dir}")

    async def _handle_health(self, request: web.Request) -> web.Response:
        """
        Health check endpoint.

        Returns JSON with service status and uptime.
        """
        uptime = time.time() - self._start_time

        return web.json_response(
            {
                "status": "healthy",
                "uptime_seconds": round(uptime, 2),
                "config": {
                    "ws_port": self.config.port,
                    "http_port": self.config.http_port,
                },
            }
        )

    async def _handle_dashboard(self, request: web.Request) -> web.Response:
        """
        Serve the monitoring dashboard.

        Returns HTML page that connects to WebSocket feed.
        """
        html_path = self.static_dir / "index.html"

        if html_path.exists():
            return web.FileResponse(html_path)
        else:
            # Return minimal placeholder if no static files yet
            return web.Response(
                text="<html><body><h1>Foundation Monitor</h1><p>Static files not found.</p></body></html>",
                content_type="text/html",
            )

    async def start(self, host: str = "localhost", port: int | None = None) -> None:
        """Start the HTTP server."""
        port = port or self.config.http_port
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        logger.info(f"HTTP server running at http://{host}:{port}")

    def get_app(self) -> web.Application:
        """Get the aiohttp application (for testing)."""
        return self.app
