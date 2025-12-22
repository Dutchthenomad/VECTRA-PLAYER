"""
DuckDB Query Layer - Stateless query interface for Parquet event data

Issue #10: [Infra] DuckDB query layer

Features:
- Query Parquet files directly (no ETL)
- SQL window functions for feature engineering
- Game episode extraction for RL training
- Player state reconstruction
"""

import logging
from collections.abc import Iterator
from typing import Any

import duckdb
import pandas as pd
import pyarrow as pa

from services.event_store.paths import EventStorePaths

logger = logging.getLogger(__name__)


class EventStoreQuery:
    """
    Stateless DuckDB query interface for Parquet event data.

    Each method creates a fresh DuckDB connection, executes the query,
    returns results, and closes the connection. This provides:
    - Thread-safety by default
    - No connection state to manage
    - Negligible overhead (~1ms per connection)

    Primary use cases:
    1. RL Training - Game episode extraction, player filtering
    2. Analytics - Ad-hoc SQL queries
    3. UI - Recent event queries

    Usage:
        query = EventStoreQuery()
        episode = query.get_game_episode("game-abc-123")
        for game_df in query.iter_episodes(player_id="whale-xyz", limit=50):
            train_on(game_df)
    """

    def __init__(self, paths: EventStorePaths | None = None):
        """
        Initialize EventStoreQuery.

        Args:
            paths: EventStorePaths instance (uses defaults if None)
        """
        self._paths = paths or EventStorePaths()

    def _parquet_glob(self, doc_type: str | None = None) -> str:
        """
        Build glob pattern for Parquet files.

        Args:
            doc_type: Filter to specific doc_type partition (optional)

        Returns:
            Glob pattern string for DuckDB
        """
        if doc_type:
            return str(self._paths.events_parquet_dir / f"doc_type={doc_type}" / "**/*.parquet")
        return str(self._paths.events_parquet_dir / "**/*.parquet")

    def _has_data(self) -> bool:
        """Check if any Parquet files exist."""
        parquet_dir = self._paths.events_parquet_dir
        if not parquet_dir.exists():
            return False
        return any(parquet_dir.rglob("*.parquet"))

    # =========================================================================
    # Core Query Methods
    # =========================================================================

    def query(self, sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
        """
        Execute SQL and return pandas DataFrame.

        Args:
            sql: SQL query string
            params: Optional parameter dict for $param substitution

        Returns:
            Query results as pandas DataFrame
        """
        conn = duckdb.connect()
        try:
            if params:
                # DuckDB uses $name for parameters
                result = conn.execute(sql, params).df()
            else:
                result = conn.execute(sql).df()
            return result
        finally:
            conn.close()

    def query_arrow(self, sql: str, params: dict[str, Any] | None = None) -> pa.Table:
        """
        Execute SQL and return PyArrow Table (zero-copy).

        Args:
            sql: SQL query string
            params: Optional parameter dict for $param substitution

        Returns:
            Query results as PyArrow Table
        """
        conn = duckdb.connect()
        try:
            if params:
                result = conn.execute(sql, params).fetch_arrow_table()
            else:
                result = conn.execute(sql).fetch_arrow_table()
            return result
        finally:
            conn.close()

    # =========================================================================
    # Game Episode Extraction (RL Training Primary Use Case)
    # =========================================================================

    def get_game_episode(self, game_id: str) -> pd.DataFrame:
        """
        Get all events for a single game, sorted by sequence.

        This is the primary method for RL training - returns a complete
        game episode with all event types (ticks, actions, states).

        Args:
            game_id: Game identifier

        Returns:
            DataFrame with all events for the game, sorted by seq.
            Returns empty DataFrame if game not found.
        """
        if not self._has_data():
            return pd.DataFrame()

        parquet_glob = self._parquet_glob()
        sql = f"""
            SELECT *
            FROM '{parquet_glob}'
            WHERE game_id = $game_id
            ORDER BY seq
        """
        return self.query(sql, {"game_id": game_id})

    def iter_episodes(
        self,
        player_id: str | None = None,
        min_ticks: int | None = None,
        limit: int | None = None,
    ) -> Iterator[pd.DataFrame]:
        """
        Iterate over game episodes as DataFrames.

        Memory-efficient way to process many games for training.

        Args:
            player_id: Filter to games with this player
            min_ticks: Filter to games with at least N ticks
            limit: Maximum number of games to return

        Yields:
            DataFrame per game, sorted by seq
        """
        if not self._has_data():
            return

        # First, get list of qualifying game_ids
        game_ids = self._get_qualifying_game_ids(player_id, min_ticks, limit)

        # Then fetch each game's data
        for game_id in game_ids:
            episode = self.get_game_episode(game_id)
            if len(episode) > 0:
                yield episode

    def _get_qualifying_game_ids(
        self,
        player_id: str | None = None,
        min_ticks: int | None = None,
        limit: int | None = None,
    ) -> list[str]:
        """Get game_ids matching the filter criteria."""
        parquet_glob = self._parquet_glob()

        # Build WHERE clauses
        where_clauses = ["game_id IS NOT NULL"]
        params: dict[str, Any] = {}

        if player_id:
            where_clauses.append("player_id = $player_id")
            params["player_id"] = player_id

        where_sql = " AND ".join(where_clauses)

        if min_ticks:
            # Subquery to filter by tick count
            # Qualify all column references to avoid ambiguity
            where_sql_qualified = where_sql.replace("game_id", "g.game_id").replace(
                "player_id", "g.player_id"
            )
            sql = f"""
                WITH game_tick_counts AS (
                    SELECT game_id, COUNT(*) as tick_count
                    FROM '{parquet_glob}'
                    WHERE doc_type = 'game_tick'
                    GROUP BY game_id
                    HAVING tick_count >= $min_ticks
                )
                SELECT DISTINCT g.game_id
                FROM '{parquet_glob}' g
                JOIN game_tick_counts t ON g.game_id = t.game_id
                WHERE {where_sql_qualified}
            """
            params["min_ticks"] = min_ticks
        else:
            sql = f"""
                SELECT DISTINCT game_id
                FROM '{parquet_glob}'
                WHERE {where_sql}
            """

        # AUDIT FIX: Use parameter substitution instead of f-string for SQL injection safety
        if limit:
            sql += " LIMIT $limit"
            params["limit"] = limit

        result = self.query(sql, params if params else None)
        return result["game_id"].tolist() if len(result) > 0 else []

    def get_episodes_batch(self, game_ids: list[str]) -> dict[str, pd.DataFrame]:
        """
        Get multiple episodes in one query (more efficient than individual calls).

        Args:
            game_ids: List of game identifiers

        Returns:
            Dict mapping game_id to DataFrame
        """
        if not self._has_data() or not game_ids:
            return {}

        parquet_glob = self._parquet_glob()

        # AUDIT FIX: Use parameter substitution with UNNEST for SQL injection safety
        # DuckDB supports list parameters via UNNEST
        sql = f"""
            SELECT *
            FROM '{parquet_glob}'
            WHERE game_id IN (SELECT UNNEST($game_ids))
            ORDER BY game_id, seq
        """

        all_data = self.query(sql, {"game_ids": game_ids})

        # Split into per-game DataFrames
        result = {}
        for game_id in game_ids:
            game_data = all_data[all_data["game_id"] == game_id].copy()
            if len(game_data) > 0:
                result[game_id] = game_data

        return result

    # =========================================================================
    # Player Queries
    # =========================================================================

    def get_player_games(self, player_id: str, limit: int = 100) -> pd.DataFrame:
        """
        Get all events from a player's games.

        Returns events from all games where this player participated.

        Args:
            player_id: Player identifier
            limit: Maximum events to return

        Returns:
            DataFrame with events from player's games
        """
        if not self._has_data():
            return pd.DataFrame()

        parquet_glob = self._parquet_glob()

        # First find games this player was in
        sql = f"""
            WITH player_games AS (
                SELECT DISTINCT game_id
                FROM '{parquet_glob}'
                WHERE player_id = $player_id
            )
            SELECT e.*
            FROM '{parquet_glob}' e
            JOIN player_games pg ON e.game_id = pg.game_id
            ORDER BY e.game_id, e.seq
            LIMIT $limit
        """
        return self.query(sql, {"player_id": player_id, "limit": limit})

    def get_player_actions(self, player_id: str, limit: int = 100) -> pd.DataFrame:
        """
        Get player_action events only for a specific player.

        Args:
            player_id: Player identifier
            limit: Maximum events to return

        Returns:
            DataFrame with only player_action doc_type events
        """
        if not self._has_data():
            return pd.DataFrame()

        parquet_glob = self._parquet_glob(doc_type="player_action")
        sql = f"""
            SELECT *
            FROM '{parquet_glob}'
            WHERE player_id = $player_id
            ORDER BY seq
            LIMIT $limit
        """
        return self.query(sql, {"player_id": player_id, "limit": limit})

    # =========================================================================
    # Discovery / Listing Methods
    # =========================================================================

    def list_games(self, limit: int = 100) -> list[str]:
        """
        List unique game_ids in the dataset.

        Args:
            limit: Maximum number of games to return

        Returns:
            List of game_id strings
        """
        if not self._has_data():
            return []

        parquet_glob = self._parquet_glob()
        sql = f"""
            SELECT DISTINCT game_id
            FROM '{parquet_glob}'
            WHERE game_id IS NOT NULL
            LIMIT $limit
        """
        result = self.query(sql, {"limit": limit})
        return result["game_id"].tolist() if len(result) > 0 else []

    def list_players(self, limit: int = 100) -> list[str]:
        """
        List unique player_ids in the dataset.

        Args:
            limit: Maximum number of players to return

        Returns:
            List of player_id strings
        """
        if not self._has_data():
            return []

        parquet_glob = self._parquet_glob()
        sql = f"""
            SELECT DISTINCT player_id
            FROM '{parquet_glob}'
            WHERE player_id IS NOT NULL
            LIMIT $limit
        """
        result = self.query(sql, {"limit": limit})
        return result["player_id"].tolist() if len(result) > 0 else []

    def count_events(self, doc_type: str | None = None) -> int:
        """
        Count total events in the dataset.

        Args:
            doc_type: Filter to specific doc_type (optional)

        Returns:
            Event count
        """
        if not self._has_data():
            return 0

        parquet_glob = self._parquet_glob(doc_type=doc_type)
        sql = f"SELECT COUNT(*) as cnt FROM '{parquet_glob}'"
        result = self.query(sql)
        return int(result.iloc[0]["cnt"]) if len(result) > 0 else 0

    # =========================================================================
    # Feature Engineering
    # =========================================================================

    def get_tick_features(self, game_id: str) -> pd.DataFrame:
        """
        Get game ticks with computed features using SQL window functions.

        Features computed:
        - price_change: Absolute change from previous tick
        - price_pct_change: Percentage change from previous tick
        - volatility_5: Rolling 5-tick standard deviation
        - volatility_10: Rolling 10-tick standard deviation
        - max_price: Running maximum price
        - drawdown: Current price vs max (percentage below max)

        Args:
            game_id: Game identifier

        Returns:
            DataFrame with tick data and computed features.
            Only includes game_tick events (not actions).
        """
        if not self._has_data():
            return pd.DataFrame()

        parquet_glob = self._parquet_glob(doc_type="game_tick")

        sql = f"""
            SELECT
                tick,
                CAST(price AS DOUBLE) as price,
                ts,
                CAST(price AS DOUBLE) - LAG(CAST(price AS DOUBLE)) OVER w AS price_change,
                (CAST(price AS DOUBLE) - LAG(CAST(price AS DOUBLE)) OVER w)
                    / NULLIF(LAG(CAST(price AS DOUBLE)) OVER w, 0) AS price_pct_change,
                STDDEV(CAST(price AS DOUBLE)) OVER (
                    ORDER BY seq ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                ) AS volatility_5,
                STDDEV(CAST(price AS DOUBLE)) OVER (
                    ORDER BY seq ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
                ) AS volatility_10,
                MAX(CAST(price AS DOUBLE)) OVER (
                    ORDER BY seq ROWS UNBOUNDED PRECEDING
                ) AS max_price,
                CAST(price AS DOUBLE) / NULLIF(
                    MAX(CAST(price AS DOUBLE)) OVER (ORDER BY seq ROWS UNBOUNDED PRECEDING),
                    0
                ) - 1 AS drawdown
            FROM '{parquet_glob}'
            WHERE game_id = $game_id
            WINDOW w AS (ORDER BY seq)
            ORDER BY seq
        """
        return self.query(sql, {"game_id": game_id})
