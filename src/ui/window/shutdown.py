"""
Shutdown handler for MainWindow.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class ShutdownMixin:
    """Mixin providing shutdown functionality for MainWindow."""

    def shutdown(self: "MainWindow"):
        """Cleanup dispatcher resources during application shutdown."""
        # Stop browser if connected
        if self.browser_connected and self.browser_executor:
            loop = None
            try:
                logger.info("Shutting down browser...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.browser_executor.stop_browser())
                logger.info("Browser stopped")
            except Exception as e:
                logger.error(f"Error stopping browser during shutdown: {e}", exc_info=True)
            finally:
                if loop:
                    loop.close()
                    asyncio.set_event_loop(None)

        # Close demo recorder (flushes pending data)
        if self.demo_recorder:
            try:
                self.demo_recorder.close()
                logger.info("Demo recorder closed")
            except Exception as e:
                logger.error(f"Error closing demo recorder: {e}")

        # Stop raw capture if running
        if self.raw_capture_recorder and self.raw_capture_recorder.is_capturing:
            try:
                self.raw_capture_recorder.stop_capture()
                logger.info("Raw capture stopped during shutdown")
            except Exception as e:
                logger.error(f"Error stopping raw capture: {e}")

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
