"""
MinimalWindow - Single-file minimal UI for RL training data collection.

Stripped-down UI with only essential components:
- Status bar: TICK, PRICE, PHASE, USER, BALANCE, CONNECTION
- Percentage selector: Vertical stack (10%, 25%, 50%, 100%)
- Increment buttons: +0.001, +0.01, +0.1, +1
- Utility buttons: 1/2, X2, MAX
- Bet entry: X (clear) + input field + "SOL" label
- Action buttons: BUY (green), SIDEBET (yellow), SELL (blue)

All visual components (charts, overlays, animations) removed.
Buttons emit ButtonEvents with timestamps for latency tracking.

Task 2: TradingController Integration
- Button clicks are delegated to TradingController for ButtonEvent emission
- TradingController handles latency tracking and EventBus publishing
"""

import logging
import tkinter as tk
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.game_state import GameState
    from services.event_bus import EventBus
    from ui.controllers.trading_controller import TradingController

logger = logging.getLogger(__name__)

# Colors
BG_COLOR = "#1a1a1a"
PANEL_COLOR = "#2a2a2a"
TEXT_COLOR = "#ffffff"
TEXT_DIM = "#888888"
GREEN_COLOR = "#00ff66"
YELLOW_COLOR = "#ffcc00"
BLUE_COLOR = "#3399ff"
GRAY_COLOR = "#666666"
SELECTED_COLOR = "#00cc66"


