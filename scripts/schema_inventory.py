#!/usr/bin/env python3
"""
Schema Inventory Script - Phase 0.1

Scans recording directories and reports:
1. Event types found in recordings
2. Schema coverage (which events have Pydantic models)
3. Sample counts per event type
4. Unknown events (not in scope or out of scope)

GitHub Issue: #23
Usage: python scripts/schema_inventory.py [--recordings-dir PATH]
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.schema_validator.registry import (
    IN_SCOPE_EVENTS,
    OUT_OF_SCOPE_EVENTS,
    SCHEMA_REGISTRY,
    get_coverage_stats,
)


def scan_jsonl_file(filepath: Path) -> Counter:
    """
    Scan a JSONL file and count event types.

    Expected format: {"seq": int, "ts": str, "event": str, "data": {...}}
    """
    event_counts = Counter()

    try:
        with open(filepath, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                    event_name = record.get("event")
                    if event_name:
                        event_counts[event_name] += 1
                except json.JSONDecodeError:
                    # Skip malformed lines
                    pass

    except Exception as e:
        print(f"  Warning: Error reading {filepath.name}: {e}", file=sys.stderr)

    return event_counts


def scan_directory(recordings_dir: Path, recursive: bool = True) -> tuple[Counter, list[Path]]:
    """
    Scan a directory for JSONL files and count events.

    Returns:
        Tuple of (event_counts, files_scanned)
    """
    total_counts = Counter()
    files_scanned = []

    pattern = "**/*.jsonl" if recursive else "*.jsonl"

    for filepath in recordings_dir.glob(pattern):
        if filepath.is_file():
            files_scanned.append(filepath)
            file_counts = scan_jsonl_file(filepath)
            total_counts.update(file_counts)

    return total_counts, files_scanned


def categorize_events(event_counts: Counter) -> dict:
    """
    Categorize found events into in-scope, out-of-scope, and unknown.
    """
    in_scope_found = {}
    out_of_scope_found = {}
    unknown_found = {}

    for event, count in event_counts.items():
        if event in IN_SCOPE_EVENTS:
            in_scope_found[event] = count
        elif event in OUT_OF_SCOPE_EVENTS:
            out_of_scope_found[event] = count
        else:
            unknown_found[event] = count

    return {
        "in_scope": in_scope_found,
        "out_of_scope": out_of_scope_found,
        "unknown": unknown_found,
    }


def print_report(
    event_counts: Counter,
    files_scanned: list[Path],
    recordings_dir: Path,
) -> None:
    """Print a formatted inventory report."""

    print("\n" + "=" * 70)
    print("SCHEMA INVENTORY REPORT")
    print("=" * 70)

    # Directory info
    print(f"\nSource: {recordings_dir}")
    print(f"Files scanned: {len(files_scanned)}")
    print(f"Total events: {sum(event_counts.values()):,}")

    # Categorize events
    categories = categorize_events(event_counts)

    # Schema coverage
    coverage = get_coverage_stats()
    print("\n--- Schema Coverage ---")
    print(f"In-scope events: {coverage['total_in_scope']}")
    print(f"With schemas: {coverage['covered']}")
    print(f"Missing schemas: {coverage['missing']}")
    print(f"Coverage: {coverage['coverage_pct']:.1f}%")

    if coverage["missing_events"]:
        print("\nMissing schemas for:")
        for event in coverage["missing_events"]:
            print(f"  - {event}")

    # In-scope events found
    print(f"\n--- In-Scope Events Found ({len(categories['in_scope'])}) ---")
    if categories["in_scope"]:
        for event in sorted(categories["in_scope"].keys()):
            count = categories["in_scope"][event]
            has_schema = "Y" if event in SCHEMA_REGISTRY else "N"
            print(f"  [{has_schema}] {event}: {count:,}")
    else:
        print("  (none found)")

    # In-scope events NOT found
    in_scope_not_found = IN_SCOPE_EVENTS - set(categories["in_scope"].keys())
    if in_scope_not_found:
        print(f"\n--- In-Scope Events NOT Found ({len(in_scope_not_found)}) ---")
        for event in sorted(in_scope_not_found):
            has_schema = "Y" if event in SCHEMA_REGISTRY else "N"
            print(f"  [{has_schema}] {event}")

    # Out-of-scope events (silently skipped)
    if categories["out_of_scope"]:
        print(f"\n--- Out-of-Scope Events (skipped) ({len(categories['out_of_scope'])}) ---")
        for event in sorted(categories["out_of_scope"].keys()):
            count = categories["out_of_scope"][event]
            print(f"  {event}: {count:,}")

    # Unknown events
    if categories["unknown"]:
        print(f"\n--- Unknown Events ({len(categories['unknown'])}) ---")
        for event in sorted(categories["unknown"].keys()):
            count = categories["unknown"][event]
            print(f"  ? {event}: {count:,}")

    print("\n" + "=" * 70)
    print("Legend: [Y] = Schema exists, [N] = Schema missing, ? = Unknown event")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Scan recordings and report schema coverage")
    parser.add_argument(
        "--recordings-dir",
        type=Path,
        default=Path("/home/nomad/rugs_recordings"),
        help="Path to recordings directory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of formatted report",
    )
    args = parser.parse_args()

    if not args.recordings_dir.exists():
        print(f"Error: Recordings directory not found: {args.recordings_dir}")
        sys.exit(1)

    print(f"Scanning {args.recordings_dir}...")

    event_counts, files_scanned = scan_directory(args.recordings_dir)

    if args.json:
        # JSON output
        categories = categorize_events(event_counts)
        coverage = get_coverage_stats()
        output = {
            "recordings_dir": str(args.recordings_dir),
            "files_scanned": len(files_scanned),
            "total_events": sum(event_counts.values()),
            "coverage": coverage,
            "events": {
                "in_scope": categories["in_scope"],
                "out_of_scope": categories["out_of_scope"],
                "unknown": categories["unknown"],
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(event_counts, files_scanned, args.recordings_dir)


if __name__ == "__main__":
    main()
