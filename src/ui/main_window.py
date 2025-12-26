"""
Main Window UI Module - Refactored with Mixins
"""

import logging
import tkinter as tk
from decimal import Decimal
from tkinter import ttk

from bot import BotController, BotInterface, list_strategies
from bot.async_executor import AsyncBotExecutor
from bot.execution_mode import ExecutionMode
from bot.ui_controller import BotUIController
from browser.bridge import get_browser_bridge
from core import ReplayEngine, TradeManager
from core.game_queue import GameQueue
from services.event_store import EventStoreService
from services.live_state_provider import LiveStateProvider
from services.ui_dispatcher import TkDispatcher
from ui.bot_config_panel import BotConfigPanel
from ui.builders import (
    BettingBuilder,
    ChartBuilder,
    MenuBarBuilder,
    PlaybackBuilder,
    StatusBarBuilder,
)

# Import mixins
from ui.handlers.balance_handlers import BalanceHandlersMixin
from ui.handlers.event_handlers import EventHandlersMixin
from ui.handlers.player_handlers import PlayerHandlersMixin
from ui.handlers.replay_handlers import ReplayHandlersMixin
from ui.interactions.keyboard_shortcuts import KeyboardShortcutsMixin
from ui.interactions.theme_manager import ThemeManagerMixin
from ui.widgets import ToastNotification
from ui.window.shutdown import ShutdownMixin

logger = logging.getLogger(__name__)


