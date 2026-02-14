"""
Tests for HumanActionInterceptor.

Verifies that human button clicks are correctly captured and recorded via
BotActionInterface while preserving original UI handler execution.
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.action_interface.recording.human_interceptor import HumanActionInterceptor
from bot.action_interface.types import ActionParams, ActionResult, ExecutionMode
from models.events.player_action import ActionType


@pytest.fixture
def mock_action_interface():
    """Create a mock BotActionInterface."""
    interface = MagicMock()
    interface.execute = AsyncMock(
        return_value=ActionResult(
            success=True,
            action_id="test-action-id",
            action_type=ActionType.BUY,
            client_ts=1000,
            server_ts=1050,
            confirmed_ts=1100,
        )
    )
    interface.mode = ExecutionMode.RECORDING
    return interface


@pytest.fixture
def interceptor(mock_action_interface):
    """Create HumanActionInterceptor with mock interface."""
    interceptor = HumanActionInterceptor(mock_action_interface)
    yield interceptor
    # Cleanup: ensure async manager is stopped properly
    if interceptor._owns_async_manager and interceptor._async_manager:
        interceptor._async_manager.stop(timeout=2.0)
    # Give any pending tasks time to complete
    import time

    time.sleep(0.05)


class TestHumanActionInterceptorInit:
    """Test HumanActionInterceptor initialization."""

    def test_init_stores_interface(self, mock_action_interface):
        """Test that __init__ stores action_interface."""
        interceptor = HumanActionInterceptor(mock_action_interface)

        assert interceptor._interface is mock_action_interface
        assert interceptor._loop is None  # Lazy initialization

    def test_init_logs_message(self, mock_action_interface, caplog):
        """Test that __init__ logs initialization message."""
        with caplog.at_level("INFO"):
            HumanActionInterceptor(mock_action_interface)

        assert "HumanActionInterceptor initialized" in caplog.text


class TestWrapBuy:
    """Test wrap_buy() method."""

    def test_wrap_buy_creates_correct_action_params(self, interceptor, mock_action_interface):
        """Test that wrap_buy creates ActionParams with BUY type."""
        # Arrange
        original_handler = MagicMock()
        get_amount = MagicMock(return_value=Decimal("10.5"))

        # Act
        wrapped = interceptor.wrap_buy(original_handler, get_amount)
        wrapped()

        # Give async task time to execute
        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.01))

        # Assert - Check that execute was called with correct params
        assert mock_action_interface.execute.call_count == 1
        call_args = mock_action_interface.execute.call_args[0][0]

        assert isinstance(call_args, ActionParams)
        assert call_args.action_type == ActionType.BUY
        assert call_args.amount == Decimal("10.5")
        assert call_args.percentage is None
        assert call_args.button is None

    def test_wrap_buy_calls_original_handler(self, interceptor):
        """Test that wrapped function calls original handler."""
        # Arrange
        original_handler = MagicMock()
        get_amount = MagicMock(return_value=Decimal("5.0"))

        # Act
        wrapped = interceptor.wrap_buy(original_handler, get_amount)
        wrapped()

        # Assert
        original_handler.assert_called_once_with()

    def test_wrap_buy_captures_amount_before_execution(self, interceptor):
        """Test that amount is captured before original handler runs."""
        # Arrange
        amounts = [Decimal("10"), Decimal("20")]
        get_amount = MagicMock(side_effect=amounts)
        original_handler = MagicMock()

        # Act
        wrapped = interceptor.wrap_buy(original_handler, get_amount)
        wrapped()

        # Assert - get_amount should be called exactly once
        assert get_amount.call_count == 1


class TestWrapSell:
    """Test wrap_sell() method."""

    def test_wrap_sell_creates_correct_action_params(self, interceptor, mock_action_interface):
        """Test that wrap_sell creates ActionParams with SELL type."""
        # Arrange
        original_handler = MagicMock()
        get_percentage = MagicMock(return_value=Decimal("0.5"))

        # Act
        wrapped = interceptor.wrap_sell(original_handler, get_percentage)
        wrapped()

        # Give async task time to execute
        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.01))

        # Assert
        assert mock_action_interface.execute.call_count == 1
        call_args = mock_action_interface.execute.call_args[0][0]

        assert isinstance(call_args, ActionParams)
        assert call_args.action_type == ActionType.SELL
        assert call_args.percentage == Decimal("0.5")
        assert call_args.amount is None
        assert call_args.button is None

    def test_wrap_sell_calls_original_handler(self, interceptor):
        """Test that wrapped SELL function calls original handler."""
        # Arrange
        original_handler = MagicMock()
        get_percentage = MagicMock(return_value=Decimal("1.0"))

        # Act
        wrapped = interceptor.wrap_sell(original_handler, get_percentage)
        wrapped()

        # Assert
        original_handler.assert_called_once_with()

    @pytest.mark.parametrize(
        "percentage",
        [Decimal("0.1"), Decimal("0.25"), Decimal("0.5"), Decimal("1.0")],
    )
    def test_wrap_sell_with_different_percentages(
        self, interceptor, mock_action_interface, percentage
    ):
        """Test wrap_sell with various percentage values."""
        # Arrange
        original_handler = MagicMock()
        get_percentage = MagicMock(return_value=percentage)

        # Act
        wrapped = interceptor.wrap_sell(original_handler, get_percentage)
        wrapped()

        # Give async task time to execute
        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.01))

        # Assert
        call_args = mock_action_interface.execute.call_args[0][0]
        assert call_args.percentage == percentage


class TestWrapSidebet:
    """Test wrap_sidebet() method."""

    def test_wrap_sidebet_creates_correct_action_params(self, interceptor, mock_action_interface):
        """Test that wrap_sidebet creates ActionParams with SIDEBET type."""
        # Arrange
        original_handler = MagicMock()
        get_amount = MagicMock(return_value=Decimal("2.5"))

        # Act
        wrapped = interceptor.wrap_sidebet(original_handler, get_amount)
        wrapped()

        # Give async task time to execute
        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.01))

        # Assert
        assert mock_action_interface.execute.call_count == 1
        call_args = mock_action_interface.execute.call_args[0][0]

        assert isinstance(call_args, ActionParams)
        assert call_args.action_type == ActionType.SIDEBET
        assert call_args.amount == Decimal("2.5")
        assert call_args.percentage is None
        assert call_args.button is None

    def test_wrap_sidebet_calls_original_handler(self, interceptor):
        """Test that wrapped SIDEBET function calls original handler."""
        # Arrange
        original_handler = MagicMock()
        get_amount = MagicMock(return_value=Decimal("1.0"))

        # Act
        wrapped = interceptor.wrap_sidebet(original_handler, get_amount)
        wrapped()

        # Assert
        original_handler.assert_called_once_with()


class TestWrapIncrement:
    """Test wrap_increment() method."""

    @pytest.mark.parametrize(
        "button_text",
        ["+0.001", "+0.01", "+0.1", "+1", "X", "1/2", "-0.001", "-0.01"],
    )
    def test_wrap_increment_with_different_buttons(
        self, interceptor, mock_action_interface, button_text
    ):
        """Test wrap_increment with various button texts."""
        # Arrange
        original_handler = MagicMock()

        # Act
        wrapped = interceptor.wrap_increment(original_handler, button_text)
        wrapped()

        # Give async task time to execute
        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.01))

        # Assert
        assert mock_action_interface.execute.call_count == 1
        call_args = mock_action_interface.execute.call_args[0][0]

        assert isinstance(call_args, ActionParams)
        assert call_args.action_type == ActionType.BET_INCREMENT
        assert call_args.button == button_text
        assert call_args.amount is None
        assert call_args.percentage is None

    def test_wrap_increment_calls_original_handler(self, interceptor):
        """Test that wrapped increment function calls original handler."""
        # Arrange
        original_handler = MagicMock()

        # Act
        wrapped = interceptor.wrap_increment(original_handler, "+0.1")
        wrapped()

        # Assert
        original_handler.assert_called_once_with()


class TestWrapPercentage:
    """Test wrap_percentage() method."""

    @pytest.mark.parametrize(
        "percentage",
        [Decimal("0.1"), Decimal("0.25"), Decimal("0.5"), Decimal("1.0")],
    )
    def test_wrap_percentage_with_different_values(
        self, interceptor, mock_action_interface, percentage
    ):
        """Test wrap_percentage with various percentage values."""
        # Arrange
        original_handler = MagicMock()

        # Act
        wrapped = interceptor.wrap_percentage(original_handler, percentage)
        wrapped()

        # Give async task time to execute
        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.01))

        # Assert
        assert mock_action_interface.execute.call_count == 1
        call_args = mock_action_interface.execute.call_args[0][0]

        assert isinstance(call_args, ActionParams)
        assert call_args.action_type == ActionType.BET_PERCENTAGE
        assert call_args.percentage == percentage
        assert call_args.amount is None
        assert call_args.button is None

    def test_wrap_percentage_calls_original_handler(self, interceptor):
        """Test that wrapped percentage function calls original handler."""
        # Arrange
        original_handler = MagicMock()

        # Act
        wrapped = interceptor.wrap_percentage(original_handler, Decimal("0.5"))
        wrapped()

        # Assert
        original_handler.assert_called_once_with()


class TestAsyncRecording:
    """Test async recording behavior."""

    @pytest.mark.asyncio
    async def test_recording_is_scheduled_asynchronously(self, interceptor, mock_action_interface):
        """Test that recording doesn't block UI thread."""
        # Arrange
        original_handler = MagicMock()
        get_amount = MagicMock(return_value=Decimal("5.0"))

        # Mock execute to take some time
        async def slow_execute(params):
            await asyncio.sleep(0.1)
            return ActionResult(
                success=True,
                action_id="test-id",
                action_type=params.action_type,
                client_ts=1000,
            )

        mock_action_interface.execute = AsyncMock(side_effect=slow_execute)

        # Act
        wrapped = interceptor.wrap_buy(original_handler, get_amount)

        # Call wrapped function - should return immediately
        wrapped()

        # Assert - Original handler should be called immediately
        original_handler.assert_called_once()

        # Execute should not be called yet (still pending)
        assert mock_action_interface.execute.call_count == 0

        # Wait for async task
        await asyncio.sleep(0.15)

        # Now execute should have been called
        assert mock_action_interface.execute.call_count == 1

    def test_exception_in_execute_does_not_crash(self, interceptor, mock_action_interface, caplog):
        """Test that exceptions during execute are caught and logged."""
        # Arrange
        mock_action_interface.execute = AsyncMock(side_effect=Exception("Test error"))
        original_handler = MagicMock()
        get_amount = MagicMock(return_value=Decimal("5.0"))

        # Act
        wrapped = interceptor.wrap_buy(original_handler, get_amount)

        with caplog.at_level("ERROR"):
            wrapped()
            # Give async task time to execute and fail
            asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.01))

        # Assert - Original handler should still be called
        original_handler.assert_called_once()

        # Error should be logged
        assert "Failed to record action" in caplog.text
        assert "Test error" in caplog.text


