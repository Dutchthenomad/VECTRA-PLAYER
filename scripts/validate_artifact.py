#!/usr/bin/env python3
"""
Artifact Validation Script - Enforces Foundation Boilerplate compliance.

Validates that:
1. HTML artifacts are in correct locations (src/artifacts/tools/ or templates/)
2. HTML files import required shared resources
3. Python subscribers inherit BaseSubscriber
4. No custom WebSocket code is present

Usage:
    python scripts/validate-artifact.py src/artifacts/tools/my-tool/
    python scripts/validate-artifact.py src/subscribers/my_subscriber.py
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationResult:
    """Result of a validation check."""

    valid: bool
    error: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "valid": self.valid,
            "error": self.error,
            "warnings": self.warnings,
        }


# =============================================================================
# Path Validation
# =============================================================================


def validate_artifact_path(path: Path, project_root: Path) -> ValidationResult:
    """
    Validate that artifact is in an allowed location.

    Allowed locations:
    - src/artifacts/tools/<name>/
    - src/artifacts/templates/

    NOT allowed:
    - src/artifacts/shared/ (IMMUTABLE)
    - Any other location
    """
    try:
        rel_path = path.relative_to(project_root)
    except ValueError:
        return ValidationResult(valid=False, error=f"Path not within project root: {path}")

    parts = rel_path.parts

    # Check for src/artifacts structure
    if len(parts) < 2 or parts[0] != "src" or parts[1] != "artifacts":
        return ValidationResult(
            valid=False,
            error=f"Artifacts must be in src/artifacts/tools/ or src/artifacts/templates/. Got: {rel_path}",
        )

    if len(parts) < 3:
        return ValidationResult(
            valid=False,
            error=f"Artifacts must be in src/artifacts/tools/ or src/artifacts/templates/. Got: {rel_path}",
        )

    subdir = parts[2]

    # Check for immutable shared directory
    if subdir == "shared":
        return ValidationResult(
            valid=False,
            error="src/artifacts/shared/ is IMMUTABLE. Do not add or modify files there.",
        )

    # Check allowed directories
    if subdir not in ("tools", "templates"):
        return ValidationResult(
            valid=False,
            error=f"Artifacts must be in src/artifacts/tools/ or src/artifacts/templates/. Got: {rel_path}",
        )

    return ValidationResult(valid=True)


# =============================================================================
# HTML Import Validation
# =============================================================================


def validate_html_imports(html_file: Path) -> ValidationResult:
    """
    Validate that HTML file imports required shared resources.

    Required:
    - foundation-ws-client.js
    - vectra-styles.css

    Prohibited:
    - Custom WebSocket code (new WebSocket(...))
    """
    content = html_file.read_text()

    errors = []
    warnings = []

    # Check for foundation-ws-client.js
    if "foundation-ws-client.js" not in content:
        errors.append("Missing required import: foundation-ws-client.js")

    # Check for vectra-styles.css
    if "vectra-styles.css" not in content:
        errors.append("Missing required import: vectra-styles.css")

    # Check for custom WebSocket code
    custom_ws_pattern = r"new\s+WebSocket\s*\("
    if re.search(custom_ws_pattern, content):
        errors.append(
            "Custom WebSocket code detected. Use FoundationWSClient from shared/foundation-ws-client.js instead."
        )

    if errors:
        return ValidationResult(valid=False, error="; ".join(errors), warnings=warnings)

    return ValidationResult(valid=True, warnings=warnings)


# =============================================================================
# Python Subscriber Validation
# =============================================================================


def validate_python_subscriber(py_file: Path) -> ValidationResult:
    """
    Validate that Python subscriber follows boilerplate.

    Required:
    - Must import and inherit from BaseSubscriber

    Prohibited:
    - Direct WebSocket connections (websockets.connect)
    """
    content = py_file.read_text()

    errors = []
    warnings = []

    # Check for BaseSubscriber inheritance
    if "BaseSubscriber" not in content:
        errors.append("Subscriber must inherit from BaseSubscriber (from foundation.subscriber)")
    else:
        # Also check that it's actually inherited, not just imported
        inheritance_pattern = r"class\s+\w+\s*\(\s*BaseSubscriber\s*\)"
        if not re.search(inheritance_pattern, content):
            errors.append(
                "Subscriber class must inherit from BaseSubscriber. "
                "Expected: class MySubscriber(BaseSubscriber)"
            )

    # Check for direct WebSocket connections
    direct_ws_patterns = [
        r"websockets\.connect\s*\(",
        r"await\s+websockets\.connect",
        r"WebSocket\s*\(",  # JavaScript-style in Python
    ]

    for pattern in direct_ws_patterns:
        if re.search(pattern, content):
            errors.append(
                "Direct WebSocket connection detected. "
                "Use FoundationClient from foundation.client instead."
            )
            break

    if errors:
        return ValidationResult(valid=False, error="; ".join(errors), warnings=warnings)

    return ValidationResult(valid=True, warnings=warnings)


# =============================================================================
# Full Artifact Validation
# =============================================================================


def validate_artifact(artifact_path: Path, project_root: Path) -> ValidationResult:
    """
    Validate a complete artifact (directory or file).

    For directories:
    - Validates path location
    - Validates all HTML files
    - Checks for README.md

    For Python files:
    - Validates subscriber compliance
    """
    errors = []
    warnings = []

    # Check path
    path_result = validate_artifact_path(artifact_path, project_root)
    if not path_result.valid:
        return path_result

    if artifact_path.is_dir():
        # Validate directory structure
        html_files = list(artifact_path.glob("*.html"))

        # Check for index.html or at least one HTML file
        if html_files:
            for html_file in html_files:
                html_result = validate_html_imports(html_file)
                if not html_result.valid:
                    errors.append(f"{html_file.name}: {html_result.error}")
                warnings.extend(html_result.warnings)

        # Check for README.md in tools
        if "tools" in artifact_path.parts:
            readme = artifact_path / "README.md"
            if not readme.exists():
                errors.append("Missing required README.md file")

    elif artifact_path.suffix == ".py":
        # Validate Python file
        py_result = validate_python_subscriber(artifact_path)
        if not py_result.valid:
            errors.append(py_result.error)
        warnings.extend(py_result.warnings)

    elif artifact_path.suffix == ".html":
        # Validate single HTML file
        html_result = validate_html_imports(artifact_path)
        if not html_result.valid:
            errors.append(html_result.error)
        warnings.extend(html_result.warnings)

    if errors:
        return ValidationResult(valid=False, error="; ".join(errors), warnings=warnings)

    return ValidationResult(valid=True, warnings=warnings)


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Foundation Boilerplate compliance for artifacts"
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to artifact (directory or file) to validate",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root directory (default: auto-detect)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Auto-detect project root if not specified
    if args.project_root is None:
        # Walk up to find pyproject.toml
        current = args.path.resolve()
        while current != current.parent:
            if (current / "pyproject.toml").exists():
                args.project_root = current
                break
            current = current.parent
        else:
            args.project_root = Path.cwd()

    # Validate
    result = validate_artifact(args.path.resolve(), args.project_root)

    if args.json:
        import json

        print(json.dumps(result.to_dict(), indent=2))
    else:
        if result.valid:
            print(f"✓ {args.path}: VALID")
            for warning in result.warnings:
                print(f"  ⚠ {warning}")
            sys.exit(0)
        else:
            print(f"✗ {args.path}: INVALID")
            print(f"  Error: {result.error}")
            for warning in result.warnings:
                print(f"  ⚠ {warning}")
            sys.exit(1)


if __name__ == "__main__":
    main()
