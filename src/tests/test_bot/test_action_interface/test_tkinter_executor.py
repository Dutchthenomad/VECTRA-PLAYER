"""
Tests for TkinterExecutor.

Verifies TkinterExecutor wraps BotUIController correctly.
"""

from decimal import Decimal
from unittest.mock import Mock

import pytest

from bot.action_interface.executors.base import ActionExecutor
from bot.action_interface.executors.tkinter import TkinterExecutor
from bot.action_interface.types import ActionParams
from models.events.player_action import ActionType


@pytest.fixture
def mock_ui_controller():
    """Create mock BotUIController."""
    controller = Mock()
    controller.execute_buy_with_amount = Mock(return_value=True)
    controller.click_sell = Mock(return_value=True)
    controller.execute_sidebet_with_amount = Mock(return_value=True)
    controller.click_increment_button = Mock(return_value=True)
    return controller


@pytest.fixture
def executor(mock_ui_controller):
    """Create TkinterExecutor with mock controller."""
    return TkinterExecutor(ui_controller=mock_ui_controller)


# ============================================================================
# Inheritance & Interface Tests
# ============================================================================


def test_tkinter_executor_is_action_executor(executor):
    """TkinterExecutor is an ActionExecutor subclass."""
    assert isinstance(executor, ActionExecutor)


def test_is_available_returns_true_when_controller_exists(executor):
    """is_available() returns True when ui_controller exists."""
    assert executor.is_available() is True


def test_is_available_returns_false_when_controller_none():
    """is_available() returns False when ui_controller is None."""
    executor = TkinterExecutor(ui_controller=None)
    assert executor.is_available() is False


def test_get_mode_name_returns_tkinter(executor):
    """get_mode_name() returns 'tkinter'."""
    assert executor.get_mode_name() == "tkinter"


# ============================================================================
# BUY Action Tests
# ============================================================================


@pytest.mark.asyncio
async def test_execute_buy_calls_ui_controller(executor, mock_ui_controller):
    """execute() BUY calls execute_buy_with_amount()."""
    params = ActionParams(
        action_type=ActionType.BUY,
        amount=Decimal("0.01"),
    )

    result = await executor.execute(params)

    # Verify UI controller was called correctly
    mock_ui_controller.execute_buy_with_amount.assert_called_once_with(Decimal("0.01"))

    # Verify result
    assert result.success is True
    assert result.action_type == ActionType.BUY
    assert result.executed_amount == Decimal("0.01")
    assert result.error is None


@pytest.mark.asyncio
async def test_execute_buy_without_amount_fails(executor):
    """execute() BUY without amount raises error."""
    params = ActionParams(action_type=ActionType.BUY)

    result = await executor.execute(params)

    assert result.success is False
    assert "amount" in result.error.lower()


# ============================================================================
# SELL Action Tests
# ============================================================================


@pytest.mark.asyncio
async def test_execute_sell_calls_ui_controller(executor, mock_ui_controller):
    """execute() SELL calls click_sell()."""
    params = ActionParams(
        action_type=ActionType.SELL,
        percentage=Decimal("0.5"),
    )

    result = await executor.execute(params)

    # Verify UI controller was called with percentage
    mock_ui_controller.click_sell.assert_called_once_with(percentage=0.5)

    assert result.success is True
    assert result.action_type == ActionType.SELL


@pytest.mark.asyncio
async def test_execute_sell_without_percentage(executor, mock_ui_controller):
    """execute() SELL without percentage calls click_sell(None)."""
    params = ActionParams(action_type=ActionType.SELL)

    result = await executor.execute(params)

    # Verify UI controller was called with None
    mock_ui_controller.click_sell.assert_called_once_with(percentage=None)

    assert result.success is True


# ============================================================================
# SIDEBET Action Tests
# ============================================================================


@pytest.mark.asyncio
async def test_execute_sidebet_calls_ui_controller(executor, mock_ui_controller):
    """execute() SIDEBET calls execute_sidebet_with_amount()."""
    params = ActionParams(
        action_type=ActionType.SIDEBET,
        amount=Decimal("0.005"),
    )

    result = await executor.execute(params)

    mock_ui_controller.execute_sidebet_with_amount.assert_called_once_with(Decimal("0.005"))

    assert result.success is True
    assert result.action_type == ActionType.SIDEBET


