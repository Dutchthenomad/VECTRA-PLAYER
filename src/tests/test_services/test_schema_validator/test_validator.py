"""
Tests for Schema Validation Engine - Issue #23 Phase 0.2

Tests the validation engine functionality.
"""

import json
import tempfile
from pathlib import Path

from services.schema_validator.validator import (
    SchemaValidationError,
    SchemaValidator,
    ValidationResult,
)


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_default_values(self):
        """Should have correct defaults."""
        result = ValidationResult()
        assert result.files_processed == 0
        assert result.events_total == 0
        assert result.events_validated == 0
        assert result.events_skipped == 0
        assert result.events_unknown == 0
        assert result.errors == []

    def test_is_success_with_no_errors(self):
        """is_success should be True when no errors."""
        result = ValidationResult()
        assert result.is_success is True

    def test_is_success_with_errors(self):
        """is_success should be False when errors exist."""
        error = SchemaValidationError(
            file_path="test.jsonl",
            line_number=1,
            event_name="test",
            seq=1,
            error_type="validation",
            error_message="Test error",
        )
        result = ValidationResult(errors=[error])
        assert result.is_success is False

    def test_error_count(self):
        """error_count should return number of errors."""
        error = SchemaValidationError(
            file_path="test.jsonl",
            line_number=1,
            event_name="test",
            seq=1,
            error_type="validation",
            error_message="Test error",
        )
        result = ValidationResult(errors=[error, error, error])
        assert result.error_count == 3

    def test_merge(self):
        """Should merge two results correctly."""
        result1 = ValidationResult(
            files_processed=1,
            events_total=10,
            events_validated=8,
            events_skipped=1,
            events_unknown=1,
        )
        result2 = ValidationResult(
            files_processed=1,
            events_total=20,
            events_validated=15,
            events_skipped=3,
            events_unknown=2,
        )
        merged = result1.merge(result2)

        assert merged.files_processed == 2
        assert merged.events_total == 30
        assert merged.events_validated == 23
        assert merged.events_skipped == 4
        assert merged.events_unknown == 3

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        result = ValidationResult(
            files_processed=1,
            events_total=10,
            events_validated=8,
        )
        d = result.to_dict()

        assert d["files_processed"] == 1
        assert d["events_total"] == 10
        assert d["events_validated"] == 8
        assert d["is_success"] is True
        assert "errors" in d


class TestValidationError:
    """Test SchemaValidationError dataclass."""

    def test_creation(self):
        """Should create with all fields."""
        error = SchemaValidationError(
            file_path="test.jsonl",
            line_number=42,
            event_name="gameStateUpdate",
            seq=100,
            error_type="validation",
            error_message="Field required: active",
        )

        assert error.file_path == "test.jsonl"
        assert error.line_number == 42
        assert error.event_name == "gameStateUpdate"
        assert error.seq == 100
        assert error.error_type == "validation"
        assert "Field required" in error.error_message

    def test_to_dict(self):
        """Should convert to dictionary."""
        error = SchemaValidationError(
            file_path="test.jsonl",
            line_number=1,
            event_name="test",
            seq=1,
            error_type="validation",
            error_message="Test",
        )
        d = error.to_dict()

        assert d["file_path"] == "test.jsonl"
        assert d["line_number"] == 1
        assert d["event_name"] == "test"


