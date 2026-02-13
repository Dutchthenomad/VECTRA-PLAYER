#!/usr/bin/env python3
"""
Foundation Launcher - Complete startup sequence

Launches:
1. Foundation service (WebSocket broadcaster + HTTP server)
2. Chrome with rugs_bot profile via CDP
3. Tab 1: rugs.fun (game)
4. Tab 2: http://localhost:9001 (monitoring UI)
5. CDP interception feeds events to Foundation broadcaster
6. Waits for usernameStatus to confirm authentication

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

from foundation.auth_waiter import AuthenticationWaiter
from foundation.config import FoundationConfig
from foundation.http_server import FoundationHTTPServer
from foundation.service import FoundationService

logger = logging.getLogger(__name__)


class FoundationLauncher:
    """
    Complete Foundation startup orchestrator.

    Sequence:
    1. Start Foundation service (broadcaster + HTTP)
    2. Launch Chrome with rugs_bot profile
    3. Navigate Tab 1 to rugs.fun
    4. Setup CDP interception
    5. Open Tab 2 with monitoring UI
    6. Wait for usernameStatus authentication
    7. Ready for subscribers
    """

    MONITOR_URL = "http://localhost:{port}"

    # Authentication configuration (exponential backoff)
    AUTH_MAX_WAIT = 60.0  # Maximum wait time (was 10.0)
    AUTH_INITIAL_INTERVAL = 0.5  # Start checking every 0.5s
    AUTH_MAX_INTERVAL = 5.0  # Cap at 5s between checks
    AUTH_BACKOFF_MULTIPLIER = 1.5  # Grow interval by 50% each time

    def __init__(self, config: FoundationConfig = None):
        self.config = config or FoundationConfig()
        self.service = FoundationService(self.config)
        self.http_server = FoundationHTTPServer(self.config)

        self._running = False
        self._browser_manager = None
        self._interceptor = None
        self._cdp_session = None
        self._broadcaster_task = None

        # Event-driven authentication with exponential backoff
        self._auth_waiter = AuthenticationWaiter(
            max_wait_seconds=self.AUTH_MAX_WAIT,
            initial_check_interval=self.AUTH_INITIAL_INTERVAL,
            max_check_interval=self.AUTH_MAX_INTERVAL,
            backoff_multiplier=self.AUTH_BACKOFF_MULTIPLIER,
        )

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
        """Start WebSocket broadcaster and HTTP server."""
        logger.info("Starting Foundation services...")

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
            # Use "domcontentloaded" instead of "networkidle" because rugs.fun
            # has constant WebSocket activity that prevents network idle
            await self._browser_manager.page.reload(wait_until="domcontentloaded")
            logger.info("  Tab 1: https://rugs.fun (reloaded)")

            # Wait for page to settle and extensions to inject
            await asyncio.sleep(2)

            # Trigger wallet connection if needed
            await self._browser_manager.ensure_wallet_ready()
        else:
            logger.warning("  No browser page available")

    async def _open_monitoring_tab(self):
        """Open Tab 2 with monitoring UI."""
        logger.info("Opening monitoring UI...")

        monitor_url = self.MONITOR_URL.format(port=self.config.http_port)

        if self._browser_manager and self._browser_manager.context:
            # Open new tab
            monitor_page = await self._browser_manager.context.new_page()
            await monitor_page.goto(monitor_url, wait_until="domcontentloaded")
            logger.info(f"  Tab 2: {monitor_url}")
        else:
            logger.info(f"  Monitor available at: {monitor_url}")
            logger.info("  (Open manually in Chrome Tab 2)")

    async def _wait_for_authentication(self) -> bool:
        """
        Wait for player authentication using event-driven detection.

        Uses exponential backoff checking and supports multiple event sources
        for extracting player identity (connection.authenticated, player.state,
        game.tick leaderboard, connection.status).

        Returns:
            True if fully authenticated, False if partial/timeout
        """
        self.service.set_connecting()

        try:
            auth_state = await self._auth_waiter.wait_for_authentication()

            if auth_state.is_fully_authenticated:
                # Update connection state with player identity
                self.service.connection_state.username = auth_state.username
                self.service.connection_state.player_id = auth_state.player_id
                self.service.connection_state.status = (
                    self.service.connection_state.status.__class__.AUTHENTICATED
                )

                # Broadcast authentication event to monitor UI
                # (usernameStatus may have been empty, so we emit manually)
                import time

                from foundation.normalizer import NormalizedEvent

                auth_event = NormalizedEvent(
                    type="connection.authenticated",
                    ts=int(time.time() * 1000),
                    game_id=auth_state.game_id,
                    seq=0,  # Sequence will be set by broadcaster
                    data={
                        "username": auth_state.username,
                        "player_id": auth_state.player_id,
                    },
                )
                self.service.broadcaster.broadcast(auth_event)
                logger.info(f"Broadcast authentication: {auth_state.username}")

                return True
            else:
                # Partial authentication (game data but no player identity)
                logger.warning("Running in read-only mode (no player identity)")
                return False

        except TimeoutError as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def _on_cdp_event(self, event: dict):
        """
        Handle event from CDP interception.

        Feeds events to:
        1. Foundation service for normalization and broadcast
        2. AuthenticationWaiter for player identity extraction
        """
        # Feed to Foundation service
        self.service.on_raw_event(event)

        # Convert raw CDP event to normalized format for auth waiter
        # The normalizer converts "gameStateUpdate" -> "game.tick", etc.
        event_name = event.get("event", "")
        data = event.get("data") or {}
        game_id = event.get("gameId") or data.get("gameId")

        # Map raw event names to normalized types for auth waiter
        type_map = {
            "gameStateUpdate": "game.tick",
            "playerUpdate": "player.state",
            "usernameStatus": "connection.authenticated",
            "playerLeaderboardPosition": "player.leaderboard",  # Contains YOUR identity
        }

        normalized_type = type_map.get(event_name, event_name)

        # Feed to auth waiter for player identity extraction
        normalized_event = {
            "type": normalized_type,
            "gameId": game_id,
            "data": data,
        }
        self._auth_waiter._update_state_from_event(normalized_event)

        # Legacy: Also handle usernameStatus for connection state
        if event_name == "usernameStatus":
            logger.debug(f"usernameStatus data: {data}")
            if data.get("username"):
                logger.info(f"  usernameStatus received: {data.get('username')}")

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

        # Stop broadcaster
        await self.service.broadcaster.stop()

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
