"""
Session Tracker - Tracks session-specific metrics.

The recording dashboard needs to show:
- Games recorded THIS session (not historical totals)
- Unique gameIds only (deduped from rolling window duplicates)
- Events captured this session

Critical knowledge from rugs-expert:
- gameHistory is a 10-game rolling window (same game appears ~10 times)
- Dual-broadcast on rug: 2 back-to-back events when game ends
- MUST deduplicate by gameId for accurate counting

Performance note:
- Stats are CACHED and updated in background (not on every request)
- This prevents blocking Flask's single-threaded server
"""

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

# Default data directory
DATA_DIR = Path.home() / "rugs_data" / "events_parquet"

# Cache settings
CACHE_TTL_SECONDS = 3.0  # How often to refresh stats


class SessionTracker:
    """
    Tracks session-specific metrics separate from historical totals.

    Per rugs-expert knowledge:
    - gameHistory is a 10-game rolling window
    - Same game appears in multiple WebSocket events (up to 10x)
    - Must deduplicate by gameId for accurate counting
    """

    def __init__(self, data_dir: Path | None = None):
        """Initialize session tracker.

        Args:
            data_dir: Base directory for Parquet files
        """
        self.data_dir = data_dir or DATA_DIR
        self.complete_game_path = self.data_dir / "doc_type=complete_game"

        # Session start time (when dashboard was started)
        self.session_start = datetime.now()
        self.session_start_ts = self.session_start.isoformat()

        # Track unique gameIds seen this session (for deduplication)
        self._seen_game_ids: set[str] = set()

        # Track raw event count this session
        self._event_count: int = 0

        # Cache for expensive stats (prevents blocking on every request)
        self._cache_lock = threading.Lock()
        self._session_stats_cache: dict[str, Any] = {
            "session_game_count": 0,
            "session_event_count": 0,
            "session_start": self.session_start_ts,
            "session_duration_seconds": 0,
        }
        self._total_stats_cache: dict[str, Any] = {
            "total_game_count": 0,
            "total_event_count": 0,
            "storage_mb": 0.0,
        }
        self._cache_last_update = 0.0
        self._cache_initializing = False

        logger.info(f"Session tracker started at {self.session_start_ts}")

        # Pre-populate cache in background (so first request doesn't fail)
        self._initialize_cache()

    def _initialize_cache(self) -> None:
        """Initialize cache in background on startup."""
        self._cache_initializing = True
        thread = threading.Thread(target=self._do_init, daemon=True, name="CacheInit")
        thread.start()

    def _do_init(self) -> None:
        """Background cache initialization."""
        try:
            logger.info("Initializing stats cache (background)...")
            self._refresh_cache()
            logger.info("Stats cache initialized")
        finally:
            self._cache_initializing = False

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get a DuckDB connection."""
        return duckdb.connect()

    def get_session_stats(self) -> dict[str, Any]:
        """
        Get session-specific statistics (cached for performance).

        Returns unique game count (deduplicated by gameId) and events
        recorded AFTER the session start time.

        Note: Stats are cached and refreshed every CACHE_TTL_SECONDS.
        """
        self._maybe_refresh_cache()

        with self._cache_lock:
            # Always update duration (cheap operation)
            stats = self._session_stats_cache.copy()
            stats["session_duration_seconds"] = (
                datetime.now() - self.session_start
            ).total_seconds()
            return stats

    def _maybe_refresh_cache(self) -> None:
        """Refresh cache if stale (non-blocking check, background update)."""
        now = time.time()
        if now - self._cache_last_update < CACHE_TTL_SECONDS:
            return

        # Don't start another refresh if one is already running
        if self._cache_initializing:
            return

        # Update in background thread to avoid blocking
        self._cache_initializing = True
        thread = threading.Thread(target=self._do_refresh, daemon=True, name="CacheRefresh")
        thread.start()

    def _do_refresh(self) -> None:
        """Wrapper to ensure flag is cleared after refresh."""
        try:
            self._refresh_cache()
        finally:
            self._cache_initializing = False

    def _refresh_cache(self) -> None:
        """Actually refresh the cache (runs in background thread)."""
        try:
            conn = self.get_connection()

            # Query games recorded after session start
            session_games: set[str] = set()
            session_event_count = 0

            if self.complete_game_path.exists():
                session_start_epoch = self.session_start.timestamp()

                for parquet_file in self.complete_game_path.rglob("*.parquet"):
                    if parquet_file.stat().st_mtime >= session_start_epoch:
                        try:
                            result = conn.execute(f"""
                                SELECT DISTINCT game_id
                                FROM '{parquet_file}'
                            """).fetchall()

                            for row in result:
                                session_games.add(row[0])
                        except Exception as e:
                            logger.debug(f"Error reading {parquet_file}: {e}")

            # Count events from all doc_types since session start
            if self.data_dir.exists():
                session_start_epoch = self.session_start.timestamp()

                for parquet_file in self.data_dir.rglob("*.parquet"):
                    if parquet_file.stat().st_mtime >= session_start_epoch:
                        try:
                            result = conn.execute(f"""
                                SELECT COUNT(*) FROM '{parquet_file}'
                            """).fetchone()
                            session_event_count += result[0] if result else 0
                        except Exception:
                            pass

            # Get total stats too (while we're at it)
            total_game_count = 0
            total_event_count = 0
            storage_bytes = 0

            if self.complete_game_path.exists():
                result = conn.execute(f"""
                    SELECT COUNT(DISTINCT game_id) as cnt
                    FROM '{self.complete_game_path}/**/*.parquet'
                """).fetchone()
                total_game_count = result[0] if result else 0

            if self.data_dir.exists():
                result = conn.execute(f"""
                    SELECT COUNT(*) as cnt
                    FROM '{self.data_dir}/**/*.parquet'
                """).fetchone()
                total_event_count = result[0] if result else 0

                for f in self.data_dir.rglob("*.parquet"):
                    storage_bytes += f.stat().st_size

            # Update caches atomically
            with self._cache_lock:
                self._session_stats_cache = {
                    "session_game_count": len(session_games),
                    "session_event_count": session_event_count,
                    "session_start": self.session_start_ts,
                    "session_duration_seconds": (
                        datetime.now() - self.session_start
                    ).total_seconds(),
                }
                self._total_stats_cache = {
                    "total_game_count": total_game_count,
                    "total_event_count": total_event_count,
                    "storage_mb": round(storage_bytes / (1024 * 1024), 2),
                }
                self._cache_last_update = time.time()

            # Update internal tracking
            self._seen_game_ids = session_games
            self._event_count = session_event_count

        except Exception as e:
            logger.error(f"Error refreshing cache: {e}")

    def get_session_games(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get games recorded during this session only.

        Returns:
            List of game dictionaries recorded since session start
        """
        try:
            if not self.complete_game_path.exists():
                return []

            conn = self.get_connection()
            session_start_epoch = self.session_start.timestamp()

            # Collect games from files modified since session start
            all_games = []

            for parquet_file in self.complete_game_path.rglob("*.parquet"):
                if parquet_file.stat().st_mtime >= session_start_epoch:
                    try:
                        result = conn.execute(f"""
                            SELECT game_id, ts, raw_json
                            FROM '{parquet_file}'
                        """).fetchall()

                        for row in result:
                            game_id, ts, raw_json = row
                            try:
                                data = json.loads(raw_json) if raw_json else {}
                            except json.JSONDecodeError:
                                data = {}

                            all_games.append(
                                {
                                    "game_id": game_id,
                                    "timestamp": ts,
                                    "peak_multiplier": data.get("peakMultiplier", 0),
                                    "tick_count": len(data.get("prices", [])),
                                    "sidebet_count": len(data.get("globalSidebets", [])),
                                    "rugged": data.get("rugged", False),
                                }
                            )
                    except Exception as e:
                        logger.debug(f"Error reading {parquet_file}: {e}")

            # Deduplicate by gameId (keep first occurrence)
            seen = set()
            unique_games = []
            for game in all_games:
                if game["game_id"] not in seen:
                    seen.add(game["game_id"])
                    unique_games.append(game)

            # Sort by timestamp descending and limit
            unique_games.sort(key=lambda g: g["timestamp"] or "", reverse=True)
            return unique_games[:limit]

        except Exception as e:
            logger.error(f"Error getting session games: {e}")
            return []

    def get_total_stats(self) -> dict[str, Any]:
        """
        Get total historical statistics (all sessions, cached).

        Useful for showing "total recorded ever" vs "this session".

        Note: Stats are cached and refreshed every CACHE_TTL_SECONDS.
        """
        self._maybe_refresh_cache()

        with self._cache_lock:
            return self._total_stats_cache.copy()

    def reset_session(self):
        """Reset session tracking (start fresh)."""
        self.session_start = datetime.now()
        self.session_start_ts = self.session_start.isoformat()
        self._seen_game_ids.clear()
        self._event_count = 0
        logger.info(f"Session reset at {self.session_start_ts}")
