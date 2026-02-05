"""
EventStorage - SQLite storage for captured WebSocket events.

Stores:
- Raw events with timestamps
- Game summaries with seed reveals
- Export format for PRNG attack suite
"""

import json
import logging
from pathlib import Path
from typing import Any

import aiosqlite

from .client import CapturedEvent

logger = logging.getLogger(__name__)


class EventStorage:
    """
    SQLite storage for WebSocket events.

    Tables:
    - games: Game summaries with final state and seed
    - events: Raw event log for replay/analysis
    """

    def __init__(self, db_path: str):
        """
        Initialize storage.

        Args:
            db_path: Path to SQLite database file
        """
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

        # Ensure parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize database connection and create tables."""
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row

        # Create tables
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                first_seen_at TEXT NOT NULL,
                last_updated_at TEXT NOT NULL,
                rugged INTEGER DEFAULT 0,
                final_price REAL,
                tick_count INTEGER,
                server_seed TEXT,
                server_seed_hash TEXT,
                peak_multiplier REAL,
                timestamp_ms INTEGER
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                game_id TEXT,
                timestamp TEXT NOT NULL,
                timestamp_ms INTEGER,
                data TEXT NOT NULL,
                FOREIGN KEY (game_id) REFERENCES games(game_id)
            );

            CREATE INDEX IF NOT EXISTS idx_events_game_id ON events(game_id);
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_games_rugged ON games(rugged);
            CREATE INDEX IF NOT EXISTS idx_games_server_seed ON games(server_seed);
        """)
        await self._db.commit()
        logger.info(f"Database initialized: {self._db_path}")

    async def close(self) -> None:
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def store_event(self, event: CapturedEvent) -> None:
        """
        Store a captured event.

        Args:
            event: CapturedEvent to store
        """
        if not self._db:
            raise RuntimeError("Database not initialized")

        timestamp_str = event.timestamp.isoformat()
        timestamp_ms = int(event.timestamp.timestamp() * 1000)
        data_json = json.dumps(event.data)

        # Store raw event
        await self._db.execute(
            """
            INSERT INTO events (event_type, game_id, timestamp, timestamp_ms, data)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event.event_type, event.game_id, timestamp_str, timestamp_ms, data_json),
        )

        # Update game record for gameStateUpdate events
        if event.event_type == "gameStateUpdate" and event.game_id:
            await self._update_game_record(event)

        await self._db.commit()

    async def _update_game_record(self, event: CapturedEvent) -> None:
        """Update or create game record from gameStateUpdate."""
        data = event.data
        game_id = event.game_id
        timestamp_str = event.timestamp.isoformat()
        timestamp_ms = int(event.timestamp.timestamp() * 1000)

        rugged = 1 if data.get("rugged") else 0
        price = data.get("price")
        tick_count = data.get("tickCount")

        # Extract provably fair data
        pf = data.get("provablyFair", {})
        server_seed = pf.get("serverSeed")
        server_seed_hash = pf.get("serverSeedHash")

        # Check if game exists
        cursor = await self._db.execute(
            "SELECT game_id, peak_multiplier FROM games WHERE game_id = ?",
            (game_id,),
        )
        existing = await cursor.fetchone()

        if existing:
            # Update existing game
            peak = max(existing["peak_multiplier"] or 1.0, price or 1.0)

            await self._db.execute(
                """
                UPDATE games SET
                    last_updated_at = ?,
                    rugged = ?,
                    final_price = ?,
                    tick_count = ?,
                    server_seed = COALESCE(?, server_seed),
                    server_seed_hash = COALESCE(?, server_seed_hash),
                    peak_multiplier = ?,
                    timestamp_ms = ?
                WHERE game_id = ?
                """,
                (
                    timestamp_str,
                    rugged,
                    price,
                    tick_count,
                    server_seed,
                    server_seed_hash,
                    peak,
                    timestamp_ms,
                    game_id,
                ),
            )
        else:
            # Insert new game
            await self._db.execute(
                """
                INSERT INTO games (
                    game_id, first_seen_at, last_updated_at, rugged,
                    final_price, tick_count, server_seed, server_seed_hash,
                    peak_multiplier, timestamp_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    timestamp_str,
                    timestamp_str,
                    rugged,
                    price,
                    tick_count,
                    server_seed,
                    server_seed_hash,
                    price or 1.0,
                    timestamp_ms,
                ),
            )

    async def get_recent_games(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get most recent games.

        Args:
            limit: Maximum number of games to return

        Returns:
            List of game dicts
        """
        if not self._db:
            return []

        cursor = await self._db.execute(
            """
            SELECT * FROM games
            ORDER BY last_updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_seed_reveals(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get games with revealed server seeds.

        Args:
            limit: Maximum number of games to return

        Returns:
            List of games with server_seed present
        """
        if not self._db:
            return []

        cursor = await self._db.execute(
            """
            SELECT * FROM games
            WHERE server_seed IS NOT NULL
            ORDER BY last_updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def export_for_prng(self) -> list[dict[str, Any]]:
        """
        Export data in format suitable for PRNG attack suite.

        Returns:
            List of dicts with game_id, server_seed, timestamp_ms, etc.
        """
        if not self._db:
            return []

        cursor = await self._db.execute(
            """
            SELECT
                game_id,
                timestamp_ms,
                server_seed,
                server_seed_hash,
                peak_multiplier,
                final_price,
                tick_count
            FROM games
            WHERE server_seed IS NOT NULL
            ORDER BY timestamp_ms ASC
            """
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_game_events(self, game_id: str) -> list[dict[str, Any]]:
        """
        Get all events for a specific game.

        Args:
            game_id: Game identifier

        Returns:
            List of event dicts
        """
        if not self._db:
            return []

        cursor = await self._db.execute(
            """
            SELECT * FROM events
            WHERE game_id = ?
            ORDER BY timestamp ASC
            """,
            (game_id,),
        )
        rows = await cursor.fetchall()

        result = []
        for row in rows:
            event_dict = dict(row)
            event_dict["data"] = json.loads(event_dict["data"])
            result.append(event_dict)

        return result

    async def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        if not self._db:
            return {}

        cursor = await self._db.execute("SELECT COUNT(*) as count FROM games")
        games_count = (await cursor.fetchone())["count"]

        cursor = await self._db.execute(
            "SELECT COUNT(*) as count FROM games WHERE server_seed IS NOT NULL"
        )
        seeds_count = (await cursor.fetchone())["count"]

        cursor = await self._db.execute("SELECT COUNT(*) as count FROM events")
        events_count = (await cursor.fetchone())["count"]

        return {
            "total_games": games_count,
            "seed_reveals": seeds_count,
            "total_events": events_count,
        }
