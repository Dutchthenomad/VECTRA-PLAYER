#!/usr/bin/env python3
"""
Migrate existing game data from various sources into rugs-feed database.

Sources:
1. Parquet files: ~/rugs_data/events_parquet/doc_type=complete_game/
2. PRNG games.json: ~/Desktop/VECTRA-PLAYER/src/rugs_recordings/PRNG CRAK/explorer_v2/data/games.json
3. games_dataset.jsonl: ~/Desktop/VECTRA-PLAYER/src/rugs_recordings/PRNG CRAK/games_dataset.jsonl

Run from services/rugs-feed directory:
    python scripts/migrate_existing_data.py
"""

import argparse
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Default paths
DEFAULT_DB_PATH = Path("./data/rugs_feed.db")
PARQUET_PATH = Path.home() / "rugs_data/events_parquet/doc_type=complete_game"
PRNG_GAMES_JSON = (
    Path.home() / "Desktop/VECTRA-PLAYER/src/rugs_recordings/PRNG CRAK/explorer_v2/data/games.json"
)
PRNG_GAMES_JSONL = (
    Path.home() / "Desktop/VECTRA-PLAYER/src/rugs_recordings/PRNG CRAK/games_dataset.jsonl"
)


def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize database connection and ensure tables exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))

    # Create game_history table if not exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS game_history (
            game_id TEXT PRIMARY KEY,
            timestamp_ms INTEGER NOT NULL,
            peak_multiplier REAL NOT NULL,
            rugged INTEGER NOT NULL,
            server_seed TEXT,
            server_seed_hash TEXT,
            global_trades TEXT,
            global_sidebets TEXT,
            game_version TEXT,
            captured_at TEXT NOT NULL,
            prices TEXT,
            source TEXT DEFAULT 'live'
        )
    """)

    # Add prices column if it doesn't exist (for older databases)
    try:
        conn.execute("ALTER TABLE game_history ADD COLUMN prices TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Add source column if it doesn't exist
    try:
        conn.execute("ALTER TABLE game_history ADD COLUMN source TEXT DEFAULT 'live'")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    return conn


def migrate_parquet(conn: sqlite3.Connection, dry_run: bool = False) -> dict:
    """Migrate games from parquet files using DuckDB."""
    stats = {"found": 0, "inserted": 0, "skipped": 0, "errors": 0}

    if not PARQUET_PATH.exists():
        logger.warning(f"Parquet path not found: {PARQUET_PATH}")
        return stats

    try:
        import duckdb
    except ImportError:
        logger.error("DuckDB not installed. Run: pip install duckdb")
        return stats

    logger.info(f"Loading parquet files from {PARQUET_PATH}")

    ddb = duckdb.connect()

    # Query unique games from parquet
    query = f"""
        SELECT DISTINCT game_id, raw_json
        FROM '{PARQUET_PATH}/**/*.parquet'
        WHERE raw_json IS NOT NULL
    """

    result = ddb.execute(query).fetchall()
    stats["found"] = len(result)
    logger.info(f"Found {len(result)} unique games in parquet")

    for game_id, raw_json in result:
        try:
            data = json.loads(raw_json)

            # Extract provablyFair
            pf = data.get("provablyFair", {})

            record = {
                "game_id": data.get("id", game_id),
                "timestamp_ms": data.get("timestamp", 0),
                "peak_multiplier": data.get("peakMultiplier", 0.0),
                "rugged": 1 if data.get("rugged") else 0,
                "server_seed": pf.get("serverSeed"),
                "server_seed_hash": pf.get("serverSeedHash"),
                "global_trades": json.dumps(data.get("globalTrades", [])),
                "global_sidebets": json.dumps(data.get("globalSidebets", [])),
                "game_version": data.get("gameVersion"),
                "captured_at": datetime.utcnow().isoformat(),
                "prices": json.dumps(data.get("prices", [])),
                "source": "parquet_migration",
            }

            if dry_run:
                stats["inserted"] += 1
                continue

            # Insert or ignore (skip duplicates)
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO game_history
                    (game_id, timestamp_ms, peak_multiplier, rugged, server_seed,
                     server_seed_hash, global_trades, global_sidebets, game_version,
                     captured_at, prices, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        record["game_id"],
                        record["timestamp_ms"],
                        record["peak_multiplier"],
                        record["rugged"],
                        record["server_seed"],
                        record["server_seed_hash"],
                        record["global_trades"],
                        record["global_sidebets"],
                        record["game_version"],
                        record["captured_at"],
                        record["prices"],
                        record["source"],
                    ),
                )

                if conn.total_changes > 0:
                    stats["inserted"] += 1
                else:
                    stats["skipped"] += 1
            except sqlite3.Error as e:
                logger.error(f"Insert error for {game_id}: {e}")
                stats["errors"] += 1

        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error for {game_id}: {e}")
            stats["errors"] += 1

    if not dry_run:
        conn.commit()

    return stats


def migrate_prng_json(conn: sqlite3.Connection, dry_run: bool = False) -> dict:
    """Migrate games from PRNG games.json."""
    stats = {"found": 0, "inserted": 0, "skipped": 0, "errors": 0}

    if not PRNG_GAMES_JSON.exists():
        logger.warning(f"PRNG games.json not found: {PRNG_GAMES_JSON}")
        return stats

    logger.info(f"Loading PRNG games from {PRNG_GAMES_JSON}")

    with open(PRNG_GAMES_JSON) as f:
        games = json.load(f)

    stats["found"] = len(games)
    logger.info(f"Found {len(games)} games in PRNG games.json")

    for game in games:
        try:
            record = {
                "game_id": game.get("game_id"),
                "timestamp_ms": game.get("timestamp_ms", 0),
                "peak_multiplier": game.get("peak_multiplier", 0.0),
                "rugged": 1 if game.get("rugged") else 0,
                "server_seed": game.get("server_seed"),
                "server_seed_hash": game.get("server_seed_hash"),
                "global_trades": "[]",
                "global_sidebets": "[]",
                "game_version": None,
                "captured_at": datetime.utcnow().isoformat(),
                "prices": "[]",  # Not available in this format
                "source": "prng_migration",
            }

            if not record["game_id"]:
                continue

            if dry_run:
                stats["inserted"] += 1
                continue

            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO game_history
                    (game_id, timestamp_ms, peak_multiplier, rugged, server_seed,
                     server_seed_hash, global_trades, global_sidebets, game_version,
                     captured_at, prices, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        record["game_id"],
                        record["timestamp_ms"],
                        record["peak_multiplier"],
                        record["rugged"],
                        record["server_seed"],
                        record["server_seed_hash"],
                        record["global_trades"],
                        record["global_sidebets"],
                        record["game_version"],
                        record["captured_at"],
                        record["prices"],
                        record["source"],
                    ),
                )

                if conn.total_changes > 0:
                    stats["inserted"] += 1
                else:
                    stats["skipped"] += 1
            except sqlite3.Error as e:
                logger.error(f"Insert error for {record['game_id']}: {e}")
                stats["errors"] += 1

        except Exception as e:
            logger.warning(f"Error processing game: {e}")
            stats["errors"] += 1

    if not dry_run:
        conn.commit()

    return stats


def migrate_prng_jsonl(conn: sqlite3.Connection, dry_run: bool = False) -> dict:
    """Migrate games from PRNG games_dataset.jsonl."""
    stats = {"found": 0, "inserted": 0, "skipped": 0, "errors": 0}

    if not PRNG_GAMES_JSONL.exists():
        logger.warning(f"PRNG games_dataset.jsonl not found: {PRNG_GAMES_JSONL}")
        return stats

    logger.info(f"Loading PRNG games from {PRNG_GAMES_JSONL}")

    with open(PRNG_GAMES_JSONL) as f:
        for line in f:
            stats["found"] += 1
            line = line.strip()
            if not line:
                continue

            try:
                game = json.loads(line)

                record = {
                    "game_id": game.get("game_id"),
                    "timestamp_ms": game.get("timestamp_ms", 0),
                    "peak_multiplier": game.get("peak_multiplier", 0.0),
                    "rugged": 1 if game.get("rugged") else 0,
                    "server_seed": game.get("server_seed"),
                    "server_seed_hash": game.get("server_seed_hash"),
                    "global_trades": "[]",
                    "global_sidebets": "[]",
                    "game_version": None,
                    "captured_at": datetime.utcnow().isoformat(),
                    "prices": "[]",
                    "source": "prng_jsonl_migration",
                }

                if not record["game_id"]:
                    continue

                if dry_run:
                    stats["inserted"] += 1
                    continue

                try:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO game_history
                        (game_id, timestamp_ms, peak_multiplier, rugged, server_seed,
                         server_seed_hash, global_trades, global_sidebets, game_version,
                         captured_at, prices, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            record["game_id"],
                            record["timestamp_ms"],
                            record["peak_multiplier"],
                            record["rugged"],
                            record["server_seed"],
                            record["server_seed_hash"],
                            record["global_trades"],
                            record["global_sidebets"],
                            record["game_version"],
                            record["captured_at"],
                            record["prices"],
                            record["source"],
                        ),
                    )

                    if conn.total_changes > 0:
                        stats["inserted"] += 1
                    else:
                        stats["skipped"] += 1
                except sqlite3.Error as e:
                    logger.error(f"Insert error for {record['game_id']}: {e}")
                    stats["errors"] += 1

            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error: {e}")
                stats["errors"] += 1

    if not dry_run:
        conn.commit()

    logger.info(f"Found {stats['found']} games in PRNG games_dataset.jsonl")
    return stats


def get_db_stats(conn: sqlite3.Connection) -> dict:
    """Get current database statistics."""
    cursor = conn.execute("SELECT COUNT(*) FROM game_history")
    total = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM game_history WHERE server_seed IS NOT NULL")
    with_seeds = cursor.fetchone()[0]

    cursor = conn.execute(
        "SELECT COUNT(*) FROM game_history WHERE prices != '[]' AND prices IS NOT NULL"
    )
    with_prices = cursor.fetchone()[0]

    cursor = conn.execute("SELECT source, COUNT(*) FROM game_history GROUP BY source")
    by_source = dict(cursor.fetchall())

    return {
        "total_games": total,
        "with_seeds": with_seeds,
        "with_prices": with_prices,
        "by_source": by_source,
    }


def main():
    parser = argparse.ArgumentParser(description="Migrate existing game data to rugs-feed database")
    parser.add_argument(
        "--db",
        "-d",
        default=str(DEFAULT_DB_PATH),
        help=f"Database path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )
    parser.add_argument(
        "--source",
        choices=["all", "parquet", "prng_json", "prng_jsonl"],
        default="all",
        help="Which source to migrate from",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    logger.info(f"Database: {db_path}")
    logger.info(f"Dry run: {args.dry_run}")

    # Initialize database
    conn = init_db(db_path)

    # Get initial stats
    initial_stats = get_db_stats(conn)
    logger.info(f"Initial database stats: {initial_stats}")

    # Run migrations
    total_stats = {"found": 0, "inserted": 0, "skipped": 0, "errors": 0}

    if args.source in ("all", "parquet"):
        logger.info("\n=== MIGRATING PARQUET DATA ===")
        stats = migrate_parquet(conn, args.dry_run)
        logger.info(
            f"Parquet: found={stats['found']}, inserted={stats['inserted']}, skipped={stats['skipped']}, errors={stats['errors']}"
        )
        for k in total_stats:
            total_stats[k] += stats[k]

    if args.source in ("all", "prng_json"):
        logger.info("\n=== MIGRATING PRNG GAMES.JSON ===")
        stats = migrate_prng_json(conn, args.dry_run)
        logger.info(
            f"PRNG JSON: found={stats['found']}, inserted={stats['inserted']}, skipped={stats['skipped']}, errors={stats['errors']}"
        )
        for k in total_stats:
            total_stats[k] += stats[k]

    if args.source in ("all", "prng_jsonl"):
        logger.info("\n=== MIGRATING PRNG GAMES_DATASET.JSONL ===")
        stats = migrate_prng_jsonl(conn, args.dry_run)
        logger.info(
            f"PRNG JSONL: found={stats['found']}, inserted={stats['inserted']}, skipped={stats['skipped']}, errors={stats['errors']}"
        )
        for k in total_stats:
            total_stats[k] += stats[k]

    # Get final stats
    final_stats = get_db_stats(conn)

    logger.info("\n" + "=" * 60)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total found:    {total_stats['found']}")
    logger.info(f"Total inserted: {total_stats['inserted']}")
    logger.info(f"Total skipped:  {total_stats['skipped']} (duplicates)")
    logger.info(f"Total errors:   {total_stats['errors']}")
    logger.info("")
    logger.info(f"Database before: {initial_stats['total_games']} games")
    logger.info(f"Database after:  {final_stats['total_games']} games")
    logger.info(f"  With seeds:    {final_stats['with_seeds']}")
    logger.info(f"  With prices:   {final_stats['with_prices']}")
    logger.info(f"  By source:     {final_stats['by_source']}")

    conn.close()


if __name__ == "__main__":
    main()