class TestSchemaValidator:
    """Test SchemaValidator class."""

    def test_validate_event_success(self):
        """Should return None for valid event."""
        validator = SchemaValidator()

        # Valid gameStatePlayerUpdate
        data = {
            "gameId": "test-game-123",
            "rugpool": {
                "rugpoolAmount": 1.5,
                "threshold": 10,
            },
        }

        error = validator.validate_event("gameStatePlayerUpdate", data)
        assert error is None

    def test_validate_event_out_of_scope(self):
        """Should return None for out-of-scope events."""
        validator = SchemaValidator()

        error = validator.validate_event("newChatMessage", {"message": "test"})
        assert error is None  # Silently skipped

    def test_validate_event_unknown(self):
        """Should return error for unknown events."""
        validator = SchemaValidator()

        error = validator.validate_event("unknownEvent123", {"data": "test"})
        assert error is not None
        assert error.error_type == "missing_schema"

    def test_validate_event_validation_failure(self):
        """Should return error for validation failure."""
        validator = SchemaValidator()

        # Missing required field 'rugpool'
        data = {"gameId": "test-game-123"}

        error = validator.validate_event("gameStatePlayerUpdate", data)
        assert error is not None
        assert error.error_type == "validation"
        assert "rugpool" in error.error_message

    def test_validate_file_basic(self):
        """Should validate a JSONL file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            # Write valid gameStatePlayerUpdate
            event = {
                "seq": 1,
                "ts": "2025-01-01T00:00:00",
                "event": "gameStatePlayerUpdate",
                "data": {
                    "gameId": "test-game",
                    "rugpool": {
                        "rugpoolAmount": 1.0,
                        "threshold": 10,
                    },
                },
            }
            f.write(json.dumps(event) + "\n")
            f.flush()

            validator = SchemaValidator()
            result = validator.validate_file(Path(f.name))

            assert result.files_processed == 1
            assert result.events_total == 1
            assert result.events_validated == 1
            assert result.is_success is True

    def test_validate_file_skips_out_of_scope(self):
        """Should skip out-of-scope events."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            event = {
                "seq": 1,
                "ts": "2025-01-01T00:00:00",
                "event": "newChatMessage",
                "data": {"message": "hello"},
            }
            f.write(json.dumps(event) + "\n")
            f.flush()

            validator = SchemaValidator()
            result = validator.validate_file(Path(f.name))

            assert result.events_total == 1
            assert result.events_skipped == 1
            assert result.events_validated == 0
            assert result.is_success is True

    def test_validate_file_tracks_unknown_events(self):
        """Should track unknown events."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            event = {
                "seq": 1,
                "ts": "2025-01-01T00:00:00",
                "event": "unknownEvent",
                "data": {},
            }
            f.write(json.dumps(event) + "\n")
            f.flush()

            validator = SchemaValidator()
            result = validator.validate_file(Path(f.name))

            assert result.events_unknown == 1
            assert result.error_count == 1

    def test_validate_file_handles_json_errors(self):
        """Should handle malformed JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("not valid json\n")
            f.flush()

            validator = SchemaValidator()
            result = validator.validate_file(Path(f.name))

            assert result.error_count == 1
            assert result.errors[0].error_type == "json_parse"

    def test_max_errors_limit(self):
        """Should stop after max_errors."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            # Write 10 events with unknown type
            for i in range(10):
                event = {
                    "seq": i,
                    "ts": "2025-01-01T00:00:00",
                    "event": "unknownEvent",
                    "data": {},
                }
                f.write(json.dumps(event) + "\n")
            f.flush()

            validator = SchemaValidator(max_errors=3)
            result = validator.validate_file(Path(f.name))

            assert result.error_count == 3


class TestValidatorWithRealData:
    """Integration tests with real event structures."""

    def test_game_state_update_cooldown_mode(self):
        """Should validate cooldown-mode gameStateUpdate."""
        validator = SchemaValidator()

        # Cooldown state - missing active/rugged/price/tickCount
        data = {
            "gameId": "test-game",
            "cooldownTimer": 500,
            "cooldownPaused": False,
            "allowPreRoundBuys": True,
            "leaderboard": [],
            "connectedPlayers": 100,
            "provablyFair": {
                "serverSeedHash": "abc123",
                "version": "v3",
            },
        }

        error = validator.validate_event("gameStateUpdate", data)
        assert error is None  # Should pass with defaults

    def test_game_state_player_update(self):
        """Should validate gameStatePlayerUpdate."""
        validator = SchemaValidator()

        data = {
            "gameId": "test-game",
            "rugpool": {
                "rugpoolAmount": 2.5,
                "threshold": 10,
                "instarugCount": 3,
                "totalEntries": 1000,
                "playersWithEntries": 50,
                "solPerEntry": 0.001,
                "maxEntriesPerPlayer": 5000,
                "playerEntries": [
                    {
                        "playerId": "did:privy:test123",
                        "entries": 100,
                        "username": "TestUser",
                        "percentage": 10.0,
                    }
                ],
            },
        }

        error = validator.validate_event("gameStatePlayerUpdate", data)
        assert error is None