class MainWindow(
    BalanceHandlersMixin,
    EventHandlersMixin,
    PlayerHandlersMixin,
    ReplayHandlersMixin,
    KeyboardShortcutsMixin,
    ThemeManagerMixin,
    ShutdownMixin,
):
    """
    Main application window with integrated ReplayEngine.

    Supports two modes:
    - Replay mode: Playback recorded game sessions
    - Live mode: Real-time WebSocket feed with optional browser automation
    """

    def __init__(self, root: tk.Tk, state, event_bus, config, live_mode: bool = False):
        self.root = root
        self.state = state
        self.event_bus = event_bus
        self.config = config
        self.live_mode = live_mode

        # Balance editing state
        self.balance_locked = True
        self.manual_balance: Decimal | None = None
        self.tracked_balance: Decimal = self.state.get("balance")

        # Server state tracking
        self.server_username: str | None = None
        self.server_player_id: str | None = None
        self.server_balance: Decimal | None = None
        self.server_authenticated = False

        # Browser executor
        self.browser_executor = None
        self.browser_connected = False

        # Optional tooling (initialized for shutdown safety)
        self._debug_terminal = None
        self._debug_terminal_event_cb = None

        try:
            from browser.executor import BrowserExecutor

            self.browser_executor = BrowserExecutor(profile_name="rugs_fun_phantom")
            logger.info("BrowserExecutor available")
        except Exception as e:
            logger.warning(f"BrowserExecutor not available: {e}")

        self.browser_bridge = get_browser_bridge()
        logger.info("BrowserBridge initialized")

        # Core components
        self.replay_engine = ReplayEngine(state)
        self.trade_manager = TradeManager(state)

        # EventStore persists all events to Parquet (canonical data store)
        # AUDIT FIX: Defer toast notifications until toast is initialized
        self._deferred_notifications = []
        try:
            self.event_store_service = EventStoreService(event_bus)
            self.event_store_service.start()
            logger.info(
                f"EventStoreService started: session {self.event_store_service.session_id[:8]}"
            )
        except Exception as e:
            logger.error(f"Failed to start EventStoreService: {e}", exc_info=True)
            self.event_store_service = None
            # Defer toast notification until after _create_ui()
            self._deferred_notifications.append(("Warning: Event storage disabled", "warning"))

        # LiveStateProvider for server-authoritative state in live mode (Phase 12C)
        try:
            self.live_state_provider = LiveStateProvider(event_bus)
            logger.info("LiveStateProvider initialized for server-authoritative state")
        except Exception as e:
            logger.error(f"Failed to initialize LiveStateProvider: {e}", exc_info=True)
            self.live_state_provider = None
            # Defer toast notification until after _create_ui()
            self._deferred_notifications.append(
                ("Warning: Live state tracking disabled", "warning")
            )

        # Game queue
        recordings_dir = config.FILES["recordings_dir"]
        self.game_queue = GameQueue(recordings_dir)
        self.multi_game_mode = False

        # Bot configuration
        self.bot_config_panel = BotConfigPanel(root, config_file="bot_config.json")
        bot_config = self.bot_config_panel.get_config()
        self.bot_interface = BotInterface(state, self.trade_manager)

        self.bot_ui_controller = None
        self.bot_controller = None
        self.bot_executor = None
        self.bot_enabled = self.bot_config_panel.is_bot_enabled()

        # Live feed
        self.live_feed = None
        self.live_feed_connected = False

        # UI dispatcher
        self.ui_dispatcher = TkDispatcher(self.root)
        self.user_paused = True

        # Replay callbacks
        self.replay_engine.on_tick_callback = self._on_tick_update
        self.replay_engine.on_game_end_callback = self._on_game_end

        # Toast notifications
        self.toast = None

        # Initialize UI
        self._create_ui()

        # AUDIT FIX: Show deferred notifications now that toast is initialized
        for message, msg_type in self._deferred_notifications:
            self.toast.show(message, msg_type)
        self._deferred_notifications = []

        self._setup_event_handlers()
        self._setup_toast_handlers()
        self._setup_keyboard_shortcuts()

        # Auto-start bot if enabled in config
        if self.bot_enabled:
            self.bot_executor.start()
            self.bot_toggle_button.config(state=tk.NORMAL)
            logger.info("Bot executor auto-started from config")

        # Auto-connect live feed
        if self.config.LIVE_FEED.get("auto_connect", False):
            self.root.after(1000, self._auto_connect_live_feed)

        # Start periodic capture stats updates
        self._update_capture_stats()

        logger.info("MainWindow initialized")

    def _create_menu_bar(self):
        """Create menu bar using MenuBarBuilder."""
        callbacks = {
            "load_file": lambda: self.replay_controller.load_file_dialog()
            if hasattr(self, "replay_controller")
            else None,
            "exit_app": self.root.quit,
            "toggle_playback": lambda: self.replay_controller.toggle_play_pause()
            if hasattr(self, "replay_controller")
            else None,
            "reset_game": lambda: self.replay_controller.reset_game()
            if hasattr(self, "replay_controller")
            else None,
            "toggle_bot": lambda: self.bot_manager.toggle_bot_from_menu()
            if hasattr(self, "bot_manager")
            else None,
            "show_bot_config": lambda: self.root.after(0, self.bot_manager.show_bot_config)
            if hasattr(self, "bot_manager")
            else None,
            "show_timing_metrics": lambda: self.root.after(0, self.bot_manager.show_timing_metrics)
            if hasattr(self, "bot_manager")
            else None,
            "toggle_timing_overlay": lambda: self.bot_manager.toggle_timing_overlay()
            if hasattr(self, "bot_manager")
            else None,
            "toggle_live_feed": lambda: self.live_feed_controller.toggle_live_feed_from_menu()
            if hasattr(self, "live_feed_controller")
            else None,
            "connect_browser": lambda: self.root.after(
                0, self.browser_bridge_controller.connect_browser_bridge
            )
            if hasattr(self, "browser_bridge_controller")
            else None,
            "disconnect_browser": lambda: self.root.after(
                0, self.browser_bridge_controller.disconnect_browser_bridge
            )
            if hasattr(self, "browser_bridge_controller")
            else None,
            "change_theme": self._change_theme,
            "set_ui_style": self._set_ui_style,
            "open_debug_terminal": self._open_debug_terminal,
            "show_about": self._show_about,
        }

        variables = {
            "bot_var": self.bot_var,
            "live_feed_var": self.live_feed_var,
            "timing_overlay_var": self.timing_overlay_var,
        }

        builder = MenuBarBuilder(self.root, callbacks, variables)
        _menubar, refs = builder.build()

        self.browser_menu = refs["browser_menu"]
        self.dev_menu = refs["dev_menu"]
        self.browser_status_item_index = refs["browser_status_item_index"]
        self.browser_disconnect_item_index = refs["browser_disconnect_item_index"]
        self.browser_connect_item_index = refs["browser_connect_item_index"]

    def _create_ui(self):
        """Create UI matching the user's mockup design"""
        # Create UI variables
        self.bot_var = tk.BooleanVar(value=self.bot_enabled)
        self.live_feed_var = tk.BooleanVar(value=self.live_feed_connected)
        self.timing_overlay_var = tk.BooleanVar(value=False)

        # ROW 1: STATUS BAR
        status_widgets = StatusBarBuilder(self.root).build()
        self.tick_label = status_widgets["tick_label"]
        self.price_label = status_widgets["price_label"]
        self.phase_label = status_widgets["phase_label"]
        self.player_profile_label = status_widgets["player_profile_label"]
        self.browser_status_label = status_widgets["browser_status_label"]
        self.source_label = status_widgets["source_label"]
        self.capture_stats_label = status_widgets["capture_stats_label"]

        # ROW 2: CHART
        chart_widgets = ChartBuilder(self.root).build()
        self.chart = chart_widgets["chart"]

        # ROW 3: PLAYBACK CONTROLS
        playback_callbacks = {
            "load_game": lambda: self.replay_controller.load_game()
            if hasattr(self, "replay_controller")
            else None,
            "toggle_playback": lambda: self.replay_controller.toggle_playback()
            if hasattr(self, "replay_controller")
            else None,
            "step_forward": lambda: self.replay_controller.step_forward()
            if hasattr(self, "replay_controller")
            else None,
            "reset_game": lambda: self.replay_controller.reset_game()
            if hasattr(self, "replay_controller")
            else None,
            "set_speed": lambda s: self.replay_controller.set_playback_speed(s)
            if hasattr(self, "replay_controller")
            else None,
        }
        playback_widgets = PlaybackBuilder(self.root, playback_callbacks).build()
        self.load_button = playback_widgets["load_button"]
        self.play_button = playback_widgets["play_button"]
        self.step_button = playback_widgets["step_button"]
        self.reset_button = playback_widgets["reset_button"]
        self.speed_label = playback_widgets["speed_label"]

        # ROW 4: BET AMOUNT CONTROLS
        bet_callbacks = {
            "clear_bet": lambda: self.trading_controller.clear_bet_amount()
            if hasattr(self, "trading_controller")
            else None,
            "increment_bet": lambda a: self.trading_controller.increment_bet_amount(a)
            if hasattr(self, "trading_controller")
            else None,
            "half_bet": lambda: self.trading_controller.half_bet_amount()
            if hasattr(self, "trading_controller")
            else None,
            "double_bet": lambda: self.trading_controller.double_bet_amount()
            if hasattr(self, "trading_controller")
            else None,
            "max_bet": lambda: self.trading_controller.max_bet_amount()
            if hasattr(self, "trading_controller")
            else None,
            "toggle_balance_lock": self._toggle_balance_lock,
        }
        bet_widgets = BettingBuilder(
            self.root,
            bet_callbacks,
            Decimal(str(self.config.FINANCIAL["default_bet"])),
            self.state.get("balance"),
        ).build()
        self.bet_entry = bet_widgets["bet_entry"]
        self.clear_button = bet_widgets["clear_button"]
        self.increment_001_button = bet_widgets["increment_001_button"]
        self.increment_01_button = bet_widgets["increment_01_button"]
        self.increment_10_button = bet_widgets["increment_10_button"]
        self.increment_1_button = bet_widgets["increment_1_button"]
        self.half_button = bet_widgets["half_button"]
        self.double_button = bet_widgets["double_button"]
        self.max_button = bet_widgets["max_button"]
        self.balance_label = bet_widgets["balance_label"]
        self.balance_lock_button = bet_widgets["balance_lock_button"]

        # ROW 5: ACTION BUTTONS
        self._create_action_row()

        # Draggable timing overlay
        from ui.timing_overlay import TimingOverlay

        self.timing_overlay = TimingOverlay(self.root, config_file="timing_overlay.json")

        # Toast notifications
        self.toast = ToastNotification(self.root)

        # Bot UI controller
        bot_config = self.bot_config_panel.get_config()
        self.bot_ui_controller = BotUIController(
            self,
            button_depress_duration_ms=bot_config.get("button_depress_duration_ms", 50),
            inter_click_pause_ms=bot_config.get("inter_click_pause_ms", 100),
        )

        # Bot controller
        execution_mode = self.bot_config_panel.get_execution_mode()
        strategy = self.bot_config_panel.get_strategy()

        self.bot_controller = BotController(
            self.bot_interface,
            strategy_name=strategy,
            execution_mode=execution_mode,
            ui_controller=self.bot_ui_controller
            if execution_mode == ExecutionMode.UI_LAYER
            else None,
        )

        self.bot_executor = AsyncBotExecutor(self.bot_controller)

        # Initialize controllers
        self._initialize_controllers()

    def _create_action_row(self):
        """Create the action buttons row."""
        action_row = tk.Frame(self.root, bg="#1a1a1a", height=80)
        action_row.pack(fill=tk.X)
        action_row.pack_propagate(False)

        # Left - large action buttons
        action_left = tk.Frame(action_row, bg="#1a1a1a")
        action_left.pack(side=tk.LEFT, padx=10, pady=10)

        large_btn_style = {
            "font": ("Arial", 14, "bold"),
            "width": 10,
            "height": 2,
            "bd": 2,
            "relief": tk.RAISED,
        }

        self.sidebet_button = tk.Button(
            action_left,
            text="SIDEBET",
            command=lambda: self.trading_controller.execute_sidebet()
            if hasattr(self, "trading_controller")
            else None,
            bg="#3399ff",
            fg="white",
            state=tk.NORMAL,
            **large_btn_style,
        )
        self.sidebet_button.pack(side=tk.LEFT, padx=5)

        self.buy_button = tk.Button(
            action_left,
            text="BUY",
            command=lambda: self.trading_controller.execute_buy()
            if hasattr(self, "trading_controller")
            else None,
            bg="#00ff66",
            fg="black",
            state=tk.NORMAL,
            **large_btn_style,
        )
        self.buy_button.pack(side=tk.LEFT, padx=5)

        self.sell_button = tk.Button(
            action_left,
            text="SELL",
            command=lambda: self.trading_controller.execute_sell()
            if hasattr(self, "trading_controller")
            else None,
            bg="#ff3399",
            fg="white",
            state=tk.NORMAL,
            **large_btn_style,
        )
        self.sell_button.pack(side=tk.LEFT, padx=5)

        # Percentage selector buttons
        separator = tk.Frame(action_left, bg="#444444", width=2)
        separator.pack(side=tk.LEFT, padx=10, fill=tk.Y, pady=15)

        pct_btn_style = {
            "font": ("Arial", 10, "bold"),
            "width": 6,
            "height": 1,
            "bd": 2,
            "relief": tk.RAISED,
        }

        self.percentage_buttons = {}
        percentages = [
            ("10%", 0.1, "#666666"),
            ("25%", 0.25, "#666666"),
            ("50%", 0.5, "#666666"),
            ("100%", 1.0, "#888888"),
        ]

        for text, value, default_color in percentages:
            btn = tk.Button(
                action_left,
                text=text,
                command=lambda v=value: self.trading_controller.set_sell_percentage(v)
                if hasattr(self, "trading_controller")
                else None,
                bg=default_color,
                fg="white",
                **pct_btn_style,
            )
            btn.pack(side=tk.LEFT, padx=3)
            self.percentage_buttons[value] = {
                "button": btn,
                "default_color": default_color,
                "selected_color": "#00cc66",
                "value": value,
            }

        self.current_sell_percentage = 1.0
        if hasattr(self, "trading_controller"):
            self.trading_controller.highlight_percentage_button(1.0)

        # Right - bot controls
        action_right = tk.Frame(action_row, bg="#1a1a1a")
        action_right.pack(side=tk.RIGHT, padx=10, pady=10)

        bot_top = tk.Frame(action_right, bg="#1a1a1a")
        bot_top.pack(anchor="e")

        self.bot_toggle_button = tk.Button(
            bot_top,
            text="ENABLE BOT",
            command=lambda: self.bot_manager.toggle_bot() if hasattr(self, "bot_manager") else None,
            bg="#444444",
            fg="white",
            font=("Arial", 10),
            width=12,
            state=tk.DISABLED,
        )
        self.bot_toggle_button.pack(side=tk.LEFT, padx=5)

        tk.Label(bot_top, text="STRATEGY:", bg="#1a1a1a", fg="white", font=("Arial", 9)).pack(
            side=tk.LEFT, padx=5
        )

        loaded_strategy = self.bot_config_panel.get_strategy()
        self.strategy_var = tk.StringVar(value=loaded_strategy)
        self.strategy_dropdown = ttk.Combobox(
            bot_top,
            textvariable=self.strategy_var,
            values=list_strategies(),
            state="readonly",
            width=12,
            font=("Arial", 9),
        )
        self.strategy_dropdown.pack(side=tk.LEFT)
        self.strategy_dropdown.bind(
            "<<ComboboxSelected>>",
            lambda e: self.bot_manager.on_strategy_changed(e)
            if hasattr(self, "bot_manager")
            else None,
        )

        bot_bottom = tk.Frame(action_right, bg="#1a1a1a")
        bot_bottom.pack(anchor="e", pady=(5, 0))

        self.bot_status_label = tk.Label(
            bot_bottom, text="BOT: DISABLED", font=("Arial", 10), bg="#1a1a1a", fg="#666666"
        )
        self.bot_status_label.pack(side=tk.LEFT, padx=10)

        self.position_label = tk.Label(
            bot_bottom, text="POSITION: NONE", font=("Arial", 10), bg="#1a1a1a", fg="#666666"
        )
        self.position_label.pack(side=tk.LEFT, padx=10)

        self.sidebet_status_label = tk.Label(
            bot_bottom, text="SIDEBET: NONE", font=("Arial", 10), bg="#1a1a1a", fg="#666666"
        )
        self.sidebet_status_label.pack(side=tk.LEFT, padx=10)

    def _initialize_controllers(self):
        """Initialize UI controllers."""
        from ui.controllers import (
            BotManager,
            BrowserBridgeController,
            LiveFeedController,
            ReplayController,
            TradingController,
        )

        self.bot_manager = BotManager(
            root=self.root,
            state=self.state,
            bot_executor=self.bot_executor,
            bot_controller=self.bot_controller,
            bot_config_panel=self.bot_config_panel,
            timing_overlay=self.timing_overlay,
            browser_executor=self.browser_executor,
            bot_toggle_button=self.bot_toggle_button,
            bot_status_label=self.bot_status_label,
            buy_button=self.buy_button,
            sell_button=self.sell_button,
            sidebet_button=self.sidebet_button,
            strategy_var=self.strategy_var,
            bot_var=self.bot_var,
            timing_overlay_var=self.timing_overlay_var,
            toast=self.toast,
            log_callback=self.log,
        )

        self.replay_controller = ReplayController(
            root=self.root,
            parent_window=self,
            replay_engine=self.replay_engine,
            chart=self.chart,
            config=self.config,
            play_button=self.play_button,
            step_button=self.step_button,
            reset_button=self.reset_button,
            bot_toggle_button=self.bot_toggle_button,
            speed_label=self.speed_label,
            toast=self.toast,
            log_callback=self.log,
        )

        self.trading_controller = TradingController(
            parent_window=self,
            trade_manager=self.trade_manager,
            state=self.state,
            config=self.config,
            browser_bridge=self.browser_bridge,
            bet_entry=self.bet_entry,
            percentage_buttons=self.percentage_buttons,
            ui_dispatcher=self.ui_dispatcher,
            toast=self.toast,
            log_callback=self.log,
        )

        self.live_feed_controller = LiveFeedController(
            root=self.root,
            parent_window=self,
            replay_engine=self.replay_engine,
            event_bus=self.event_bus,
            live_feed_var=self.live_feed_var,
            toast=self.toast,
            log_callback=self.log,
        )

        self._create_menu_bar()

        self.browser_bridge_controller = BrowserBridgeController(
            root=self.root,
            parent_window=self,
            browser_menu=self.browser_menu,
            browser_status_item_index=self.browser_status_item_index,
            browser_disconnect_item_index=self.browser_disconnect_item_index,
            toast=self.toast,
            log_callback=self.log,
        )

        self.browser_bridge.on_status_change = (
            self.browser_bridge_controller.on_bridge_status_change
        )

    def log(self, message: str):
        """Log message (using logger instead of text widget)"""
        logger.info(message)

    def _update_capture_stats(self):
        """Update the status bar capture stats (EventStore session + buffered event count)."""
        event_store_service = getattr(self, "event_store_service", None)
        capture_stats_label = getattr(self, "capture_stats_label", None)

        if event_store_service is not None and capture_stats_label is not None:
            session_id = str(getattr(event_store_service, "session_id", "--------"))[:8]
            try:
                event_count = int(getattr(event_store_service, "event_count", 0))
            except Exception:
                event_count = 0

            capture_stats_label.config(text=f"Session: {session_id} | Events: {event_count}")

        self.root.after(1000, self._update_capture_stats)

    def _open_debug_terminal(self):
        """Open (or focus) the WebSocket debug terminal window."""
        try:
            if (
                getattr(self, "_debug_terminal", None)
                and self._debug_terminal.window.winfo_exists()
            ):
                self._debug_terminal.window.deiconify()
                self._debug_terminal.window.lift()
                self._debug_terminal.window.focus_force()
                return

            from services.event_bus import Events
            from ui.debug_terminal import DebugTerminal

            def on_close():
                try:
                    if getattr(self, "_debug_terminal_event_cb", None):
                        self.event_bus.unsubscribe(
                            Events.WS_RAW_EVENT, self._debug_terminal_event_cb
                        )
                finally:
                    self._debug_terminal_event_cb = None
                    self._debug_terminal = None

            terminal = DebugTerminal(self.root, on_close=on_close)
            self._debug_terminal = terminal

            def handle_ws_event(data):
                event = data
                if isinstance(data, dict) and "event" not in data and "data" in data:
                    if isinstance(data["data"], dict):
                        event = data["data"]

                if not isinstance(event, dict):
                    event = {"event": "unknown", "data": event}

                if "timestamp" not in event:
                    event["timestamp"] = ""

                terminal.log_event(event)

            self._debug_terminal_event_cb = handle_ws_event
            self.event_bus.subscribe(Events.WS_RAW_EVENT, handle_ws_event, weak=False)

        except Exception as e:
            logger.error(f"Failed to open debug terminal: {e}", exc_info=True)
            if getattr(self, "toast", None):
                self.toast.show("Failed to open debug terminal", "error")

    def _show_about(self):
        """Show About dialog."""
        try:
            from tkinter import messagebox

            messagebox.showinfo(
                "About VECTRA-PLAYER",
                "VECTRA-PLAYER\nUnified game replay and live trading platform.",
            )
        except Exception as e:
            logger.error(f"Failed to show About dialog: {e}", exc_info=True)

    def _auto_connect_live_feed(self):
        """Auto-connect to live feed on startup."""
        if hasattr(self, "live_feed_controller"):
            logger.info("Auto-connecting to live feed...")
            self.live_feed_controller.toggle_live_feed()