class MinimalWindow:
    """
    Minimal UI window for RL training data collection.

    Plain Tk widgets, no mixins, no animations.
    Status bar + controls layout only.
    """

    def __init__(
        self,
        root: tk.Tk,
        game_state: "GameState",
        event_bus: "EventBus",
        config: Any,
        trading_controller: "TradingController | None" = None,
        browser_bridge: Any = None,
        live_state_provider: Any = None,
    ):
        """
        Initialize MinimalWindow.

        Args:
            root: Tk root window
            game_state: GameState instance for state access
            event_bus: EventBus for event subscriptions
            config: Configuration object
            trading_controller: Optional TradingController for ButtonEvent emission
            browser_bridge: Optional BrowserBridge for browser clicks
            live_state_provider: Optional LiveStateProvider for live game context
        """
        self.root = root
        self.game_state = game_state
        self.event_bus = event_bus
        self.config = config
        self.browser_bridge = browser_bridge
        self.live_state_provider = live_state_provider

        # Configure root window
        self.root.title("VECTRA-PLAYER - Minimal UI")
        self.root.configure(bg=BG_COLOR)
        self.root.geometry("900x200")
        self.root.minsize(800, 180)

        # Current state
        self.current_sell_percentage = 1.0
        self.bet_amount = Decimal("0.0")

        # Widget references (set during _create_ui)
        self.tick_label: tk.Label | None = None
        self.price_label: tk.Label | None = None
        self.phase_label: tk.Label | None = None
        self.connection_label: tk.Label | None = None
        self.user_label: tk.Label | None = None
        self.balance_label: tk.Label | None = None
        self.bet_entry: tk.Entry | None = None
        self.percentage_buttons: dict[float, dict] = {}

        # Build UI first (before TradingController, as it needs bet_entry)
        self._create_ui()

        # TradingController for ButtonEvent emission (Task 2)
        # Created after UI so bet_entry exists
        self.trading_controller = trading_controller
        if self.trading_controller is None and self.bet_entry is not None:
            self._create_trading_controller()

        logger.info("MinimalWindow initialized")

    def _create_ui(self):
        """Create the minimal UI layout."""
        # Main container
        main_frame = tk.Frame(self.root, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # STATUS BAR (Row 1)
        self._create_status_bar(main_frame)

        # Separator
        separator = tk.Frame(main_frame, bg=GRAY_COLOR, height=1)
        separator.pack(fill=tk.X, pady=10)

        # CONTROLS (Row 2)
        self._create_controls(main_frame)

    def _create_status_bar(self, parent: tk.Frame):
        """Create status bar with game state labels."""
        status_frame = tk.Frame(parent, bg=BG_COLOR)
        status_frame.pack(fill=tk.X)

        # Row 1: TICK, PRICE, PHASE, CONNECTION
        row1 = tk.Frame(status_frame, bg=BG_COLOR)
        row1.pack(fill=tk.X)

        # TICK
        tk.Label(row1, text="TICK:", bg=BG_COLOR, fg=TEXT_DIM, font=("Arial", 10)).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        self.tick_label = tk.Label(
            row1, text="0000", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")
        )
        self.tick_label.pack(side=tk.LEFT, padx=(0, 20))

        # PRICE
        tk.Label(row1, text="PRICE:", bg=BG_COLOR, fg=TEXT_DIM, font=("Arial", 10)).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        self.price_label = tk.Label(
            row1, text="0000.00", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")
        )
        self.price_label.pack(side=tk.LEFT, padx=(0, 20))

        # PHASE
        tk.Label(row1, text="PHASE:", bg=BG_COLOR, fg=TEXT_DIM, font=("Arial", 10)).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        self.phase_label = tk.Label(
            row1, text="UNKNOWN", bg=BG_COLOR, fg=YELLOW_COLOR, font=("Arial", 10, "bold")
        )
        self.phase_label.pack(side=tk.LEFT, padx=(0, 20))

        # CONNECTION (indicator dot on right)
        connection_frame = tk.Frame(row1, bg=BG_COLOR)
        connection_frame.pack(side=tk.RIGHT)
        tk.Label(
            connection_frame, text="CONNECTION:", bg=BG_COLOR, fg=TEXT_DIM, font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=(0, 5))
        self.connection_label = tk.Label(
            connection_frame, text="\u25cf", bg=BG_COLOR, fg=GRAY_COLOR, font=("Arial", 12)
        )
        self.connection_label.pack(side=tk.LEFT)

        # Row 2: USER, BALANCE
        row2 = tk.Frame(status_frame, bg=BG_COLOR)
        row2.pack(fill=tk.X, pady=(5, 0))

        # USER
        tk.Label(row2, text="USER:", bg=BG_COLOR, fg=TEXT_DIM, font=("Arial", 10)).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        self.user_label = tk.Label(
            row2, text="---", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")
        )
        self.user_label.pack(side=tk.LEFT, padx=(0, 40))

        # BALANCE (on right)
        balance_frame = tk.Frame(row2, bg=BG_COLOR)
        balance_frame.pack(side=tk.RIGHT)
        tk.Label(balance_frame, text="BALANCE:", bg=BG_COLOR, fg=TEXT_DIM, font=("Arial", 10)).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        self.balance_label = tk.Label(
            balance_frame,
            text="00.000 SOL",
            bg=BG_COLOR,
            fg=GREEN_COLOR,
            font=("Arial", 10, "bold"),
        )
        self.balance_label.pack(side=tk.LEFT)

    def _create_controls(self, parent: tk.Frame):
        """Create control buttons and bet entry."""
        controls_frame = tk.Frame(parent, bg=BG_COLOR)
        controls_frame.pack(fill=tk.X)

        # LEFT: Percentage buttons (vertical stack)
        pct_frame = tk.Frame(controls_frame, bg=BG_COLOR)
        pct_frame.pack(side=tk.LEFT, padx=(0, 15))

        pct_btn_style = {
            "font": ("Arial", 9, "bold"),
            "width": 5,
            "height": 1,
            "bd": 2,
            "relief": tk.RAISED,
        }

        percentages = [
            ("10%", 0.1),
            ("25%", 0.25),
            ("50%", 0.5),
            ("100%", 1.0),
        ]

        for text, value in percentages:
            btn = tk.Button(
                pct_frame,
                text=text,
                command=lambda v=value: self._on_percentage_clicked(v),
                bg=GRAY_COLOR,
                fg=TEXT_COLOR,
                activebackground=SELECTED_COLOR,
                activeforeground="black",
                **pct_btn_style,
            )
            btn.pack(pady=2)
            self.percentage_buttons[value] = {
                "button": btn,
                "default_color": GRAY_COLOR,
                "selected_color": SELECTED_COLOR,
                "value": value,
            }

        # Highlight default (100%)
        self._highlight_percentage_button(1.0)

        # CENTER: Increment buttons + Bet entry + Utility buttons
        center_frame = tk.Frame(controls_frame, bg=BG_COLOR)
        center_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Increment row
        inc_row = tk.Frame(center_frame, bg=BG_COLOR)
        inc_row.pack(fill=tk.X, pady=(0, 8))

        inc_btn_style = {
            "font": ("Arial", 9),
            "width": 6,
            "bd": 1,
            "relief": tk.RAISED,
            "bg": PANEL_COLOR,
            "fg": TEXT_COLOR,
            "activebackground": GRAY_COLOR,
        }

        # Increment buttons: +0.001, +0.01, +0.1, +1
        increments = ["+0.001", "+0.01", "+0.1", "+1"]
        for inc_text in increments:
            btn = tk.Button(
                inc_row,
                text=inc_text,
                command=lambda t=inc_text: self._on_increment_clicked(t),
                **inc_btn_style,
            )
            btn.pack(side=tk.LEFT, padx=3)

        # Spacer
        tk.Frame(inc_row, bg=BG_COLOR, width=30).pack(side=tk.LEFT)

        # Utility buttons: 1/2, X2, MAX
        utility_buttons = ["1/2", "X2", "MAX"]
        for util_text in utility_buttons:
            btn = tk.Button(
                inc_row,
                text=util_text,
                command=lambda t=util_text: self._on_utility_clicked(t),
                **inc_btn_style,
            )
            btn.pack(side=tk.LEFT, padx=3)

        # Bet amount row
        bet_row = tk.Frame(center_frame, bg=BG_COLOR)
        bet_row.pack(fill=tk.X)

        tk.Label(bet_row, text="BET AMOUNT", bg=BG_COLOR, fg=TEXT_DIM, font=("Arial", 9)).pack(
            side=tk.LEFT, padx=(0, 10)
        )

        # X (clear) button
        clear_btn = tk.Button(
            bet_row,
            text="X",
            command=self._on_clear_clicked,
            font=("Arial", 10, "bold"),
            width=3,
            bd=1,
            relief=tk.RAISED,
            bg="#cc3333",
            fg=TEXT_COLOR,
            activebackground="#ff4444",
        )
        clear_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Bet entry
        self.bet_entry = tk.Entry(
            bet_row,
            font=("Arial", 12),
            width=12,
            bg=PANEL_COLOR,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            relief=tk.SUNKEN,
            bd=2,
        )
        self.bet_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.bet_entry.insert(0, "0.000")

        # SOL label
        tk.Label(bet_row, text="SOL", bg=BG_COLOR, fg=TEXT_DIM, font=("Arial", 10, "bold")).pack(
            side=tk.LEFT, padx=(0, 20)
        )

        # RIGHT: Action buttons
        action_frame = tk.Frame(controls_frame, bg=BG_COLOR)
        action_frame.pack(side=tk.RIGHT, padx=(20, 0))

        action_btn_style = {
            "font": ("Arial", 14, "bold"),
            "width": 10,
            "height": 2,
            "bd": 2,
            "relief": tk.RAISED,
        }

        # BUY button (green)
        buy_btn = tk.Button(
            action_frame,
            text="BUY",
            command=self._on_buy_clicked,
            bg=GREEN_COLOR,
            fg="black",
            activebackground="#00cc55",
            activeforeground="black",
            **action_btn_style,
        )
        buy_btn.pack(side=tk.LEFT, padx=5)

        # SIDEBET button (yellow)
        sidebet_btn = tk.Button(
            action_frame,
            text="SIDEBET",
            command=self._on_sidebet_clicked,
            bg=YELLOW_COLOR,
            fg="black",
            activebackground="#ddaa00",
            activeforeground="black",
            **action_btn_style,
        )
        sidebet_btn.pack(side=tk.LEFT, padx=5)

        # SELL button (blue)
        sell_btn = tk.Button(
            action_frame,
            text="SELL",
            command=self._on_sell_clicked,
            bg=BLUE_COLOR,
            fg=TEXT_COLOR,
            activebackground="#2277dd",
            activeforeground=TEXT_COLOR,
            **action_btn_style,
        )
        sell_btn.pack(side=tk.LEFT, padx=5)

    # =========================================================================
    # TRADING CONTROLLER SETUP (Task 2)
    # =========================================================================

    def _create_trading_controller(self):
        """
        Create TradingController with minimal dependencies for MinimalWindow.

        TradingController is responsible for:
        - Emitting ButtonEvents with timestamps
        - Coordinating with BrowserBridge for browser clicks
        - Tracking action sequences
        """
        from ui.controllers.trading_controller import TradingController

        # Create minimal dispatcher that runs callbacks directly (for testing)
        # In production, this would be replaced with TkDispatcher
        class MinimalDispatcher:
            @staticmethod
            def submit(callback):
                callback()

        # Create minimal toast that just logs
        class MinimalToast:
            @staticmethod
            def show(message: str, level: str = "info"):
                logger.info(f"[Toast:{level}] {message}")

        self.trading_controller = TradingController(
            parent_window=self,
            trade_manager=None,  # Not needed for ButtonEvent emission
            state=self.game_state,
            config=self.config,
            browser_bridge=self.browser_bridge or _NullBrowserBridge(),
            bet_entry=self.bet_entry,
            percentage_buttons=self.percentage_buttons,
            ui_dispatcher=MinimalDispatcher(),
            toast=MinimalToast(),
            log_callback=lambda msg: logger.info(f"[TradingController] {msg}"),
            event_bus=self.event_bus,
            live_state_provider=self.live_state_provider,
        )
        logger.debug("TradingController created for MinimalWindow")

    # =========================================================================
    # BUTTON CALLBACKS (Wired to TradingController - Task 2)
    # =========================================================================

    def _on_percentage_clicked(self, percentage: float):
        """Handle percentage button click - delegates to TradingController."""
        logger.debug(f"Percentage clicked: {percentage * 100:.0f}%")
        self.current_sell_percentage = percentage
        self._highlight_percentage_button(percentage)

        # Delegate to TradingController for ButtonEvent emission
        if self.trading_controller:
            self.trading_controller.set_sell_percentage(percentage)

    def _highlight_percentage_button(self, selected: float):
        """Highlight selected percentage button (radio-button style)."""
        for pct, info in self.percentage_buttons.items():
            btn = info["button"]
            if pct == selected:
                btn.config(bg=info["selected_color"], relief=tk.SUNKEN, bd=3)
            else:
                btn.config(bg=info["default_color"], relief=tk.RAISED, bd=2)

    def _on_increment_clicked(self, increment: str):
        """Handle increment button click - delegates to TradingController."""
        logger.debug(f"Increment clicked: {increment}")

        # Delegate to TradingController for ButtonEvent emission
        if self.trading_controller:
            try:
                amount = Decimal(increment)
                self.trading_controller.increment_bet_amount(amount)
            except Exception as e:
                logger.warning(f"Failed to parse increment {increment}: {e}")
        else:
            # Fallback: direct update if no TradingController
            try:
                value = Decimal(increment)
                current = Decimal(self.bet_entry.get())
                new_amount = current + value
                self.bet_entry.delete(0, tk.END)
                self.bet_entry.insert(0, str(new_amount))
            except Exception as e:
                logger.warning(f"Failed to apply increment {increment}: {e}")

    def _on_utility_clicked(self, utility: str):
        """Handle utility button click - delegates to TradingController."""
        logger.debug(f"Utility clicked: {utility}")

        # Delegate to TradingController for ButtonEvent emission
        if self.trading_controller:
            if utility == "1/2":
                self.trading_controller.half_bet_amount()
            elif utility == "X2":
                self.trading_controller.double_bet_amount()
            elif utility == "MAX":
                self.trading_controller.max_bet_amount()
        else:
            # Fallback: direct update if no TradingController
            try:
                current = Decimal(self.bet_entry.get())
                if utility == "1/2":
                    new_amount = current / 2
                elif utility == "X2":
                    new_amount = current * 2
                elif utility == "MAX":
                    balance = self.game_state.get("balance", Decimal("0"))
                    new_amount = balance
                else:
                    return

                self.bet_entry.delete(0, tk.END)
                self.bet_entry.insert(0, str(new_amount))
            except Exception as e:
                logger.warning(f"Failed to apply utility {utility}: {e}")

    def _on_clear_clicked(self):
        """Handle clear (X) button click - delegates to TradingController."""
        logger.debug("Clear clicked")

        # Delegate to TradingController for ButtonEvent emission
        if self.trading_controller:
            self.trading_controller.clear_bet_amount()
        else:
            # Fallback: direct update if no TradingController
            self.bet_entry.delete(0, tk.END)
            self.bet_entry.insert(0, "0.000")

    def _on_buy_clicked(self):
        """Handle BUY button click - delegates to TradingController."""
        logger.debug("BUY clicked")

        # Delegate to TradingController for ButtonEvent emission
        if self.trading_controller:
            self.trading_controller.execute_buy()

    def _on_sidebet_clicked(self):
        """Handle SIDEBET button click - delegates to TradingController."""
        logger.debug("SIDEBET clicked")

        # Delegate to TradingController for ButtonEvent emission
        if self.trading_controller:
            self.trading_controller.execute_sidebet()

    def _on_sell_clicked(self):
        """Handle SELL button click - delegates to TradingController."""
        logger.debug("SELL clicked")

        # Delegate to TradingController for ButtonEvent emission
        if self.trading_controller:
            self.trading_controller.execute_sell()

    # =========================================================================
    # STATUS UPDATE METHODS (Placeholder for Task 3)
    # =========================================================================

    def update_tick(self, tick: int):
        """Update tick display."""
        if self.tick_label:
            self.tick_label.config(text=f"{tick:04d}")

    def update_price(self, price: float):
        """Update price display."""
        if self.price_label:
            self.price_label.config(text=f"{price:.2f}")

    def update_phase(self, phase: str):
        """Update phase display with color coding."""
        if self.phase_label:
            # Color code by phase
            color = TEXT_COLOR
            if phase == "ACTIVE":
                color = GREEN_COLOR
            elif phase == "PRESALE":
                color = YELLOW_COLOR
            elif phase in ("COOLDOWN", "RUGGED"):
                color = "#ff3366"  # Red
            self.phase_label.config(text=phase, fg=color)

    def update_connection(self, connected: bool):
        """Update connection indicator."""
        if self.connection_label:
            if connected:
                self.connection_label.config(fg=GREEN_COLOR)
            else:
                self.connection_label.config(fg=GRAY_COLOR)

    def update_user(self, username: str):
        """Update user display."""
        if self.user_label:
            self.user_label.config(text=username if username else "---")

    def update_balance(self, balance: Decimal):
        """Update balance display."""
        if self.balance_label:
            self.balance_label.config(text=f"{balance:.3f} SOL")

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_bet_amount(self) -> Decimal:
        """Get current bet amount from entry."""
        try:
            return Decimal(self.bet_entry.get())
        except Exception:
            return Decimal("0")

    def set_bet_amount(self, amount: Decimal):
        """Set bet amount in entry."""
        self.bet_entry.delete(0, tk.END)
        self.bet_entry.insert(0, str(amount))

    def get_sell_percentage(self) -> float:
        """Get current sell percentage."""
        return self.current_sell_percentage


class _NullBrowserBridge:
    """
    Null object pattern for BrowserBridge when no browser is connected.

    All methods are no-ops that log debug messages.
    Prevents errors when TradingController tries to interact with browser.
    """

    def on_buy_clicked(self):
        """No-op BUY click."""
        logger.debug("NullBrowserBridge: on_buy_clicked (no browser connected)")

    def on_sell_clicked(self):
        """No-op SELL click."""
        logger.debug("NullBrowserBridge: on_sell_clicked (no browser connected)")

    def on_sidebet_clicked(self):
        """No-op SIDEBET click."""
        logger.debug("NullBrowserBridge: on_sidebet_clicked (no browser connected)")

    def on_percentage_clicked(self, percentage: float):
        """No-op percentage click."""
        logger.debug(
            f"NullBrowserBridge: on_percentage_clicked({percentage}) (no browser connected)"
        )

    def on_increment_clicked(self, increment: str):
        """No-op increment click."""
        logger.debug(f"NullBrowserBridge: on_increment_clicked({increment}) (no browser connected)")

    def on_clear_clicked(self):
        """No-op clear click."""
        logger.debug("NullBrowserBridge: on_clear_clicked (no browser connected)")
