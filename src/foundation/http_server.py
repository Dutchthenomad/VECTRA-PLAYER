"""HTTP server for Foundation monitoring UI and Service Manager API."""

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from aiohttp import web

from foundation.config import FoundationConfig

if TYPE_CHECKING:
    from browser.executor import BrowserExecutor
    from foundation.service_manager import ServiceManager

logger = logging.getLogger(__name__)


class FoundationHTTPServer:
    """
    HTTP server for Foundation Control Panel and Service Manager API.

    Serves:
    - GET /health - Health check endpoint
    - GET / - VECTRA Control Panel dashboard
    - GET /monitor/ - Foundation System Monitor (detailed event view)
    - GET /static/* - Static assets (JS, CSS)
    - GET /api/services - List all registered services
    - POST /api/services/<name>/start - Start a service
    - POST /api/services/<name>/stop - Stop a service
    - GET /api/services/<name>/status - Get service status
    - GET /artifacts/<name>/* - Serve HTML artifacts
    """

    def __init__(self, config: FoundationConfig | None = None):
        self.config = config or FoundationConfig()
        self._start_time = time.time()

        # Static files directory
        self.static_dir = Path(__file__).parent / "static"

        # Artifacts directory
        self.artifacts_dir = Path(__file__).parent.parent / "artifacts" / "tools"

        # Shared resources directory
        self.shared_dir = Path(__file__).parent.parent / "artifacts" / "shared"

        # Service manager (injected later)
        self.service_manager: ServiceManager | None = None

        # Browser executor for trade API (injected later)
        self.browser_executor: BrowserExecutor | None = None

        # Create aiohttp app
        self.app = web.Application()
        self._setup_routes()

        logger.info(f"FoundationHTTPServer initialized (port={self.config.http_port})")

    def set_service_manager(self, manager: "ServiceManager") -> None:
        """Inject service manager for API endpoints."""
        self.service_manager = manager

    def set_browser_executor(self, executor: "BrowserExecutor") -> None:
        """Inject browser executor for trade API endpoints."""
        self.browser_executor = executor
        logger.info("BrowserExecutor injected into HTTP server")

    def _setup_routes(self) -> None:
        """Configure HTTP routes."""
        # Health and dashboards
        self.app.router.add_get("/health", self._handle_health)
        self.app.router.add_get("/", self._handle_dashboard)
        self.app.router.add_get("/monitor/", self._handle_monitor)

        # Service Manager API
        self.app.router.add_get("/api/services", self._handle_list_services)
        self.app.router.add_post("/api/services/{name}/start", self._handle_start_service)
        self.app.router.add_post("/api/services/{name}/stop", self._handle_stop_service)
        self.app.router.add_get("/api/services/{name}/status", self._handle_service_status)

        # Trade Execution API
        self.app.router.add_post("/api/trade/buy", self._handle_trade_buy)
        self.app.router.add_post("/api/trade/sell", self._handle_trade_sell)
        self.app.router.add_post("/api/trade/sidebet", self._handle_trade_sidebet)
        self.app.router.add_post("/api/trade/increment", self._handle_trade_increment)
        self.app.router.add_post("/api/trade/percentage", self._handle_trade_percentage)
        self.app.router.add_post("/api/trade/clear", self._handle_trade_clear)
        self.app.router.add_post("/api/trade/half", self._handle_trade_half)
        self.app.router.add_post("/api/trade/double", self._handle_trade_double)
        self.app.router.add_post("/api/trade/max", self._handle_trade_max)

        # Artifacts serving
        self.app.router.add_get("/artifacts/{name}/", self._handle_artifact)
        self.app.router.add_get("/artifacts/{name}/{file}", self._handle_artifact_file)

        # Shared resources (CSS, JS)
        if self.shared_dir.exists():
            self.app.router.add_static("/shared", self.shared_dir)

        # Static files for Control Panel
        if self.static_dir.exists():
            self.app.router.add_static("/static", self.static_dir)

    async def _handle_health(self, request: web.Request) -> web.Response:
        """
        Health check endpoint.

        Returns JSON with service status and uptime.
        """
        uptime = time.time() - self._start_time

        return web.json_response(
            {
                "status": "healthy",
                "service": "foundation",
                "version": "1.0.0",
                "uptime_seconds": round(uptime, 2),
                "config": {
                    "ws_port": self.config.port,
                    "http_port": self.config.http_port,
                },
            }
        )

    async def _handle_dashboard(self, request: web.Request) -> web.Response:
        """
        Serve the Control Panel dashboard.

        Returns HTML page that connects to WebSocket feed.
        """
        html_path = self.static_dir / "index.html"

        if html_path.exists():
            return web.FileResponse(html_path)
        else:
            # Return minimal placeholder if no static files yet
            return web.Response(
                text="<html><body><h1>VECTRA Control Panel</h1><p>Static files not found. Run from project root.</p></body></html>",
                content_type="text/html",
            )

    async def _handle_monitor(self, request: web.Request) -> web.Response:
        """Serve the Foundation System Monitor dashboard."""
        html_path = self.static_dir / "monitor.html"

        if html_path.exists():
            return web.FileResponse(html_path)
        else:
            return web.Response(
                text="<html><body><h1>Foundation System Monitor</h1><p>monitor.html not found.</p></body></html>",
                content_type="text/html",
            )

    # =========================================================================
    # Service Manager API
    # =========================================================================

    async def _handle_list_services(self, request: web.Request) -> web.Response:
        """GET /api/services - List all registered services."""
        if not self.service_manager:
            return web.json_response(
                {"error": "Service manager not initialized"},
                status=503,
            )

        services = self.service_manager.list_services()
        return web.json_response({"services": services})

    async def _handle_start_service(self, request: web.Request) -> web.Response:
        """POST /api/services/{name}/start - Start a service."""
        if not self.service_manager:
            return web.json_response(
                {"error": "Service manager not initialized"},
                status=503,
            )

        name = request.match_info["name"]
        result = await self.service_manager.start_service(name)

        status_code = 200 if result.get("success") else 400
        return web.json_response(result, status=status_code)

    async def _handle_stop_service(self, request: web.Request) -> web.Response:
        """POST /api/services/{name}/stop - Stop a service."""
        if not self.service_manager:
            return web.json_response(
                {"error": "Service manager not initialized"},
                status=503,
            )

        name = request.match_info["name"]
        result = await self.service_manager.stop_service(name)

        status_code = 200 if result.get("success") else 400
        return web.json_response(result, status=status_code)

    async def _handle_service_status(self, request: web.Request) -> web.Response:
        """GET /api/services/{name}/status - Get detailed service status."""
        if not self.service_manager:
            return web.json_response(
                {"error": "Service manager not initialized"},
                status=503,
            )

        name = request.match_info["name"]
        service = self.service_manager.get_service(name)

        if not service:
            return web.json_response(
                {"error": f"Service not found: {name}"},
                status=404,
            )

        return web.json_response(service.to_dict())

    # =========================================================================
    # Trade Execution API
    # =========================================================================

    def _check_browser_executor(self) -> web.Response | None:
        """Check if browser executor is available."""
        if not self.browser_executor:
            return web.json_response(
                {"success": False, "error": "Browser executor not initialized"},
                status=503,
            )
        if not self.browser_executor.is_ready():
            return web.json_response(
                {"success": False, "error": "Browser not connected"},
                status=503,
            )
        return None

    async def _handle_trade_buy(self, request: web.Request) -> web.Response:
        """POST /api/trade/buy - Click BUY button in browser."""
        error_response = self._check_browser_executor()
        if error_response:
            return error_response

        try:
            success = await self.browser_executor.click_buy()
            return web.json_response({"success": success, "action": "buy"})
        except Exception as e:
            logger.error(f"Trade buy error: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _handle_trade_sell(self, request: web.Request) -> web.Response:
        """POST /api/trade/sell - Click SELL button in browser."""
        error_response = self._check_browser_executor()
        if error_response:
            return error_response

        try:
            # Check for percentage in request body
            percentage = None
            if request.content_type == "application/json":
                data = await request.json()
                percentage = data.get("percentage")

            success = await self.browser_executor.click_sell(percentage=percentage)
            return web.json_response(
                {"success": success, "action": "sell", "percentage": percentage}
            )
        except Exception as e:
            logger.error(f"Trade sell error: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _handle_trade_sidebet(self, request: web.Request) -> web.Response:
        """POST /api/trade/sidebet - Click SIDEBET button in browser."""
        error_response = self._check_browser_executor()
        if error_response:
            return error_response

        try:
            success = await self.browser_executor.click_sidebet()
            return web.json_response({"success": success, "action": "sidebet"})
        except Exception as e:
            logger.error(f"Trade sidebet error: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _handle_trade_increment(self, request: web.Request) -> web.Response:
        """POST /api/trade/increment - Click increment button (+0.001, +0.01, etc.)."""
        error_response = self._check_browser_executor()
        if error_response:
            return error_response

        try:
            data = await request.json()
            amount = data.get("amount")

            if amount is None:
                return web.json_response(
                    {"success": False, "error": "Missing 'amount' parameter"},
                    status=400,
                )

            # Map amount to button type
            button_map = {
                0.001: "+0.001",
                0.01: "+0.01",
                0.1: "+0.1",
                1.0: "+1",
            }

            button_type = button_map.get(float(amount))
            if not button_type:
                return web.json_response(
                    {"success": False, "error": f"Invalid amount: {amount}"},
                    status=400,
                )

            success = await self.browser_executor._click_increment_button_in_browser(button_type)
            return web.json_response({"success": success, "action": "increment", "amount": amount})
        except Exception as e:
            logger.error(f"Trade increment error: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _handle_trade_percentage(self, request: web.Request) -> web.Response:
        """POST /api/trade/percentage - Click percentage button (10%, 25%, etc.)."""
        error_response = self._check_browser_executor()
        if error_response:
            return error_response

        try:
            data = await request.json()
            pct = data.get("pct") or data.get("percentage")

            if pct is None:
                return web.json_response(
                    {"success": False, "error": "Missing 'pct' parameter"},
                    status=400,
                )

            # Convert percentage value (10 -> 0.1, 25 -> 0.25, etc.)
            pct_float = float(pct)
            if pct_float > 1:
                pct_float = pct_float / 100

            success = await self.browser_executor._set_sell_percentage_in_browser(pct_float)
            return web.json_response({"success": success, "action": "percentage", "pct": pct_float})
        except Exception as e:
            logger.error(f"Trade percentage error: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _handle_trade_clear(self, request: web.Request) -> web.Response:
        """POST /api/trade/clear - Click X (clear) button."""
        error_response = self._check_browser_executor()
        if error_response:
            return error_response

        try:
            success = await self.browser_executor._click_increment_button_in_browser("X")
            return web.json_response({"success": success, "action": "clear"})
        except Exception as e:
            logger.error(f"Trade clear error: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _handle_trade_half(self, request: web.Request) -> web.Response:
        """POST /api/trade/half - Click 1/2 button."""
        error_response = self._check_browser_executor()
        if error_response:
            return error_response

        try:
            success = await self.browser_executor._click_increment_button_in_browser("1/2")
            return web.json_response({"success": success, "action": "half"})
        except Exception as e:
            logger.error(f"Trade half error: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _handle_trade_double(self, request: web.Request) -> web.Response:
        """POST /api/trade/double - Click X2 button."""
        error_response = self._check_browser_executor()
        if error_response:
            return error_response

        try:
            success = await self.browser_executor._click_increment_button_in_browser("X2")
            return web.json_response({"success": success, "action": "double"})
        except Exception as e:
            logger.error(f"Trade double error: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _handle_trade_max(self, request: web.Request) -> web.Response:
        """POST /api/trade/max - Click MAX button."""
        error_response = self._check_browser_executor()
        if error_response:
            return error_response

        try:
            success = await self.browser_executor._click_increment_button_in_browser("MAX")
            return web.json_response({"success": success, "action": "max"})
        except Exception as e:
            logger.error(f"Trade max error: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)

    # =========================================================================
    # Artifact Serving
    # =========================================================================

    async def _handle_artifact(self, request: web.Request) -> web.Response:
        """GET /artifacts/{name}/ - Serve artifact index.html."""
        name = request.match_info["name"]
        artifact_path = self.artifacts_dir / name / "index.html"

        if artifact_path.exists():
            return web.FileResponse(artifact_path)
        else:
            return web.Response(
                text=f"<html><body><h1>Artifact Not Found</h1><p>No artifact named '{name}'</p></body></html>",
                content_type="text/html",
                status=404,
            )

    async def _handle_artifact_file(self, request: web.Request) -> web.Response:
        """GET /artifacts/{name}/{file} - Serve artifact file."""
        name = request.match_info["name"]
        filename = request.match_info["file"]

        # Security: prevent path traversal
        if ".." in filename or filename.startswith("/"):
            return web.Response(text="Invalid path", status=400)

        file_path = self.artifacts_dir / name / filename

        if file_path.exists() and file_path.is_file():
            return web.FileResponse(file_path)
        else:
            return web.Response(text="File not found", status=404)

    # =========================================================================
    # Server Lifecycle
    # =========================================================================

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
