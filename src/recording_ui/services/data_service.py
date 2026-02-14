"""
Data Service - DuckDB queries for recorded game data.

Queries Parquet files directly without coupling to EventStoreService.
"""

import json
import logging
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

# Default data directory
DATA_DIR = Path.home() / "rugs_data" / "events_parquet"
COMPLETE_GAME_PATH = DATA_DIR / "doc_type=complete_game"

# Whitelist of allowed ORDER BY clauses to prevent SQL injection
ALLOWED_ORDER_BY = frozenset(
    {
        "ts ASC",
        "ts DESC",
        "game_id ASC",
        "game_id DESC",
        "ts",  # DuckDB defaults to ASC
        "game_id",
    }
)


class DataService:
    """Service for querying recorded game data from Parquet files."""

    def __init__(self, data_dir: Path | None = None):
        """Initialize data service.

        Args:
            data_dir: Base directory for Parquet files. Defaults to ~/rugs_data/events_parquet/
        """
        self.data_dir = data_dir or DATA_DIR
        self.complete_game_path = self.data_dir / "doc_type=complete_game"

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get a DuckDB connection."""
        return duckdb.connect()

    def get_stats(self) -> dict[str, Any]:
        """Get overall statistics about recorded data.

        Returns:
            Dictionary with game_count, event_count, storage_mb
        """
        try:
            conn = self.get_connection()

            # Count unique games
            game_count = 0
            if self.complete_game_path.exists():
                result = conn.execute(f"""
                    SELECT COUNT(DISTINCT game_id) as cnt
                    FROM '{self.complete_game_path}/**/*.parquet'
                """).fetchone()
                game_count = result[0] if result else 0

            # Count all events
            event_count = 0
            if self.data_dir.exists():
                result = conn.execute(f"""
                    SELECT COUNT(*) as cnt
                    FROM '{self.data_dir}/**/*.parquet'
                """).fetchone()
                event_count = result[0] if result else 0

            # Calculate storage size
            storage_bytes = 0
            if self.data_dir.exists():
                for f in self.data_dir.rglob("*.parquet"):
                    storage_bytes += f.stat().st_size

            return {
                "game_count": game_count,
                "event_count": event_count,
                "storage_mb": round(storage_bytes / (1024 * 1024), 2),
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "game_count": 0,
                "event_count": 0,
                "storage_mb": 0.0,
            }

    def get_games(
        self, limit: int = 100, offset: int = 0, order_by: str = "ts DESC"
    ) -> list[dict[str, Any]]:
        """Get list of recorded games.

        Args:
            limit: Maximum number of games to return
            offset: Number of games to skip
            order_by: SQL ORDER BY clause (must be in ALLOWED_ORDER_BY whitelist)

        Returns:
            List of game dictionaries with metadata
        """
        try:
            if not self.complete_game_path.exists():
                return []

            # Validate order_by against whitelist to prevent SQL injection
            if order_by not in ALLOWED_ORDER_BY:
                logger.warning(f"Invalid order_by '{order_by}', using default 'ts DESC'")
                order_by = "ts DESC"

            # Validate limit and offset are positive integers
            limit = max(1, min(int(limit), 1000))  # Cap at 1000
            offset = max(0, int(offset))

            conn = self.get_connection()
            result = conn.execute(f"""
                SELECT
                    game_id,
                    ts,
                    raw_json
                FROM '{self.complete_game_path}/**/*.parquet'
                ORDER BY {order_by}
                LIMIT {limit}
                OFFSET {offset}
            """).fetchall()

            games = []
            for row in result:
                game_id, ts, raw_json = row
                try:
                    data = json.loads(raw_json) if raw_json else {}
                except json.JSONDecodeError:
                    data = {}

                games.append(
                    {
                        "game_id": game_id,
                        "timestamp": ts,
                        "peak_multiplier": data.get("peakMultiplier", 0),
                        "tick_count": len(data.get("prices", [])),
                        "sidebet_count": len(data.get("globalSidebets", [])),
                        "rugged": data.get("rugged", False),
                    }
                )

            return games
        except Exception as e:
            logger.error(f"Error getting games: {e}")
            return []

    def get_game(self, game_id: str) -> dict[str, Any] | None:
        """Get a single game by ID.

        Args:
            game_id: The game ID to retrieve

        Returns:
            Game dictionary with full data, or None if not found
        """
        try:
            if not self.complete_game_path.exists():
                return None

            conn = self.get_connection()
            result = conn.execute(
                f"""
                SELECT
                    game_id,
                    ts,
                    raw_json
                FROM '{self.complete_game_path}/**/*.parquet'
                WHERE game_id = ?
                LIMIT 1
            """,
                [game_id],
            ).fetchone()

            if not result:
                return None

            game_id, ts, raw_json = result
            try:
                data = json.loads(raw_json) if raw_json else {}
            except json.JSONDecodeError:
                data = {}

            return {
                "game_id": game_id,
                "timestamp": ts,
                "peak_multiplier": data.get("peakMultiplier", 0),
                "tick_count": len(data.get("prices", [])),
                "sidebet_count": len(data.get("globalSidebets", [])),
                "rugged": data.get("rugged", False),
                "prices": data.get("prices", []),
                "global_sidebets": data.get("globalSidebets", []),
                "provably_fair": data.get("provablyFair", {}),
                "raw_data": data,
            }
        except Exception as e:
            logger.error(f"Error getting game {game_id}: {e}")
            return None

    def get_game_prices(self, game_id: str) -> list[float]:
        """Get price array for a specific game.

        Args:
            game_id: The game ID

        Returns:
            List of price values (multipliers)
        """
        game = self.get_game(game_id)
        if game:
            return game.get("prices", [])
        return []
