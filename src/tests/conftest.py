"""
Shared test fixtures for pytest
"""

import sys
import time
import warnings
from decimal import Decimal
from pathlib import Path

# Add project root to path for scripts imports
# conftest.py -> tests -> src -> project_root
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest

from bot import BotController, BotInterface
from core import GameState, ReplayEngine, TradeManager
from models import GameTick, Position, SideBet
from services import event_bus, setup_logging


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Setup logging for all tests"""
    setup_logging()


@pytest.fixture(autouse=True)
def cleanup_async_tasks():
    """
    Cleanup pending async tasks after each test to prevent warnings.

    HumanActionInterceptor creates fire-and-forget async tasks that may
    not complete before test teardown. This fixture ensures they complete.
    """
    yield
    # Give async tasks time to complete
    time.sleep(0.05)

    # Suppress warnings about pending tasks since we've given them time to complete
    warnings.filterwarnings("ignore", message="coroutine.*was never awaited")
    warnings.filterwarnings("ignore", message="Task was destroyed but it is pending")


@pytest.fixture
def game_state():
    """Create a fresh GameState with default balance"""
    return GameState(Decimal("0.100"))


@pytest.fixture
def trade_manager(game_state):
    """Create TradeManager with GameState"""
    return TradeManager(game_state)


@pytest.fixture
def replay_engine(game_state):
    """Create ReplayEngine with GameState"""
    return ReplayEngine(game_state)


@pytest.fixture
def bot_interface(game_state, trade_manager):
    """Create BotInterface with dependencies"""
    return BotInterface(game_state, trade_manager)


@pytest.fixture
def bot_controller(bot_interface):
    """Create BotController with conservative strategy"""
    return BotController(bot_interface, "conservative")


@pytest.fixture
def sample_tick():
    """Create a sample GameTick for testing"""
    return GameTick.from_dict(
        {
            "game_id": "test-game",
            "tick": 0,
            "timestamp": "2025-11-04T00:00:00",
            "price": 1.0,
            "phase": "ACTIVE",
            "active": True,
            "rugged": False,
            "cooldown_timer": 0,
            "trade_count": 0,
        }
    )


@pytest.fixture
def sample_position():
    """Create a sample Position for testing"""
    return Position(
        entry_price=Decimal("1.0"), amount=Decimal("0.01"), entry_time=1234567890.0, entry_tick=0
    )


@pytest.fixture
def sample_sidebet():
    """Create a sample SideBet for testing"""
    return SideBet(amount=Decimal("0.002"), placed_tick=10, placed_price=Decimal("1.2"))


@pytest.fixture
def loaded_game_state(game_state, sample_tick):
    """GameState with a loaded game"""
    # Set up game state as if a game is loaded
    game_state.update(
        game_id="test-game",
        game_active=True,
        current_tick=0,
        current_price=sample_tick.price,
        current_phase=sample_tick.phase,
    )
    return game_state


@pytest.fixture
def price_series():
    """Create a series of price ticks for testing (10 ticks, rise then fall)"""
    prices = [1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 2.5, 2.0, 1.5, 1.0]
    ticks = []
    for i, price in enumerate(prices):
        tick = GameTick.from_dict(
            {
                "game_id": "test-game",
                "tick": i,
                "timestamp": f"2025-11-04T00:00:{i:02d}",
                "price": price,
                "phase": "ACTIVE",
                "active": True,
                "rugged": False,
                "cooldown_timer": 0,
                "trade_count": i,
            }
        )
        ticks.append(tick)
    return ticks


@pytest.fixture(autouse=True)
def cleanup_event_bus():
    """Clean up event bus after each test"""
    # Start event bus for tests
    if not event_bus._processing:
        event_bus.start()

    yield

    # Clear all subscribers after test
    event_bus.clear_all()