@pytest.mark.asyncio
async def test_execute_sidebet_without_amount_fails(executor):
    """execute() SIDEBET without amount raises error."""
    params = ActionParams(action_type=ActionType.SIDEBET)

    result = await executor.execute(params)

    assert result.success is False
    assert "amount" in result.error.lower()


# ============================================================================
# BET_INCREMENT Action Tests
# ============================================================================


@pytest.mark.asyncio
async def test_execute_bet_increment_calls_ui_controller(executor, mock_ui_controller):
    """execute() BET_INCREMENT calls click_increment_button()."""
    params = ActionParams(
        action_type=ActionType.BET_INCREMENT,
        button="+0.01",
    )

    result = await executor.execute(params)

    mock_ui_controller.click_increment_button.assert_called_once_with("+0.01")

    assert result.success is True
    assert result.action_type == ActionType.BET_INCREMENT


@pytest.mark.asyncio
async def test_execute_bet_increment_without_button_fails(executor):
    """execute() BET_INCREMENT without button raises error."""
    params = ActionParams(action_type=ActionType.BET_INCREMENT)

    result = await executor.execute(params)

    assert result.success is False
    assert "button" in result.error.lower()


# ============================================================================
# BET_DECREMENT Action Tests
# ============================================================================


@pytest.mark.asyncio
async def test_execute_bet_decrement_calls_ui_controller(executor, mock_ui_controller):
    """execute() BET_DECREMENT calls click_increment_button()."""
    params = ActionParams(
        action_type=ActionType.BET_DECREMENT,
        button="X",
    )

    result = await executor.execute(params)

    mock_ui_controller.click_increment_button.assert_called_once_with("X")

    assert result.success is True


# ============================================================================
# BET_PERCENTAGE Action Tests
# ============================================================================


@pytest.mark.asyncio
async def test_execute_bet_percentage_calls_ui_controller(executor, mock_ui_controller):
    """execute() BET_PERCENTAGE calls click_increment_button()."""
    params = ActionParams(
        action_type=ActionType.BET_PERCENTAGE,
        button="MAX",
    )

    result = await executor.execute(params)

    mock_ui_controller.click_increment_button.assert_called_once_with("MAX")

    assert result.success is True


# ============================================================================
# ActionResult Tests
# ============================================================================


@pytest.mark.asyncio
async def test_execute_returns_action_result_with_proper_fields(executor):
    """execute() returns ActionResult with all required fields."""
    params = ActionParams(
        action_type=ActionType.BUY,
        amount=Decimal("0.01"),
    )

    result = await executor.execute(params)

    # Verify all required fields present
    assert result.success is True
    assert result.action_id is not None
    assert result.action_type == ActionType.BUY
    assert result.client_ts > 0
    assert result.executed_amount == Decimal("0.01")


@pytest.mark.asyncio
async def test_execute_handles_ui_controller_failure(executor, mock_ui_controller):
    """execute() handles UI controller method returning False."""
    mock_ui_controller.execute_buy_with_amount.return_value = False

    params = ActionParams(
        action_type=ActionType.BUY,
        amount=Decimal("0.01"),
    )

    result = await executor.execute(params)

    assert result.success is False


@pytest.mark.asyncio
async def test_execute_handles_exceptions_gracefully(executor, mock_ui_controller):
    """execute() catches exceptions and returns failed ActionResult."""
    mock_ui_controller.execute_buy_with_amount.side_effect = RuntimeError("UI error")

    params = ActionParams(
        action_type=ActionType.BUY,
        amount=Decimal("0.01"),
    )

    result = await executor.execute(params)

    assert result.success is False
    assert "UI error" in result.error


# ============================================================================
# Animation Flag Tests
# ============================================================================


def test_tkinter_executor_with_animate_true():
    """TkinterExecutor accepts animate=True parameter."""
    controller = Mock()
    executor = TkinterExecutor(ui_controller=controller, animate=True)

    assert executor._animate is True


def test_tkinter_executor_with_animate_false():
    """TkinterExecutor accepts animate=False parameter."""
    controller = Mock()
    executor = TkinterExecutor(ui_controller=controller, animate=False)

    assert executor._animate is False
