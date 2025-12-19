"""
Schema Validator Module - Phase 0 Schema Validation Tool

GitHub Issue: #23
Schema Version: 1.0.0

Provides:
- Schema registry mapping event names to Pydantic models
- Inventory scanning of recordings
- Validation engine for testing schemas against recorded data
"""

from .registry import SCHEMA_REGISTRY, get_in_scope_events, get_schema_for_event
from .validator import SchemaValidationError, SchemaValidator, ValidationResult

__all__ = [
    "SCHEMA_REGISTRY",
    "get_schema_for_event",
    "get_in_scope_events",
    "SchemaValidationError",
    "SchemaValidator",
    "ValidationResult",
]
