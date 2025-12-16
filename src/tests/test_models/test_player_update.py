"""
Tests for PlayerUpdate Pydantic Schema

GitHub Issue: #2
TDD: Tests written FIRST to validate schema design
"""

import pytest
from decimal import Decimal

import sys
sys.path.insert(0, '/home/nomad/Desktop/VECTRA-PLAYER/src')

from models.events.player_update import PlayerUpdate


class TestPlayerUpdateBasic:
    """Test basic PlayerUpdate parsing."""

    def test_minimal_payload(self):
        """Minimum required fields parse successfully."""
        data = {
            "cash": 3.967072345,
        }
        event = PlayerUpdate(**data)

        assert event.cash == Decimal("3.967072345")
        assert event.cumulativePnL == Decimal(0)
        assert event.positionQty == Decimal(0)

    def test_full_payload(self):
        """Complete playerUpdate payload from spec."""
        data = {
            "cash": 3.967072345,
            "cumulativePnL": 0.264879755,
            "positionQty": 0.2222919,
            "avgCost": 1.259605046,
            "totalInvested": 0.251352892,
        }
        event = PlayerUpdate(**data)

        assert event.cash == Decimal("3.967072345")
        assert event.cumulativePnL == Decimal("0.264879755")
        assert event.positionQty == Decimal("0.2222919")
        assert event.avgCost == Decimal("1.259605046")
        assert event.totalInvested == Decimal("0.251352892")


class TestDecimalCoercion:
    """Test float to Decimal conversion."""

    def test_all_fields_coerced(self):
        """All money fields coerced from float to Decimal."""
        data = {
            "cash": 3.967072345,  # Float from server
            "cumulativePnL": 0.264879755,
            "positionQty": 0.2222919,
            "avgCost": 1.259605046,
            "totalInvested": 0.251352892,
        }
        event = PlayerUpdate(**data)

        assert isinstance(event.cash, Decimal)
        assert isinstance(event.cumulativePnL, Decimal)
        assert isinstance(event.positionQty, Decimal)
        assert isinstance(event.avgCost, Decimal)
        assert isinstance(event.totalInvested, Decimal)

    def test_null_values_default_to_zero(self):
        """Null values default to Decimal(0)."""
        data = {
            "cash": 1.0,
            "cumulativePnL": None,
            "positionQty": None,
        }
        event = PlayerUpdate(**data)

        assert event.cumulativePnL == Decimal(0)
        assert event.positionQty == Decimal(0)


class TestHelperMethods:
    """Test PlayerUpdate helper methods and properties."""

    def test_has_position_true(self):
        """has_position returns True when position > 0."""
        event = PlayerUpdate(cash=Decimal("1.0"), positionQty=Decimal("0.001"))
        assert event.has_position is True

    def test_has_position_false(self):
        """has_position returns False when position = 0."""
        event = PlayerUpdate(cash=Decimal("1.0"), positionQty=Decimal("0"))
        assert event.has_position is False

    def test_is_profitable_true(self):
        """is_profitable returns True when PnL > 0."""
        event = PlayerUpdate(cash=Decimal("1.0"), cumulativePnL=Decimal("0.05"))
        assert event.is_profitable is True

    def test_is_profitable_false(self):
        """is_profitable returns False when PnL <= 0."""
        event = PlayerUpdate(cash=Decimal("1.0"), cumulativePnL=Decimal("-0.05"))
        assert event.is_profitable is False

        event_zero = PlayerUpdate(cash=Decimal("1.0"), cumulativePnL=Decimal("0"))
        assert event_zero.is_profitable is False


class TestValidationAgainstLocal:
    """Test the validate_against_local method for drift detection."""

    def test_validation_passes_exact_match(self):
        """Validation passes when local matches server exactly."""
        event = PlayerUpdate(
            cash=Decimal("3.967072345"),
            positionQty=Decimal("0.2222919"),
        )
        result = event.validate_against_local(
            local_balance=Decimal("3.967072345"),
            local_position=Decimal("0.2222919"),
        )

        assert result['valid'] is True
        assert result['balance_drift'] == Decimal(0)
        assert result['position_drift'] == Decimal(0)

    def test_validation_passes_within_tolerance(self):
        """Validation passes when drift is within tolerance."""
        event = PlayerUpdate(
            cash=Decimal("3.967072345"),
            positionQty=Decimal("0.2222919"),
        )
        result = event.validate_against_local(
            local_balance=Decimal("3.9670723"),  # Small drift
            local_position=Decimal("0.2222919"),
            tolerance=Decimal("0.0001"),  # Larger tolerance
        )

        assert result['valid'] is True

    def test_validation_fails_balance_drift(self):
        """Validation fails when balance drift exceeds tolerance."""
        event = PlayerUpdate(
            cash=Decimal("3.967072345"),
            positionQty=Decimal("0.2222919"),
        )
        result = event.validate_against_local(
            local_balance=Decimal("3.5"),  # Significant drift!
            local_position=Decimal("0.2222919"),
        )

        assert result['valid'] is False
        assert result['balance_drift'] > Decimal("0.000001")
        assert result['server_balance'] == Decimal("3.967072345")
        assert result['local_balance'] == Decimal("3.5")

    def test_validation_fails_position_drift(self):
        """Validation fails when position drift exceeds tolerance."""
        event = PlayerUpdate(
            cash=Decimal("3.967072345"),
            positionQty=Decimal("0.5"),  # Server says 0.5
        )
        result = event.validate_against_local(
            local_balance=Decimal("3.967072345"),
            local_position=Decimal("0.3"),  # Local says 0.3 - BUG!
        )

        assert result['valid'] is False
        assert result['position_drift'] == Decimal("0.2")


class TestMetadataFields:
    """Test ingestion metadata fields."""

    def test_metadata_optional(self):
        """Metadata fields are optional (not from socket)."""
        data = {"cash": 1.0}
        event = PlayerUpdate(**data)

        assert event.meta_ts is None
        assert event.meta_seq is None
        assert event.meta_source is None
        assert event.meta_session_id is None
        assert event.meta_game_id is None
        assert event.meta_player_id is None

    def test_metadata_can_be_set(self):
        """Metadata fields can be populated during ingestion."""
        from datetime import datetime

        event = PlayerUpdate(
            cash=Decimal("1.0"),
            meta_ts=datetime.utcnow(),
            meta_seq=42,
            meta_source='cdp',
            meta_session_id='session-123',
            meta_game_id='game-456',
            meta_player_id='did:privy:player789',
        )

        assert event.meta_seq == 42
        assert event.meta_source == 'cdp'
        assert event.meta_game_id == 'game-456'


class TestForwardCompatibility:
    """Test handling of unknown fields."""

    def test_extra_fields_allowed(self):
        """Unknown fields are captured for forward compatibility."""
        data = {
            "cash": 1.0,
            "newServerField": "future_data",
            "anotherField": 12345,
        }
        event = PlayerUpdate(**data)

        # Model should parse without error
        assert event.cash == Decimal("1.0")
        # Extra fields captured
        assert 'newServerField' in event.model_extra
