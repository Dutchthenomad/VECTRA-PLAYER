#!/usr/bin/env python3
"""
Query captured session data from Parquet files.

Usage:
    python scripts/query_session.py --session <session_id>
    python scripts/query_session.py --recent 10
    python scripts/query_session.py --stats
"""

import argparse
import os
import sys
from pathlib import Path

import duckdb


def get_data_dir() -> Path:
    """Get the data directory from environment or default location"""
    return Path(os.environ.get("RUGS_DATA_DIR", str(Path.home() / "rugs_data")))


def query_session(session_id: str):
    """
    Query events from a specific session.

    Args:
        session_id: Session UUID to query

    Prints event counts by doc_type for the session.
    """
    data_dir = get_data_dir()
    parquet_dir = data_dir / "events_parquet"

    if not parquet_dir.exists():
        print(f"Error: Parquet directory not found: {parquet_dir}", file=sys.stderr)
        sys.exit(1)

    conn = duckdb.connect()

    # Query events for this session using parameterized query to prevent SQL injection
    # Note: parquet_dir is from environment/config, not user input, so safe to interpolate
    query = f"""
    SELECT
        doc_type,
        COUNT(*) as event_count,
        MIN(ts) as first_event,
        MAX(ts) as last_event
    FROM read_parquet('{parquet_dir}/**/*.parquet', hive_partitioning=true, union_by_name=true)
    WHERE session_id = $session_id
    GROUP BY doc_type
    ORDER BY doc_type
    """

    try:
        result = conn.execute(query, {"session_id": session_id}).fetchall()

        if not result:
            print(f"No events found for session: {session_id}")
            return

        print(f"\nSession: {session_id}")
        print("-" * 80)
        print(f"{'Doc Type':<20} {'Count':>10} {'First Event':<25} {'Last Event':<25}")
        print("-" * 80)

        total = 0
        for row in result:
            doc_type, count, first_ts, last_ts = row
            print(f"{doc_type:<20} {count:>10} {first_ts:<25} {last_ts:<25}")
            total += count

        print("-" * 80)
        print(f"{'TOTAL':<20} {total:>10}")
        print()

    except Exception as e:
        print(f"Error querying session: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def query_recent(limit: int = 10):
    """
    Show most recent events.

    Args:
        limit: Number of recent events to show (default: 10)

    Prints the most recent events with timestamp, doc_type, event_name, and game_id.
    """
    data_dir = get_data_dir()
    parquet_dir = data_dir / "events_parquet"

    if not parquet_dir.exists():
        print(f"Error: Parquet directory not found: {parquet_dir}", file=sys.stderr)
        sys.exit(1)

    conn = duckdb.connect()

    # Use parameterized query for LIMIT to follow best practices
    # Note: parquet_dir is from environment/config, not user input, so safe to interpolate
    query = f"""
    SELECT
        ts,
        doc_type,
        event_name,
        game_id,
        session_id
    FROM read_parquet('{parquet_dir}/**/*.parquet', hive_partitioning=true, union_by_name=true)
    ORDER BY ts DESC
    LIMIT $limit
    """

    try:
        result = conn.execute(query, {"limit": limit}).fetchall()

        if not result:
            print("No events found")
            return

        print(f"\nMost Recent {limit} Events")
        print("-" * 100)
        print(
            f"{'Timestamp':<25} {'Doc Type':<20} {'Event Name':<20} {'Game ID':<20} {'Session ID':<36}"
        )
        print("-" * 100)

        for row in result:
            ts, doc_type, event_name, game_id, session_id = row
            event_name_display = event_name or "N/A"
            game_id_display = game_id or "N/A"
            print(
                f"{ts:<25} {doc_type:<20} {event_name_display:<20} {game_id_display:<20} {session_id:<36}"
            )

        print()

    except Exception as e:
        print(f"Error querying recent events: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def query_stats():
    """
    Show capture statistics.

    Prints:
    - Total event count
    - Number of unique sessions
    - Date range (first and last event)
    - Event counts by doc_type
    """
    data_dir = get_data_dir()
    parquet_dir = data_dir / "events_parquet"

    if not parquet_dir.exists():
        print(f"Error: Parquet directory not found: {parquet_dir}", file=sys.stderr)
        sys.exit(1)

    conn = duckdb.connect()

    # Overall statistics
    # Note: parquet_dir is from environment/config, not user input, so safe to interpolate
    stats_query = f"""
    SELECT
        COUNT(*) as total_events,
        COUNT(DISTINCT session_id) as total_sessions,
        MIN(ts) as first_event,
        MAX(ts) as last_event
    FROM read_parquet('{parquet_dir}/**/*.parquet', hive_partitioning=true, union_by_name=true)
    """

    # Events by doc_type
    doc_type_query = f"""
    SELECT
        doc_type,
        COUNT(*) as event_count,
        COUNT(DISTINCT session_id) as session_count
    FROM read_parquet('{parquet_dir}/**/*.parquet', hive_partitioning=true, union_by_name=true)
    GROUP BY doc_type
    ORDER BY doc_type
    """

    try:
        # Get overall stats
        stats = conn.execute(stats_query).fetchone()
        total_events, total_sessions, first_event, last_event = stats

        print("\n" + "=" * 80)
        print("CAPTURE STATISTICS")
        print("=" * 80)
        print(f"Total Events:    {total_events:,}")
        print(f"Total Sessions:  {total_sessions:,}")
        print(f"Date Range:      {first_event} to {last_event}")
        print()

        # Get doc_type breakdown
        doc_types = conn.execute(doc_type_query).fetchall()

        print("Events by Document Type:")
        print("-" * 80)
        print(f"{'Doc Type':<20} {'Event Count':>15} {'Session Count':>15}")
        print("-" * 80)

        for row in doc_types:
            doc_type, event_count, session_count = row
            print(f"{doc_type:<20} {event_count:>15,} {session_count:>15,}")

        print("=" * 80)
        print()

    except Exception as e:
        print(f"Error querying statistics: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description="Query captured session data from Parquet files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show statistics
  %(prog)s --stats

  # Show 20 most recent events
  %(prog)s --recent 20

  # Query specific session
  %(prog)s --session abc123-def456-789
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--session", type=str, metavar="SESSION_ID", help="Query events from a specific session"
    )
    group.add_argument(
        "--recent",
        type=int,
        metavar="N",
        nargs="?",
        const=10,
        help="Show N most recent events (default: 10)",
    )
    group.add_argument("--stats", action="store_true", help="Show capture statistics")

    args = parser.parse_args()

    # Execute the appropriate query
    if args.session:
        query_session(args.session)
    elif args.recent is not None:
        query_recent(args.recent)
    elif args.stats:
        query_stats()


if __name__ == "__main__":
    main()
