#!/usr/bin/env python3
"""Export Parquet data to JSONL for backwards compatibility."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import duckdb


def get_data_dir() -> Path:
    """Get the data directory from environment or default location"""
    return Path(os.environ.get("RUGS_DATA_DIR", str(Path.home() / "rugs_data")))


def export_to_jsonl(
    parquet_dir: Path,
    output_dir: Path,
    session_id: str | None = None,
    doc_type: str | None = None,
) -> list[Path]:
    """
    Export Parquet data to JSONL format.

    Args:
        parquet_dir: Directory containing Parquet files
        output_dir: Output directory for JSONL files
        session_id: Optional session ID filter
        doc_type: Optional doc_type filter

    Returns:
        List of created JSONL file paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect()

    # Build WHERE clause with parameterized queries to prevent SQL injection
    conditions = []
    params = {}
    if session_id:
        conditions.append("session_id = $session_id")
        params["session_id"] = session_id
    if doc_type:
        conditions.append("doc_type = $doc_type")
        params["doc_type"] = doc_type
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Query Parquet files
    parquet_path = str(parquet_dir / "**" / "*.parquet")
    query = f"""
        SELECT * FROM read_parquet('{parquet_path}', hive_partitioning=true, union_by_name=true)
        {where_clause}
        ORDER BY ts
    """

    try:
        result = conn.execute(query, params).df()
    except Exception as e:
        print(f"Error querying Parquet: {e}", file=sys.stderr)
        return []
    finally:
        conn.close()

    if len(result) == 0:
        print("No events found to export")
        return []

    # Group by doc_type and export
    created_files = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for dt in result["doc_type"].unique():
        subset = result[result["doc_type"] == dt]
        filename = f"{timestamp}_{dt}.jsonl"
        filepath = output_dir / filename

        with open(filepath, "w") as f:
            for _, row in subset.iterrows():
                record = row.to_dict()
                # Convert timestamp to string
                if "ts" in record:
                    record["ts"] = str(record["ts"])
                # Remove None values for cleaner output
                record = {k: v for k, v in record.items() if v is not None}
                f.write(json.dumps(record, default=str) + "\n")

        print(f"Exported {len(subset)} events to {filepath}")
        created_files.append(filepath)

    return created_files


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description="Export Parquet to JSONL for backwards compatibility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export all events
  %(prog)s --output /tmp/exports

  # Export specific session
  %(prog)s --output /tmp/exports --session abc123-def456-789

  # Export specific doc_type
  %(prog)s --output /tmp/exports --doc-type game_tick

  # Export session + doc_type
  %(prog)s --output /tmp/exports --session abc123 --doc-type ws_event
        """,
    )

    parser.add_argument("--output", "-o", required=True, help="Output directory for JSONL files")
    parser.add_argument("--session", help="Session ID to export (optional filter)")
    parser.add_argument("--doc-type", help="Document type to export (optional filter)")
    parser.add_argument(
        "--data-dir", help="Data directory (default: RUGS_DATA_DIR env or ~/rugs_data)"
    )

    args = parser.parse_args()

    # Get data directory
    data_dir = Path(args.data_dir) if args.data_dir else get_data_dir()
    parquet_dir = data_dir / "events_parquet"

    if not parquet_dir.exists():
        print(f"Error: Parquet directory not found: {parquet_dir}", file=sys.stderr)
        sys.exit(1)

    # Export to JSONL
    files = export_to_jsonl(parquet_dir, Path(args.output), args.session, args.doc_type)

    if files:
        print(f"\nExported {len(files)} file(s) to {args.output}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
