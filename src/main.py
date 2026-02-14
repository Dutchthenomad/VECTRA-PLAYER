"""
Main Entry Point for Rugs Replay Viewer
Clean, modular implementation
Phase 8.5: Added --live flag for browser automation mode
"""

try:
    from importlib.metadata import version

    __version__ = version("vectra-player")
except Exception:
    __version__ = "0.0.0-dev"

import os
import platform
import signal
import sys
from pathlib import Path

# Add parent directory to Python path for browser_automation imports
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

import argparse
import logging
import tkinter as tk

from browser.bridge import get_browser_bridge
from config import config
from core.game_state import GameState
from services.async_loop_manager import AsyncLoopManager
from services.event_bus import Events, event_bus
from services.event_store.service import EventStoreService
from services.live_state_provider import LiveStateProvider
from services.logger import setup_logging
from ui.minimal_window import MinimalWindow


class Application:
    """
    Main application controller
    Coordinates all components and manages lifecycle
    Phase 8.5: Added live_mode parameter for browser automation
    """

    def __init__(self, live_mode: bool = False):
        """
        Initialize application

        Args:
            live_mode: If True, enable live browser automation mode (Phase 8.5)
        """
        self._initialized_components = []
        self.main_window: MinimalWindow | None = None
        self.root: tk.Tk | None = None
        self.state: GameState | None = None
        self.event_bus = event_bus
        self.async_manager: AsyncLoopManager | None = None
        self.browser_bridge = None
        self.live_state_provider: LiveStateProvider | None = None
        self.event_store: EventStoreService | None = None

        try:
            # Initialize logging first
            self.logger = setup_logging()
            self._initialized_components.append("logging")
            self.logger.info("=" * 60)
            self.logger.info("Rugs Replay Viewer - Starting Application")
            self.logger.info(f"Version: {__version__}")
            if live_mode:
                self.logger.info("MODE: LIVE BROWSER AUTOMATION (Phase 8.5)")
            else:
                self.logger.info("MODE: REPLAY")
            self.logger.info("=" * 60)

            # Live mode flag for WebSocket feed vs replay
            self.live_mode = live_mode

            # Configure config runtime behavior at startup (avoid import-time side effects)
            config.set_logger(self.logger)
            config.ensure_directories()

            # Validate configuration at startup
            try:
                config.validate()
                self.logger.info("Configuration validated successfully")
            except Exception as e:
                self.logger.critical(f"Configuration validation failed: {e}")
                self._show_error_and_exit(
                    "Invalid configuration detected:\n\n"
                    f"{e}\n\nPlease check your config.py settings."
                )

            # Initialize core components
            self.config = config
            # Pass event_bus to GameState for live mode sync (Phase 12D fix)
            self.state = GameState(config.FINANCIAL["initial_balance"], event_bus=event_bus)

            # Start event bus
            self.event_bus.start()
            self._initialized_components.append("event_bus")

            # Dedicated asyncio loop thread for any legacy async operations that must be
            # invoked from the Tk thread (prevents ad-hoc event loop creation).
            self.async_manager = AsyncLoopManager()
            self.async_manager.start()
            self._initialized_components.append("async_manager")

            # Setup event handlers
            self._setup_event_handlers()

            # Create UI window (MinimalWindow uses plain tkinter)
            self.root = tk.Tk()
            self.logger.info("Using MinimalWindow (plain tkinter)")

            # Configure root window
            self._configure_root()

            self.logger.info("Application initialized successfully")
        except Exception:
            self._emergency_cleanup()
            raise

    def _show_error_and_exit(self, message: str):
        """Show error dialog if possible, then exit"""
        try:
            import tkinter as tk
            import tkinter.messagebox as messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("REPLAYER Error", message)
            root.destroy()
        except Exception:
            print(f"FATAL ERROR: {message}", file=sys.stderr)
        finally:
            sys.exit(1)

    def _emergency_cleanup(self):
        """Clean up partially initialized components"""
        for component in reversed(self._initialized_components):
            try:
                if component == "event_bus":
                    self.event_bus.stop()
                elif component == "async_manager" and self.async_manager:
                    self.async_manager.stop()
                elif component == "logging":
                    logging.shutdown()
            except Exception:
                pass

    def _configure_root(self):
        """Configure the root tkinter window"""
        self.root.title("Rugs.fun Replay Viewer - Professional Edition")
        self.root.geometry(f"{config.UI['window_width']}x{config.UI['window_height']}")

        # Set minimum size
        min_width = config.UI.get("min_width", 800)
        min_height = config.UI.get("min_height", 600)
        self.root.minsize(min_width, min_height)

        # Configure grid weights for responsive design
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Set icon if available
        assets_dir = Path(__file__).parent / "assets"
        icon_path = assets_dir / ("icon.ico" if platform.system() == "Windows" else "icon.png")
        if not icon_path.exists():
            icon_path = assets_dir / "icon.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception as e:
                self.logger.warning(f"Could not set icon: {e}")

        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def _setup_event_handlers(self):
        """Setup global event handlers"""
        # Application lifecycle events
        self.event_bus.subscribe(Events.UI_ERROR, self._handle_ui_error)

        # Game events
        self.event_bus.subscribe(Events.GAME_START, self._handle_game_start)
        self.event_bus.subscribe(Events.GAME_END, self._handle_game_end)
        self.event_bus.subscribe(Events.GAME_RUG, self._handle_rug_event)

        # Trading events
        self.event_bus.subscribe(Events.TRADE_EXECUTED, self._handle_trade_executed)
        self.event_bus.subscribe(Events.TRADE_FAILED, self._handle_trade_failed)

        self.logger.debug("Event handlers configured")

    def _handle_ui_error(self, event):
        """Handle UI errors"""
        data = event.get("data", {})
        self.logger.error(f"UI Error: {data}")

    def _handle_game_start(self, event):
        """Handle game start event"""
        data = event.get("data", {})
        self.logger.info(f"Game started: {data}")

    def _handle_game_end(self, event):
        """Handle game end event"""
        metrics = self.state.calculate_metrics()
        self.logger.info(f"Game ended. Metrics: {metrics}")

    def _handle_rug_event(self, event):
        """Handle rug event"""
        data = event.get("data", {})
        tick = data.get("tick", "unknown")
        self.logger.warning(f"RUG EVENT at tick {tick}")

    def _handle_trade_executed(self, event):
        """Handle successful trade"""
        data = event.get("data", {})
        self.logger.info(f"Trade executed: {data}")

    def _handle_trade_failed(self, event):
        """Handle failed trade"""
        data = event.get("data", {})
        self.logger.warning(f"Trade failed: {data}")

    def run(self):
        """Run the application"""
        try:
            # Create browser bridge for CDP connection (C1 fix)
            self.browser_bridge = get_browser_bridge()
            self.logger.info("Browser bridge initialized")

            # Create LiveStateProvider for server-authoritative state (H2 fix)
            self.live_state_provider = LiveStateProvider(self.event_bus)
            self._initialized_components.append("live_state_provider")
            self.logger.info("LiveStateProvider initialized")

            # Create and start EventStore for Parquet persistence (H3 fix)
            self.event_store = EventStoreService(self.event_bus)
            self.event_store.start()
            self._initialized_components.append("event_store")
            self.logger.info("EventStore started")

            # Create main window (MinimalWindow for RL training data collection)
            self.main_window = MinimalWindow(
                self.root,
                self.state,
                self.event_bus,
                self.config,
                browser_bridge=self.browser_bridge,
                live_state_provider=self.live_state_provider,
                event_store=self.event_store,
            )

            # Auto-load games if directory exists (skip in live mode)
            if not self.live_mode:
                self._auto_load_games()

            # Publish ready event
            self.event_bus.publish(Events.UI_READY)

            # Start main loop
            self.logger.info("Starting UI main loop")
            self.root.mainloop()

        except Exception as e:
            self.logger.critical(f"Critical error in main loop: {e}", exc_info=True)
            self.shutdown()

    def _auto_load_games(self):
        """Auto-load game files if available"""
        recordings_dir = self.config.FILES["recordings_dir"]

        if recordings_dir.exists():
            game_files = sorted(recordings_dir.glob("game_*.jsonl"))
            if game_files:
                self.logger.info(f"Found {len(game_files)} game files to auto-load")
                # Notify main window about available games
                self.event_bus.publish(Events.FILE_LOADED, {"files": game_files})

    def shutdown(self):
        """Clean shutdown of application"""
        self.logger.info("Shutting down application...")

        # AUDIT FIX: signal.SIGALRM is Unix-only, guard for Windows portability
        timeout_set = False
        if hasattr(signal, "SIGALRM"):

            def timeout_handler(signum, frame):
                self.logger.warning("Shutdown timeout - forcing exit")
                os._exit(1)

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)
            timeout_set = True

        try:
            # Save configuration
            config_file = self.config.FILES["config_dir"] / "settings.json"
            self.config.save_to_file(str(config_file))

            # Save state metrics
            metrics = self.state.calculate_metrics()
            self.logger.info(f"Final session metrics: {metrics}")

            # Stop EventStore first (flushes buffers)
            if self.event_store:
                self.event_store.stop()
                self.logger.info("EventStore stopped")

            # Stop LiveStateProvider
            if self.live_state_provider:
                self.live_state_provider.stop()
                self.logger.info("LiveStateProvider stopped")

            # Stop browser bridge
            if self.browser_bridge:
                self.browser_bridge.stop()
                self.logger.info("BrowserBridge stopped")

            # Stop event bus
            self.event_bus.stop()

            # Shut down UI if shutdown method exists
            if self.main_window and hasattr(self.main_window, "shutdown"):
                self.main_window.shutdown()
            elif self.main_window and hasattr(self.main_window, "_unsubscribe_from_events"):
                # MinimalWindow cleanup: unsubscribe from events
                self.main_window._unsubscribe_from_events()

            # Stop dedicated async manager after UI shutdown
            if self.async_manager:
                self.async_manager.stop()

            if self.root:
                self.root.quit()
                self.root.destroy()

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

        finally:
            if timeout_set:
                signal.alarm(0)
            self.logger.info("Application shutdown complete")
            sys.exit(0)


def main():
    """
    Main entry point
    Phase 8.5: Added --live command-line flag for browser automation
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Rugs.fun Replay Viewer - Professional Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                 # Run in replay mode (default)
  %(prog)s --live          # Run in live browser automation mode (Phase 8.5)

Phase 8.5: Live mode connects to Rugs.fun via Playwright automation.
        """,
    )

    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable live browser automation mode (requires CV-BOILER-PLATE-FORK)",
    )

    args = parser.parse_args()

    # Create and run application
    app = None
    try:
        app = Application(live_mode=args.live)
        app.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}", exc_info=True)
    finally:
        if app is not None:
            try:
                app.shutdown()
            except KeyboardInterrupt:
                print("\nForced exit during shutdown")
                os._exit(130)
            except Exception as e:
                logging.error(f"Error during shutdown: {e}")


if __name__ == "__main__":
    main()
