"""
LiveFeedController - Manages WebSocket live feed connection and state

Extracted from MainWindow to follow Single Responsibility Principle.
Handles:
- WebSocket feed connection/disconnection
- Live mode state management
- Feed source switching
- UI updates for live feed status

Phase 10.6: Auto-starts recording when WebSocket connects,
auto-stops when disconnected.
"""

import logging
import threading
import tkinter as tk
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.controllers.recording_controller import RecordingController

logger = logging.getLogger(__name__)


class LiveFeedController:
    """
    Manages WebSocket live feed connection and state management.

    Extracted from MainWindow (Phase 3.4) to reduce God Object anti-pattern.
    """

    def __init__(
        self,
        root: tk.Tk,
        parent_window,  # Reference to MainWindow for state access
        replay_engine,
        event_bus,
        # UI variables
        live_feed_var: tk.BooleanVar,
        # Notifications
        toast,
        # Callbacks
        log_callback: Callable[[str], None],
    ):
        """
        Initialize LiveFeedController with dependencies.

        Args:
            root: Tkinter root window (for thread-safe marshaling)
            parent_window: MainWindow instance (for state access)
            replay_engine: ReplayEngine instance (to push ticks)
            event_bus: EventBus instance (for publishing events)
            live_feed_var: Menu checkbox variable for live feed
            toast: Toast notification widget
            log_callback: Logging function
        """
        self.root = root
        self.parent = parent_window
        self.replay_engine = replay_engine
        self.event_bus = event_bus

        # UI variables
        self.live_feed_var = live_feed_var

        # Notifications
        self.toast = toast

        # Callbacks
        self.log = log_callback
        # Coalescing tick delivery to protect Tk event loop under bursty traffic.
        self._signal_lock = threading.Lock()
        self._latest_signal = None
        self._signal_drain_scheduled = False

        # Phase 10.6: Recording controller for auto-start/stop
        self._recording_controller: RecordingController | None = None

        # Phase 10.7: Player identity tracking
        self._player_id: str | None = None
        self._username: str | None = None

        logger.info("LiveFeedController initialized")

    def set_recording_controller(self, controller: "RecordingController") -> None:
        """
        Set the recording controller for auto-start/stop recording.

        Phase 10.6: Must be called after RecordingController is created.

        Args:
            controller: RecordingController instance
        """
        self._recording_controller = controller
        logger.debug("Recording controller set for auto-start/stop")

    def _queue_live_signal(self, signal_snapshot) -> None:
        """Store the latest signal and schedule a single UI-thread drain."""
        with self._signal_lock:
            self._latest_signal = signal_snapshot
            if self._signal_drain_scheduled:
                return
            self._signal_drain_scheduled = True

        self.root.after(0, self._drain_live_signals)

    def _drain_live_signals(self) -> None:
        """UI-thread: process the most recent pending signals (coalesced)."""
        max_per_cycle = 3
        processed = 0

        while processed < max_per_cycle:
            with self._signal_lock:
                captured_signal = self._latest_signal
                self._latest_signal = None

            if captured_signal is None:
                break

            self._process_live_signal(captured_signal)
            processed += 1

        with self._signal_lock:
            if self._latest_signal is None:
                self._signal_drain_scheduled = False
                return

        # More signals arrived while we were processing: schedule another drain.
        self.root.after(0, self._drain_live_signals)

    def _process_live_signal(self, captured_signal) -> None:
        """Convert a live signal to a tick and push through ReplayEngine."""
        try:
            tick = self.parent.live_feed.signal_to_game_tick(captured_signal)
            # ReplayEngine owns GAME_START/GAME_TICK/GAME_END publishing for live ticks.
            self.replay_engine.push_tick(tick)
        except Exception as e:
            logger.error(f"Error processing live signal: {e}", exc_info=True)

    # ========================================================================
    # LIVE FEED CONNECTION
    # ========================================================================

    def enable_live_feed(self):
        """Enable WebSocket live feed (Phase 6)"""
        if self.parent.live_feed_connected:
            self.log("Live feed already connected")
            return

        try:
            self.log("Connecting to live feed...")
            # Show connecting toast for user feedback
            if self.toast:
                self.toast.show("Connecting to live feed...", "info")

            # Create WebSocketFeed
            from sources.websocket_feed import WebSocketFeed

            self.parent.live_feed = WebSocketFeed(log_level="WARN")

            # Register event handlers (THREAD-SAFE with root.after)
            # PRODUCTION FIX: All handlers capture values via default arguments
            # to prevent race conditions when signals arrive faster than processing
            @self.parent.live_feed.on("signal")
            def on_signal(signal):
                # CRITICAL FIX: Create immutable snapshot to prevent race conditions
                signal_snapshot = dict(signal) if hasattr(signal, "items") else signal
                self._queue_live_signal(signal_snapshot)

            @self.parent.live_feed.on("connected")
            def on_connected(info):
                # PRODUCTION FIX: Capture info snapshot
                info_snapshot = (
                    dict(info)
                    if hasattr(info, "items")
                    else {"socketId": getattr(info, "socketId", None)}
                )

                # Marshal to Tkinter main thread with captured value
                def handle_connected(captured_info=info_snapshot):
                    socket_id = captured_info.get("socketId")

                    # Skip first connection event (Socket ID not yet assigned)
                    # Socket.IO fires 'connect' twice during handshake - ignore the first one
                    if socket_id is None:
                        self.log("🔌 Connection negotiating...")
                        return

                    # Only process when Socket ID is available (actual connection established)
                    self.parent.live_feed_connected = True
                    # Sync menu checkbox state (connection succeeded)
                    self.live_feed_var.set(True)
                    self.log(f"✅ Live feed connected (Socket ID: {socket_id})")
                    if self.toast:
                        self.toast.show("Live feed connected", "success")
                    # Update status label if it exists
                    if hasattr(self.parent, "phase_label"):
                        self.parent.phase_label.config(text="PHASE: LIVE FEED", fg="#00ff88")

                    # Phase 10.6: Auto-start recording DISABLED
                    # Recording is now controlled via UI toggle, not auto-started
                    # If you want to re-enable, uncomment below:
                    # if self._recording_controller:
                    #     try:
                    #         self._recording_controller.start_session()
                    #         self.log("📹 Recording started automatically")
                    #     except Exception as rec_e:
                    #         logger.error(f"Failed to auto-start recording: {rec_e}")

                self.root.after(0, handle_connected)

            @self.parent.live_feed.on("disconnected")
            def on_disconnected(info):
                # PRODUCTION FIX: Capture info snapshot
                info_snapshot = dict(info) if hasattr(info, "items") else {}

                # Marshal to Tkinter main thread with captured value
                def handle_disconnected(captured_info=info_snapshot):
                    reason = captured_info.get("reason", "unknown")
                    self.parent.live_feed_connected = False
                    # Sync menu checkbox state (disconnected)
                    self.live_feed_var.set(False)
                    self.log(f"❌ Live feed disconnected: {reason}")
                    if self.toast:
                        self.toast.show("Live feed disconnected", "error")
                    if hasattr(self.parent, "phase_label"):
                        self.parent.phase_label.config(text="PHASE: DISCONNECTED", fg="#ff3366")

                    # Phase 10.6: Auto-stop recording
                    if self._recording_controller and self._recording_controller.is_active:
                        try:
                            self._recording_controller.stop_session()
                            self.log("📹 Recording stopped automatically")
                        except Exception as rec_e:
                            logger.error(f"Failed to auto-stop recording: {rec_e}")

                    # Phase 10.8: Reset server state UI
                    if hasattr(self.parent, "_reset_server_state"):
                        self.parent._reset_server_state()

                self.root.after(0, handle_disconnected)

            @self.parent.live_feed.on("gameComplete")
            def on_game_complete(data):
                # PRODUCTION FIX: Capture data snapshot
                data_snapshot = dict(data) if hasattr(data, "items") else {}

                # Marshal to Tkinter main thread with captured value
                def handle_game_complete(captured_data=data_snapshot):
                    game_num = captured_data.get("gameNumber", 0)
                    seed_data = captured_data.get("seedData")
                    self.log(f"💥 Game {game_num} complete")
                    # Attach seed data to the next ReplayEngine GAME_END for this game.
                    if seed_data and getattr(self.replay_engine, "game_id", None):
                        self.replay_engine.set_seed_data(self.replay_engine.game_id, seed_data)

                self.root.after(0, handle_game_complete)

            # Phase 10.7: Player identity event (once on connect)
            @self.parent.live_feed.on("player_identity")
            def on_player_identity(info):
                # PRODUCTION FIX: Capture info snapshot
                info_snapshot = dict(info) if hasattr(info, "items") else {}

                def handle_identity(captured_info=info_snapshot):
                    from services.event_bus import Events

                    self._player_id = captured_info.get("player_id")
                    self._username = captured_info.get("username")
                    self.log(f"👤 Logged in as: {self._username}")

                    # Set player info on recording controller
                    if self._recording_controller:
                        self._recording_controller.set_player_info(self._player_id, self._username)

                    # Publish to EventBus for other consumers
                    self.event_bus.publish(Events.PLAYER_IDENTITY, captured_info)

                self.root.after(0, handle_identity)

            # Phase 10.7: Player update event (after each trade)
            @self.parent.live_feed.on("player_update")
            def on_player_update(data):
                # PRODUCTION FIX: Capture data snapshot
                data_snapshot = dict(data) if hasattr(data, "items") else {}

                def handle_update(captured_data=data_snapshot):
                    from models.recording_models import ServerState
                    from services.event_bus import Events

                    # Create ServerState from WebSocket data
                    server_state = ServerState.from_websocket(captured_data)

                    # Forward to recording controller
                    if self._recording_controller:
                        self._recording_controller.update_server_state(server_state)

                    # Publish to EventBus for other consumers
                    self.event_bus.publish(
                        Events.PLAYER_UPDATE,
                        {"server_state": server_state, "raw_data": captured_data},
                    )

                self.root.after(0, handle_update)

            # Bug 6 Fix: Connect to feed in background thread (non-blocking)
            # This prevents UI freeze during Socket.IO handshake (up to 20s timeout)
            def connect_in_background():
                try:
                    self.parent.live_feed.connect()
                except Exception as e:
                    logger.error(f"Background connection failed: {e}", exc_info=True)

                    # Marshal error handling to main thread
                    def handle_error():
                        self.log(f"Failed to connect to live feed: {e}")
                        if self.toast:
                            self.toast.show(f"Live feed error: {e}", "error")
                        self.parent.live_feed = None
                        self.parent.live_feed_connected = False
                        self.live_feed_var.set(False)

                    self.root.after(0, handle_error)

            connection_thread = threading.Thread(target=connect_in_background, daemon=True)
            connection_thread.start()

        except Exception as e:
            logger.error(f"Failed to enable live feed: {e}", exc_info=True)
            self.log(f"Failed to connect to live feed: {e}")
            if self.toast:
                self.toast.show(f"Live feed error: {e}", "error")
            self.parent.live_feed = None
            self.parent.live_feed_connected = False
            # Sync menu checkbox state (connection failed)
            self.live_feed_var.set(False)

    def disable_live_feed(self):
        """Disable WebSocket live feed"""
        if not self.parent.live_feed:
            self.log("Live feed not active")
            return

        try:
            self.log("Disconnecting from live feed...")
            self.parent.live_feed.disconnect()
            self.parent.live_feed = None
            self.parent.live_feed_connected = False
            # Phase 10.5: Reset game tracking
            # Phase 10.7: Reset player tracking
            self._player_id = None
            self._username = None
            self.toast.show("Live feed disconnected", "info")
            if hasattr(self.parent, "phase_label"):
                self.parent.phase_label.config(text="PHASE: DISCONNECTED", fg="white")
        except Exception as e:
            logger.error(f"Error disconnecting live feed: {e}", exc_info=True)
            self.log(f"Error disconnecting: {e}")

    def toggle_live_feed(self):
        """Toggle live feed on/off"""
        if self.parent.live_feed_connected:
            self.disable_live_feed()
        else:
            self.enable_live_feed()

    def toggle_live_feed_from_menu(self):
        """
        Toggle live feed connection from menu (syncs with actual state)
        AUDIT FIX: Ensure all UI updates happen in main thread
        """

        def do_toggle():
            self.toggle_live_feed()
            # Checkbox will be synced in event handlers (connected/disconnected)
            # Don't sync here - connection is async and takes 100-2000ms!

        # AUDIT FIX: Defensive - ensure always runs in main thread
        self.root.after(0, do_toggle)

    # ========================================================================
    # CLEANUP
    # ========================================================================

    def cleanup(self):
        """Cleanup live feed on shutdown (Phase 6 cleanup)"""
        if self.parent.live_feed_connected and self.parent.live_feed:
            try:
                logger.info("Shutting down live feed...")
                self.parent.live_feed.disconnect()
                self.parent.live_feed = None
                self.parent.live_feed_connected = False
                # Phase 10.5: Reset game tracking
                # Phase 10.7: Reset player tracking
                self._player_id = None
                self._username = None
            except Exception as e:
                logger.error(f"Error disconnecting live feed during shutdown: {e}", exc_info=True)
