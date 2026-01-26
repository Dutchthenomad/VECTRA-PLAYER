#!/usr/bin/env python3
"""
Foundation Launcher - Complete startup sequence

Launches:
1. Foundation service (WebSocket broadcaster + HTTP server)
2. Chrome with rugs_bot profile via CDP
3. Tab 1: rugs.fun (game)
4. Tab 2: http://localhost:9001/monitor/ (Foundation System Monitor - detailed events)
5. Tab 3: http://localhost:9001/ (VECTRA Control Panel - service management)
6. CDP interception feeds events to Foundation broadcaster
7. Waits for usernameStatus to confirm authentication

Usage:
    python -m foundation.launcher

    Or with custom ports:
    FOUNDATION_PORT=9000 FOUNDATION_HTTP_PORT=9001 python -m foundation.launcher
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src to path for imports
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from foundation.config import FoundationConfig
from foundation.http_server import FoundationHTTPServer
from foundation.service import FoundationService
from foundation.service_manager import ServiceManager

# Browser executor for trade API
try:
    from browser.executor import BrowserExecutor

    BROWSER_EXECUTOR_AVAILABLE = True
except ImportError:
    BrowserExecutor = None
    BROWSER_EXECUTOR_AVAILABLE = False

logger = logging.getLogger(__name__)


class FoundationLauncher:
    """
    Complete Foundation startup orchestrator.

    Sequence:
    1. Start Foundation service (broadcaster + HTTP)
    2. Launch Chrome with rugs_bot profile
    3. Navigate Tab 1 to rugs.fun
    4. Setup CDP interception
    5. Open Tab 2 with System Monitor (/monitor/)
    6. Open Tab 3 with Control Panel (/)
    7. Wait for usernameStatus authentication
    8. Ready for subscribers
    """

    MONITOR_URL = "http://localhost:{port}"
    AUTH_TIMEOUT = 10.0  # seconds to wait for usernameStatus

    def __init__(self, config: FoundationConfig = None):
        self.config = config or FoundationConfig()
        self.service = FoundationService(self.config)
        self.http_server = FoundationHTTPServer(self.config)

        # Initialize Service Manager for managing subscriber services
        project_root = Path(__file__).parent.parent.parent
        self.service_manager = ServiceManager(project_root)

        # Inject service manager into HTTP server for API endpoints
        self.http_server.set_service_manager(self.service_manager)

        # Browser executor for trade API (created after browser connects)
        self.browser_executor: BrowserExecutor | None = None

        self._running = False
        self._browser_manager = None
        self._interceptor = None
        self._cdp_session = None
        self._auth_event = asyncio.Event()
        self._broadcaster_task = None

        logger.info("FoundationLauncher initialized")

    async def start(self) -> bool:
        """
        Start complete Foundation system.

        Returns:
            True if authenticated successfully, False otherwise
        """
        self._running = True

        try:
            # Step 1: Start Foundation services
            logger.info("=" * 60)
            logger.info("FOUNDATION LAUNCHER - Starting")
            logger.info("=" * 60)

            await self._start_foundation_services()

            # Step 2: Launch Chrome with CDP
            await self._launch_browser()

            # Step 3: Setup CDP WebSocket interception BEFORE navigating
            # (to capture WebSocket creation events)
            await self._setup_interception()

            # Step 4: Navigate to rugs.fun (triggers WebSocket creation)
            await self._navigate_to_game()

            # Step 5: Open monitoring UI in Tab 2
            await self._open_monitoring_tab()

            # Step 5b: Create Trade API executor
            await self._create_trade_executor()

            # Step 6: Wait for authentication
            authenticated = await self._wait_for_authentication()

            if authenticated:
                logger.info("=" * 60)
                logger.info("FOUNDATION READY")
                logger.info(f"  User: {self.service.connection_state.username}")
                logger.info(f"  WebSocket: ws://localhost:{self.config.port}/feed")
                logger.info(f"  Monitor: http://localhost:{self.config.http_port}")
                logger.info("=" * 60)
            else:
                logger.warning("Authentication timeout - running in read-only mode")
                self.service.connection_state.set_unauthenticated()

            # Keep running until interrupted
            await self._run_forever()

            return authenticated

        except Exception as e:
            logger.error(f"Launcher error: {e}")
            raise
        finally:
            await self.stop()

    async def _start_foundation_services(self):
        """Start WebSocket broadcaster, HTTP server, and Service Manager."""
        logger.info("Starting Foundation services...")

        # Discover available services
        discovered = self.service_manager.discover_services()
        logger.info(f"  Discovered services: {discovered}")

        # Start Service Manager health check loop
        await self.service_manager.start()

        # Start broadcaster in background
        self._broadcaster_task = asyncio.create_task(self.service.broadcaster.start())
        await asyncio.sleep(0.1)  # Let it initialize

        # Start HTTP server
        await self.http_server.start(
            host=self.config.host,
            port=self.config.http_port,
        )

        logger.info(f"  WebSocket broadcaster: ws://{self.config.host}:{self.config.port}/feed")
        logger.info(f"  HTTP server: http://{self.config.host}:{self.config.http_port}")

    async def _launch_browser(self):
        """Launch Chrome with rugs_bot profile via CDP."""
        logger.info("Launching Chrome with rugs_bot profile...")

        try:
            from browser.manager import CDPBrowserManager

            self._browser_manager = CDPBrowserManager(
                cdp_port=self.config.cdp_port,
                profile_name=self.config.chrome_profile,
            )

            await self._browser_manager.connect()
            logger.info(f"  Chrome connected via CDP port {self.config.cdp_port}")

        except ImportError:
            logger.error("browser.manager not available - cannot launch Chrome")
            raise RuntimeError("Browser manager required for Foundation launcher")
        except Exception as e:
            logger.error(f"Failed to launch Chrome: {e}")
            raise

    async def _setup_interception(self):
        """Setup CDP WebSocket interception."""
        logger.info("Setting up CDP WebSocket interception...")

        try:
            from sources.cdp_websocket_interceptor import CDPWebSocketInterceptor

            self._interceptor = CDPWebSocketInterceptor()

            # Set event callback to feed Foundation
            self._interceptor.on_event = self._on_cdp_event

            # Create CDP session from Playwright page
            if self._browser_manager and self._browser_manager.page:
                # Get CDP session from the page's context
                cdp_session = await self._browser_manager.context.new_cdp_session(
                    self._browser_manager.page
                )
                self._cdp_session = cdp_session
                await self._interceptor.connect(cdp_session)
                logger.info("  CDP interception active")
            else:
                logger.warning("  No browser page available for interception")

        except ImportError:
            logger.error("CDPWebSocketInterceptor not available")
            raise RuntimeError("CDP interceptor required for Foundation launcher")
        except Exception as e:
            logger.error(f"Failed to setup interception: {e}")
            raise

    async def _navigate_to_game(self):
        """Navigate Tab 1 to rugs.fun."""
        logger.info("Navigating to rugs.fun...")

        if self._browser_manager and self._browser_manager.page:
            # Reload the page to trigger fresh WebSocket connection
            # (interception is already active, so we'll capture the auth event)
            await self._browser_manager.page.reload(wait_until="networkidle")
            logger.info("  Tab 1: https://rugs.fun (reloaded)")

            # Wait for page to settle and extensions to inject
            await asyncio.sleep(2)

            # Trigger wallet connection if needed
            await self._browser_manager.ensure_wallet_ready()
        else:
            logger.warning("  No browser page available")

    async def _open_monitoring_tab(self):
        """Open Tab 2 (System Monitor) and Tab 3 (Control Panel)."""
        logger.info("Opening monitoring UIs...")

        base_url = self.MONITOR_URL.format(port=self.config.http_port)
        monitor_url = f"{base_url}/monitor/"
        control_panel_url = base_url

        if self._browser_manager and self._browser_manager.context:
            # Tab 2: Foundation System Monitor (detailed event view)
            monitor_page = await self._browser_manager.context.new_page()
            await monitor_page.goto(monitor_url, wait_until="networkidle")
            logger.info(f"  Tab 2: {monitor_url} (System Monitor)")

            # Tab 3: VECTRA Control Panel (service management)
            control_page = await self._browser_manager.context.new_page()
            await control_page.goto(control_panel_url, wait_until="networkidle")
            logger.info(f"  Tab 3: {control_panel_url} (Control Panel)")
        else:
            logger.info(f"  System Monitor: {monitor_url}")
            logger.info(f"  Control Panel: {control_panel_url}")
            logger.info("  (Open manually in Chrome)")

    async def _wait_for_authentication(self) -> bool:
        """Wait for usernameStatus event."""
        logger.info(f"Waiting for authentication (timeout: {self.AUTH_TIMEOUT}s)...")

        self.service.set_connecting()

        try:
            await asyncio.wait_for(self._auth_event.wait(), timeout=self.AUTH_TIMEOUT)
            return True
        except TimeoutError:
            logger.warning("Authentication timeout")
            return False

    def _on_cdp_event(self, event: dict):
        """
        Handle event from CDP interception.

        Feeds events to Foundation service for normalization and broadcast.
        """
        event_name = event.get("event", "")

        # Feed to Foundation service
        self.service.on_raw_event(event)

        # Check for authentication event
        if event_name == "usernameStatus":
            data = event.get("data") or {}
            logger.debug(f"usernameStatus data: {data}")
            if data.get("hasUsername") and data.get("username"):
                logger.info(f"  Authenticated as: {data.get('username')}")
                self._auth_event.set()
            elif data.get("username"):
                # Alternative: just check for username presence
                logger.info(f"  Authenticated as: {data.get('username')}")
                self._auth_event.set()

    async def _create_trade_executor(self):
        """Create BrowserExecutor for Trade API and inject into HTTP server."""
        if not BROWSER_EXECUTOR_AVAILABLE:
            logger.warning("BrowserExecutor not available - Trade API disabled")
            return

        if not self._browser_manager:
            logger.warning("No browser manager available - Trade API disabled")
            return

        logger.info("Creating BrowserExecutor for Trade API...")

        try:
            self.browser_executor = BrowserExecutor(
                profile_name=self.config.chrome_profile,
                use_cdp=True,
            )

            # Share the existing browser manager (don't create a new connection)
            self.browser_executor.cdp_manager = self._browser_manager

            # Inject into HTTP server for trade endpoints
            self.http_server.set_browser_executor(self.browser_executor)
            logger.info("  Trade API ready (sharing browser connection)")

        except Exception as e:
            logger.error(f"Failed to create BrowserExecutor: {e}")
            self.browser_executor = None

    async def _run_forever(self):
        """Run until interrupted."""
        stop_event = asyncio.Event()

        def signal_handler():
            logger.info("Shutdown signal received")
            stop_event.set()

        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

        await stop_event.wait()

    async def stop(self):
        """Stop all components."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping Foundation launcher...")

        # Stop Service Manager (stops all managed services)
        await self.service_manager.stop()

        # Stop broadcaster
        await self.service.broadcaster.stop()

        # Clear browser executor reference (browser manager is shared, don't stop it)
        if self.browser_executor:
            self.browser_executor.cdp_manager = None
            self.browser_executor = None
            logger.info("BrowserExecutor cleared")

        # Disconnect browser
        if self._browser_manager:
            try:
                await self._browser_manager.disconnect()
            except Exception as e:
                logger.debug(f"Browser disconnect error: {e}")

        logger.info("Foundation launcher stopped")


def main():
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    launcher = FoundationLauncher()
    asyncio.run(launcher.start())


if __name__ == "__main__":
    main()
