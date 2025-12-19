"""
Schema Validation Engine - Phase 0.2

Validates recorded events against Pydantic schemas.

GitHub Issue: #23
Schema Version: 1.0.0

Features:
- Parse JSONL files and validate each event
- Report validation errors with context (file, line, event)
- Skip out-of-scope events silently
- Track unknown events for review
- Batch validation with progress reporting
"""

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from .registry import (
    get_schema_for_event,
    is_out_of_scope,
)


@dataclass
class SchemaValidationError:
    """A single validation error."""

    file_path: str
    line_number: int
    event_name: str
    seq: int | None
    error_type: str  # 'validation', 'json_parse', 'missing_schema'
    error_message: str
    raw_line: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "event_name": self.event_name,
            "seq": self.seq,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


@dataclass
class ValidationResult:
    """Result of validating a recording file or batch."""

    files_processed: int = 0
    events_total: int = 0
    events_validated: int = 0
    events_skipped: int = 0  # Out of scope
    events_unknown: int = 0  # No schema, not out of scope
    errors: list[SchemaValidationError] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        """True if no validation errors."""
        return len(self.errors) == 0

    @property
    def error_count(self) -> int:
        """Number of validation errors."""
        return len(self.errors)

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another result into this one."""
        return ValidationResult(
            files_processed=self.files_processed + other.files_processed,
            events_total=self.events_total + other.events_total,
            events_validated=self.events_validated + other.events_validated,
            events_skipped=self.events_skipped + other.events_skipped,
            events_unknown=self.events_unknown + other.events_unknown,
            errors=self.errors + other.errors,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "files_processed": self.files_processed,
            "events_total": self.events_total,
            "events_validated": self.events_validated,
            "events_skipped": self.events_skipped,
            "events_unknown": self.events_unknown,
            "error_count": self.error_count,
            "is_success": self.is_success,
            "errors": [e.to_dict() for e in self.errors],
        }


class SchemaValidator:
    """
    Validates recorded events against Pydantic schemas.

    Usage:
        validator = SchemaValidator()
        result = validator.validate_file(Path("recording.jsonl"))
        if not result.is_success:
            for error in result.errors:
                print(f"Error: {error.error_message}")
    """

    def __init__(
        self,
        max_errors: int | None = None,
        include_raw_line: bool = False,
    ):
        """
        Initialize the validator.

        Args:
            max_errors: Stop after this many errors (None = no limit)
            include_raw_line: Include raw JSON line in error reports
        """
        self.max_errors = max_errors
        self.include_raw_line = include_raw_line

    def validate_event(
        self,
        event_name: str,
        data: dict,
        file_path: str = "",
        line_number: int = 0,
        seq: int | None = None,
        raw_line: str = "",
    ) -> SchemaValidationError | None:
        """
        Validate a single event against its schema.

        Returns:
            SchemaValidationError if validation fails, None if success or skipped
        """
        schema = get_schema_for_event(event_name)

        if schema is None:
            if is_out_of_scope(event_name):
                return None  # Silently skip out-of-scope events
            # Unknown event - return error for tracking
            return SchemaValidationError(
                file_path=file_path,
                line_number=line_number,
                event_name=event_name,
                seq=seq,
                error_type="missing_schema",
                error_message=f"No schema registered for event: {event_name}",
                raw_line=raw_line if self.include_raw_line else "",
            )

        try:
            schema.model_validate(data)
            return None  # Success
        except ValidationError as e:
            # Format Pydantic validation errors
            error_details = []
            for err in e.errors():
                loc = ".".join(str(x) for x in err["loc"])
                msg = err["msg"]
                error_details.append(f"{loc}: {msg}")

            return SchemaValidationError(
                file_path=file_path,
                line_number=line_number,
                event_name=event_name,
                seq=seq,
                error_type="validation",
                error_message="; ".join(error_details),
                raw_line=raw_line if self.include_raw_line else "",
            )

    def validate_file(self, file_path: Path) -> ValidationResult:
        """
        Validate all events in a JSONL file.

        Expected format: {"seq": int, "ts": str, "event": str, "data": {...}}
        """
        result = ValidationResult(files_processed=1)
        errors = []

        try:
            with open(file_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    result.events_total += 1

                    # Check error limit
                    if self.max_errors and len(errors) >= self.max_errors:
                        break

                    # Parse JSON
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as e:
                        errors.append(
                            SchemaValidationError(
                                file_path=str(file_path),
                                line_number=line_num,
                                event_name="(parse_error)",
                                seq=None,
                                error_type="json_parse",
                                error_message=f"JSON parse error: {e}",
                                raw_line=line if self.include_raw_line else "",
                            )
                        )
                        continue

                    # Extract event info
                    event_name = record.get("event")
                    data = record.get("data", {})
                    seq = record.get("seq")

                    if not event_name:
                        errors.append(
                            SchemaValidationError(
                                file_path=str(file_path),
                                line_number=line_num,
                                event_name="(missing)",
                                seq=seq,
                                error_type="json_parse",
                                error_message="Missing 'event' field in record",
                                raw_line=line if self.include_raw_line else "",
                            )
                        )
                        continue

                    # Check if out of scope
                    if is_out_of_scope(event_name):
                        result.events_skipped += 1
                        continue

                    # Check if has schema
                    if get_schema_for_event(event_name) is None:
                        result.events_unknown += 1
                        # Still record as unknown for tracking
                        errors.append(
                            SchemaValidationError(
                                file_path=str(file_path),
                                line_number=line_num,
                                event_name=event_name,
                                seq=seq,
                                error_type="missing_schema",
                                error_message=f"No schema for event: {event_name}",
                                raw_line=line if self.include_raw_line else "",
                            )
                        )
                        continue

                    # Validate
                    result.events_validated += 1
                    error = self.validate_event(
                        event_name=event_name,
                        data=data,
                        file_path=str(file_path),
                        line_number=line_num,
                        seq=seq,
                        raw_line=line,
                    )
                    if error:
                        errors.append(error)

        except Exception as e:
            errors.append(
                SchemaValidationError(
                    file_path=str(file_path),
                    line_number=0,
                    event_name="(file_error)",
                    seq=None,
                    error_type="file_error",
                    error_message=f"Error reading file: {e}",
                )
            )

        result.errors = errors
        return result

    def validate_directory(
        self,
        directory: Path,
        recursive: bool = True,
        progress_callback: Callable | None = None,
    ) -> ValidationResult:
        """
        Validate all JSONL files in a directory.

        Args:
            directory: Directory to scan
            recursive: Search subdirectories
            progress_callback: Called with (current_file, file_number, total_files)
        """
        pattern = "**/*.jsonl" if recursive else "*.jsonl"
        files = list(directory.glob(pattern))

        total_result = ValidationResult()

        for i, file_path in enumerate(files):
            if progress_callback:
                progress_callback(file_path, i + 1, len(files))

            file_result = self.validate_file(file_path)
            total_result = total_result.merge(file_result)

            # Check error limit
            if self.max_errors and total_result.error_count >= self.max_errors:
                break

        return total_result

    def iter_errors(self, file_path: Path) -> Iterator[SchemaValidationError]:
        """
        Iterate over validation errors in a file.

        Useful for streaming validation of large files.
        """
        result = self.validate_file(file_path)
        yield from result.errors
