"""
Shutdown handler for MainWindow.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class ShutdownMixin:
    """Mixin providing shutdown functionality for MainWindow."""

    def shutdown(self: "MainWindow"):
        """Cleanup dispatcher resources during application shutdown."""
        # Stop BrowserBridge (canonical CDP bridge) if running
        browser_bridge = getattr(self, "browser_bridge", None)
        if browser_bridge is not None:
            try:
                browser_bridge.disconnect()
                browser_bridge.stop()
            except Exception as e:
                logger.debug(f"Error stopping BrowserBridge during shutdown: {e}")

        # Stop browser if connected
        if self.browser_connected and self.browser_executor:
            try:
                logger.info("Shutting down browser...")
                async_manager = getattr(self, "async_manager", None)
                if async_manager is None:
                    raise RuntimeError("AsyncLoopManager not available for browser shutdown")

                future = async_manager.run_coroutine(self.browser_executor.stop_browser())
                future.result(timeout=15)
                logger.info("Browser stopped")
            except Exception as e:
                logger.error(f"Error stopping browser during shutdown: {e}", exc_info=True)

        # Stop EventStoreService (flushes remaining Parquet data)
        if hasattr(self, "event_store_service") and self.event_store_service:
            try:
                self.event_store_service.stop()
                logger.info("EventStoreService stopped")
            except Exception as e:
                logger.error(f"Error stopping EventStoreService: {e}")

        # Stop LiveStateProvider
        if hasattr(self, "live_state_provider") and self.live_state_provider:
            try:
                self.live_state_provider.stop()
                logger.info("LiveStateProvider stopped")
            except Exception as e:
                logger.error(f"Error stopping LiveStateProvider: {e}")

        # Clean up live feed connection
        self.live_feed_controller.cleanup()

        # Stop bot executor
        if self.bot_enabled:
            self.bot_executor.stop()
            self.bot_enabled = False

        # Stop UI dispatcher
        self.ui_dispatcher.stop()