class TestEventLoopManagement:
    """Test event loop creation and management."""

    def test_get_event_loop_creates_loop_if_none(self, interceptor):
        """Test that _get_event_loop caches the thread event loop when available."""
        # Arrange - Ensure no loop initially
        interceptor._loop = None

        # Act
        loop = interceptor._get_event_loop()

        # Assert
        assert loop is not None
        assert interceptor._loop is loop

    def test_get_event_loop_reuses_existing_loop(self, interceptor):
        """Test that _get_event_loop reuses existing loop."""
        # Arrange
        loop1 = interceptor._get_event_loop()

        # Act
        loop2 = interceptor._get_event_loop()

        # Assert
        assert loop1 is loop2

    @patch("bot.action_interface.recording.human_interceptor.asyncio.get_event_loop")
    def test_get_event_loop_handles_runtime_error(self, mock_get_loop, interceptor):
        """Test that _get_event_loop returns None when no thread loop exists."""
        # Arrange
        mock_get_loop.side_effect = RuntimeError("No event loop")

        # Act
        loop = interceptor._get_event_loop()

        # Assert
        assert loop is None
        assert interceptor._loop is None


class TestScheduleRecording:
    """Test _schedule_recording() method."""

    def test_schedule_recording_handles_exceptions(self, interceptor, caplog):
        """Test that _schedule_recording catches and logs exceptions."""
        # Arrange
        params = ActionParams(action_type=ActionType.BUY, amount=Decimal("5.0"))

        # Mock _get_event_loop to raise exception
        with (
            patch.object(interceptor, "_get_event_loop", side_effect=Exception("Test error")),
            caplog.at_level("ERROR"),
        ):
            # Act
            interceptor._schedule_recording(params)

        # Assert
        assert "Failed to schedule recording" in caplog.text
        assert "Test error" in caplog.text
