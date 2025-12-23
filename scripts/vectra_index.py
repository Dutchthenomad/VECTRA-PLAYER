#!/usr/bin/env python3
"""CLI for vector index management.

Usage:
    ./scripts/vectra_index.py build --full       # Full rebuild
    ./scripts/vectra_index.py build --incremental  # Incremental update
    ./scripts/vectra_index.py query "What is playerUpdate?"
    ./scripts/vectra_index.py stats
"""

import argparse
import os
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_dir))

# Add claude-flow to path
claude_flow_rag = Path("/home/nomad/Desktop/claude-flow/rag-pipeline")
sys.path.insert(0, str(claude_flow_rag))


def get_data_dir() -> Path:
    """Get data directory from env or default."""
    return Path(os.getenv("RUGS_DATA_DIR", str(Path.home() / "rugs_data")))


def cmd_build(args):
    """Build or update the vector index."""
    from services.vector_indexer import VectorIndexer

    data_dir = get_data_dir()
    print(f"Data directory: {data_dir}")

    indexer = VectorIndexer(data_dir=data_dir)

    if args.full:
        print("Starting full rebuild...")
        stats = indexer.build_full(batch_size=args.batch_size)
    else:
        print("Starting incremental update...")
        stats = indexer.build_incremental(batch_size=args.batch_size)

    print("\n✓ Done!")
    print(f"  New events: {stats['new_events']}")
    print(f"  Chunks added: {stats['chunks_added']}")


def cmd_query(args):
    """Query the vector index."""
    from retrieval.retrieve import search

    results = search(args.query, top_k=args.top_k)

    if not results:
        print("No results found.")
        return

    print(f"\nTop {len(results)} results for: {args.query}\n")
    print("=" * 60)

    for i, result in enumerate(results, 1):
        print(f"\n[{i}] Score: {result.get('score', 0):.3f}")
        print(f"    Source: {result.get('source', 'N/A')}")
        print(f"    Headers: {', '.join(result.get('headers', []))}")
        print("-" * 40)
        # Show first 300 chars of text
        text = result.get("text", "")
        if len(text) > 300:
            text = text[:300] + "..."
        print(text)


def cmd_stats(args):
    """Show index statistics."""
    from storage.store import get_collection

    from services.vector_indexer import VectorIndexer

    data_dir = get_data_dir()
    indexer = VectorIndexer(data_dir=data_dir)
    checkpoint = indexer.read_checkpoint()

    # Get collection stats
    try:
        collection = get_collection()
        doc_count = collection.count()
    except Exception as e:
        doc_count = f"Error: {e}"

    print("\nChromaDB Index Status")
    print("=" * 40)
    print(f"Data Directory:    {data_dir}")
    print("Collection:        rugs_events")
    print(f"Documents:         {doc_count}")
    print(f"Embedding Model:   {checkpoint.get('embedding_model', 'N/A')}")
    print(f"Schema Version:    {checkpoint.get('schema_version', 'N/A')}")
    print(f"Last Indexed:      {checkpoint.get('last_indexed_ts', 'Never')}")

    # Check parquet files
    parquet_dir = data_dir / "events_parquet"
    if parquet_dir.exists():
        parquet_files = list(parquet_dir.rglob("*.parquet"))
        print(f"Parquet Files:     {len(parquet_files)}")
    else:
        print("Parquet Files:     0 (directory not found)")


def main():
    parser = argparse.ArgumentParser(
        description="VECTRA-PLAYER Vector Index CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s build --full          Full rebuild from Parquet
  %(prog)s build --incremental   Incremental update (default)
  %(prog)s query "playerUpdate"  Search the index
  %(prog)s stats                 Show index statistics
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build or update index")
    build_group = build_parser.add_mutually_exclusive_group()
    build_group.add_argument(
        "--full", action="store_true", help="Full rebuild (delete and recreate)"
    )
    build_group.add_argument(
        "--incremental",
        action="store_true",
        default=True,
        help="Incremental update (default)",
    )
    build_parser.add_argument(
        "--batch-size", type=int, default=1000, help="Batch size for processing"
    )
    build_parser.set_defaults(func=cmd_build)

    # Query command
    query_parser = subparsers.add_parser("query", help="Query the index")
    query_parser.add_argument("query", help="Search query")
    query_parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    query_parser.set_defaults(func=cmd_query)

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show index statistics")
    stats_parser.set_defaults(func=cmd_stats)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
