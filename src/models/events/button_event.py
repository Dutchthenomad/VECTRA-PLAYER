"""
ButtonEvent and ActionSequence models for human gameplay recording.

Phase B: ButtonEvent Logging Implementation
These models capture every button press with full game context for RL training.

Key Outcomes to Track:
- Positions active during rug → LIQUIDATED (total loss)
- Sidebets active during rug → WON (5X payout, 400% net profit)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class ButtonCategory(str, Enum):
    """Category of button pressed."""

    ACTION = "action"  # BUY, SELL, SIDEBET
    BET_ADJUST = "bet_adjust"  # X, +0.001, +0.01, +0.1, +1, 1/2, X2, MAX
    PERCENTAGE = "percentage"  # 10%, 25%, 50%, 100%


class TradeOutcome(str, Enum):
    """Outcome of a trade position."""

    PENDING = "pending"  # Trade in progress, not yet resolved
    PROFIT = "profit"  # Closed with profit
    LOSS = "loss"  # Closed with loss
    LIQUIDATED = "liquidated"  # Position active during rug → total loss
    BREAK_EVEN = "break_even"  # Closed at entry price


class SidebetOutcome(str, Enum):
    """Outcome of a sidebet."""

    PENDING = "pending"  # Sidebet placed, not yet resolved
    WON = "won"  # Game rugged → 5X payout (400% net profit)
    LOST = "lost"  # Game didn't rug → lost sidebet amount


# Mapping from UI button text to (button_id, category)
BUTTON_ID_MAP: dict[str, tuple[str, str]] = {
    # Action buttons
    "BUY": ("BUY", "action"),
    "SELL": ("SELL", "action"),
    "SIDEBET": ("SIDEBET", "action"),
    # Bet adjustment buttons
    "X": ("CLEAR", "bet_adjust"),
    "+0.001": ("INC_001", "bet_adjust"),
    "+0.01": ("INC_01", "bet_adjust"),
    "+0.1": ("INC_10", "bet_adjust"),
    "+1": ("INC_1", "bet_adjust"),
    "1/2": ("HALF", "bet_adjust"),
    "X2": ("DOUBLE", "bet_adjust"),
    "MAX": ("MAX", "bet_adjust"),
    # Percentage buttons
    "10%": ("SELL_10", "percentage"),
    "25%": ("SELL_25", "percentage"),
    "50%": ("SELL_50", "percentage"),
    "100%": ("SELL_100", "percentage"),
}


@dataclass
class ButtonEvent:
    """
    Record of a single button press with full game context.

    This is the atomic unit of human gameplay recording.
    Captures the exact state at the moment the button was pressed.
    """

    # === TIMESTAMP ===
    ts: datetime  # When button was pressed (client time, UTC)
    server_ts: Optional[int]  # Server timestamp if confirmed (ms since epoch)

    # === BUTTON IDENTITY ===
    button_id: str  # "BUY", "SELL", "INC_001", etc.
    button_category: ButtonCategory  # action, bet_adjust, percentage

    # === GAME CONTEXT ===
    tick: int  # Current tick when pressed
    price: float  # Current multiplier
    game_phase: int  # 0=cooldown, 1=presale, 2=active, 3=rugged
    game_id: str  # Game identifier

    # === PLAYER STATE (before action) ===
    balance: Decimal  # Available SOL
    position_qty: Decimal  # Position size
    bet_amount: Decimal  # Current bet amount in entry field

    # === DERIVED ===
    ticks_since_last_action: int  # Time since last button press

    # === ACTION SEQUENCE ===
    sequence_id: str  # UUID for grouping related presses
    sequence_position: int  # Position in sequence (0, 1, 2...)

    # === EXECUTION TRACKING (Optional - filled from server response) ===
    # From standard/newTrade broadcast event
    execution_tick: Optional[int] = None  # Actual tick when trade executed
    execution_price: Optional[float] = None  # Actual price at execution
    trade_id: Optional[str] = None  # Links to newTrade broadcast

    # === LATENCY TRACKING ===
    client_timestamp: Optional[int] = None  # When we sent request (ms since epoch)
    latency_ms: Optional[int] = None  # server_ts - client_timestamp

    # === POSITION TIMING (from LiveStateProvider) ===
    time_in_position: int = 0  # current_tick - entry_tick (how long held)

    def to_dict(self) -> dict:
        """Convert to dictionary for storage/serialization."""
        return {
            "ts": self.ts.isoformat() if self.ts else None,
            "server_ts": self.server_ts,
            "button_id": self.button_id,
            "button_category": self.button_category.value
            if isinstance(self.button_category, ButtonCategory)
            else self.button_category,
            "tick": self.tick,
            "price": float(self.price) if self.price else None,
            "game_phase": self.game_phase,
            "game_id": self.game_id,
            "balance": float(self.balance) if self.balance else 0.0,
            "position_qty": float(self.position_qty) if self.position_qty else 0.0,
            "bet_amount": float(self.bet_amount) if self.bet_amount else 0.0,
            "ticks_since_last_action": self.ticks_since_last_action,
            "sequence_id": self.sequence_id,
            "sequence_position": self.sequence_position,
            # Execution tracking
            "execution_tick": self.execution_tick,
            "execution_price": self.execution_price,
            "trade_id": self.trade_id,
            # Latency tracking
            "client_timestamp": self.client_timestamp,
            "latency_ms": self.latency_ms,
            # Position timing
            "time_in_position": self.time_in_position,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ButtonEvent":
        """Create ButtonEvent from dictionary."""
        return cls(
            ts=datetime.fromisoformat(data["ts"]) if data.get("ts") else None,
            server_ts=data.get("server_ts"),
            button_id=data["button_id"],
            button_category=ButtonCategory(data["button_category"]),
            tick=data["tick"],
            price=data["price"],
            game_phase=data["game_phase"],
            game_id=data["game_id"],
            balance=Decimal(str(data.get("balance", 0))),
            position_qty=Decimal(str(data.get("position_qty", 0))),
            bet_amount=Decimal(str(data.get("bet_amount", 0))),
            ticks_since_last_action=data.get("ticks_since_last_action", 0),
            sequence_id=data["sequence_id"],
            sequence_position=data.get("sequence_position", 0),
            # Execution tracking
            execution_tick=data.get("execution_tick"),
            execution_price=data.get("execution_price"),
            trade_id=data.get("trade_id"),
            # Latency tracking
            client_timestamp=data.get("client_timestamp"),
            latency_ms=data.get("latency_ms"),
            # Position timing
            time_in_position=data.get("time_in_position", 0),
        )


@dataclass
class ActionSequence:
    """
    Group of button presses forming a complete action.

    Example: ["+0.01", "+0.01", "BUY"] = build to 0.02, then buy

    An ActionSequence ends when:
    1. An ACTION button is pressed (BUY, SELL, SIDEBET)
    2. A timeout occurs (e.g., 5 seconds of inactivity)
    3. A new game starts

    If the sequence ends without an action button, final_action = "INCOMPLETE"

    Outcome Tracking:
    - Positions active during rug → LIQUIDATED (total loss)
    - Sidebets active during rug → WON (5X payout, 400% net profit)
    """

    # Required fields (no defaults) - must come first
    sequence_id: str
    final_action: str  # "BUY", "SELL", "SIDEBET", or "INCOMPLETE"
    total_duration_ms: int  # Time from first to last press
    success: bool  # Did the action execute?
    executed_price: Optional[float]  # Price at execution
    latency_ms: Optional[int]  # Time to confirmation

    # Optional fields with defaults - must come after required fields
    button_events: list[ButtonEvent] = field(default_factory=list)

    # Trade/Sidebet outcome (filled when position/sidebet resolves)
    trade_outcome: Optional[TradeOutcome] = None
    sidebet_outcome: Optional[SidebetOutcome] = None

    # P&L tracking
    entry_price: Optional[float] = None  # For trades: entry price
    exit_price: Optional[float] = None  # For trades: exit price (or rug price if liquidated)
    pnl_amount: Optional[Decimal] = None  # Realized P&L
    pnl_percent: Optional[float] = None  # Percentage return

    # Rug context
    was_rugged: bool = False  # Did this game end in rug?
    rug_tick: Optional[int] = None  # Tick when rug occurred
    rug_price: Optional[float] = None  # Final price at rug

    def to_dict(self) -> dict:
        """Convert to dictionary for storage/serialization."""
        return {
            "sequence_id": self.sequence_id,
            "button_events": [e.to_dict() for e in self.button_events],
            "final_action": self.final_action,
            "total_duration_ms": self.total_duration_ms,
            "success": self.success,
            "executed_price": self.executed_price,
            "latency_ms": self.latency_ms,
            # Outcomes
            "trade_outcome": self.trade_outcome.value if self.trade_outcome else None,
            "sidebet_outcome": self.sidebet_outcome.value if self.sidebet_outcome else None,
            # P&L
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "pnl_amount": float(self.pnl_amount) if self.pnl_amount else None,
            "pnl_percent": self.pnl_percent,
            # Rug context
            "was_rugged": self.was_rugged,
            "rug_tick": self.rug_tick,
            "rug_price": self.rug_price,
        }

    def mark_liquidated(self, rug_tick: int, rug_price: float, entry_price: float, amount: Decimal) -> None:
        """
        Mark this sequence as a liquidated position (position active during rug).

        Args:
            rug_tick: Tick when rug occurred
            rug_price: Final price at rug (near 0)
            entry_price: Original entry price
            amount: Position size that was liquidated
        """
        self.trade_outcome = TradeOutcome.LIQUIDATED
        self.was_rugged = True
        self.rug_tick = rug_tick
        self.rug_price = rug_price
        self.entry_price = entry_price
        self.exit_price = rug_price
        self.pnl_amount = -amount  # Total loss
        self.pnl_percent = -100.0  # 100% loss

    def mark_sidebet_won(self, rug_tick: int, rug_price: float, bet_amount: Decimal) -> None:
        """
        Mark this sequence as a winning sidebet (sidebet active during rug).

        Sidebets pay 5X on rug = 400% net profit.

        Args:
            rug_tick: Tick when rug occurred
            rug_price: Final price at rug
            bet_amount: Original sidebet amount
        """
        self.sidebet_outcome = SidebetOutcome.WON
        self.was_rugged = True
        self.rug_tick = rug_tick
        self.rug_price = rug_price
        # Sidebet pays 5X, so net profit is 4X the bet
        self.pnl_amount = bet_amount * Decimal("4")  # 5X payout - 1X original = 4X profit
        self.pnl_percent = 400.0  # 400% profit

    def mark_sidebet_lost(self, bet_amount: Decimal) -> None:
        """
        Mark this sequence as a losing sidebet (game didn't rug).

        Args:
            bet_amount: Original sidebet amount that was lost
        """
        self.sidebet_outcome = SidebetOutcome.LOST
        self.was_rugged = False
        self.pnl_amount = -bet_amount
        self.pnl_percent = -100.0


def get_button_info(button_text: str) -> tuple[str, ButtonCategory]:
    """
    Get button_id and category from UI button text.

    Args:
        button_text: Raw text from UI button (e.g., "+0.01", "BUY")

    Returns:
        Tuple of (button_id, ButtonCategory)

    Raises:
        KeyError: If button_text not found in mapping
    """
    button_id, category_str = BUTTON_ID_MAP[button_text]
    return button_id, ButtonCategory(category_str)
