"""
Game Storage - Parquet-based storage for captured game data.

Stores complete game records extracted from gameHistory.
"""

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Try to import pyarrow for Parquet support
try:
    import pyarrow as pa
    import pyarrow.parquet as pq

    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    logger.warning("pyarrow not installed, falling back to JSON storage")


class GameStorage:
    """
    Storage backend for captured game data.

    Primary: Parquet files partitioned by date
    Fallback: JSON files if pyarrow not available

    Storage structure:
        storage_path/
        ├── games_2026-01-19.parquet  (or .jsonl)
        ├── games_2026-01-20.parquet
        └── ...
    """

    def __init__(self, storage_path: Path | str):
        """
        Initialize game storage.

        Args:
            storage_path: Base directory for storing game files
        """
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        # Buffer for batched writes
        self._buffer: list[dict] = []
        self._buffer_size = 10  # Flush after N games

        logger.info(
            f"GameStorage initialized at {self._storage_path} "
            f"(parquet={'yes' if PARQUET_AVAILABLE else 'no'})"
        )

    def store_games(self, games: list[dict]) -> int:
        """
        Store multiple games.

        Args:
            games: List of game dicts from gameHistory

        Returns:
            Number of games stored
        """
        if not games:
            return 0

        with self._lock:
            # Add metadata to each game
            now = datetime.now(timezone.utc)
            enriched_games = []
            for game in games:
                enriched = self._enrich_game(game, now)
                enriched_games.append(enriched)

            # Add to buffer
            self._buffer.extend(enriched_games)

            # Flush if buffer is full
            if len(self._buffer) >= self._buffer_size:
                self._flush()

            return len(enriched_games)

    def _enrich_game(self, game: dict, capture_time: datetime) -> dict:
        """
        Add metadata to game record.

        Args:
            game: Raw game dict from gameHistory
            capture_time: When the game was captured

        Returns:
            Enriched game dict
        """
        return {
            # Core game fields (preserve original)
            **game,
            # Metadata fields
            "_captured_at": capture_time.isoformat(),
            "_capture_date": capture_time.strftime("%Y-%m-%d"),
            "_source": "recording_service",
            "_version": "1.0.0",
        }

    def _flush(self) -> None:
        """Flush buffer to storage."""
        if not self._buffer:
            return

        try:
            # Group by date
            by_date: dict[str, list[dict]] = {}
            for game in self._buffer:
                date = game.get("_capture_date", datetime.now().strftime("%Y-%m-%d"))
                if date not in by_date:
                    by_date[date] = []
                by_date[date].append(game)

            # Write each date partition
            for date, games in by_date.items():
                self._write_partition(date, games)

            logger.debug(f"Flushed {len(self._buffer)} games to storage")
            self._buffer.clear()

        except Exception as e:
            logger.error(f"Failed to flush games to storage: {e}")
            # Keep buffer for retry

    def _write_partition(self, date: str, games: list[dict]) -> None:
        """
        Write games to date-partitioned file.

        Args:
            date: Date string (YYYY-MM-DD)
            games: List of games to write
        """
        if PARQUET_AVAILABLE:
            self._write_parquet(date, games)
        else:
            self._write_jsonl(date, games)

    def _write_parquet(self, date: str, games: list[dict]) -> None:
        """Write games to Parquet file."""
        file_path = self._storage_path / f"games_{date}.parquet"

        # Convert to PyArrow table
        # Flatten nested structures for Parquet compatibility
        flat_games = [self._flatten_game(g) for g in games]

        if file_path.exists():
            # Append to existing file
            existing_table = pq.read_table(file_path)
            new_table = pa.Table.from_pylist(flat_games)

            # Combine tables (handle schema differences gracefully)
            try:
                combined = pa.concat_tables([existing_table, new_table], promote=True)
            except Exception:
                # If schemas incompatible, just write new data
                combined = new_table
                logger.warning(f"Schema mismatch, overwriting {file_path}")

            pq.write_table(combined, file_path, compression="snappy")
        else:
            # Create new file
            table = pa.Table.from_pylist(flat_games)
            pq.write_table(table, file_path, compression="snappy")

    def _write_jsonl(self, date: str, games: list[dict]) -> None:
        """Write games to JSONL file (fallback)."""
        file_path = self._storage_path / f"games_{date}.jsonl"

        with open(file_path, "a") as f:
            for game in games:
                f.write(json.dumps(game) + "\n")

    def _flatten_game(self, game: dict) -> dict:
        """
        Flatten nested game structure for Parquet.

        Converts nested dicts/lists to JSON strings.
        """
        flat = {}
        for key, value in game.items():
            if isinstance(value, (dict, list)):
                flat[key] = json.dumps(value)
            else:
                flat[key] = value
        return flat

    def get_total_game_count(self) -> int:
        """Get total number of stored games."""
        count = 0
        try:
            for file in self._storage_path.glob("games_*.parquet"):
                table = pq.read_table(file)
                count += table.num_rows
            for file in self._storage_path.glob("games_*.jsonl"):
                with open(file) as f:
                    count += sum(1 for _ in f)
        except Exception as e:
            logger.error(f"Failed to count games: {e}")
        return count

    def get_today_game_count(self) -> int:
        """Get number of games stored today."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self._get_date_count(today)

    def _get_date_count(self, date: str) -> int:
        """Get number of games for a specific date."""
        count = 0
        try:
            parquet_file = self._storage_path / f"games_{date}.parquet"
            if parquet_file.exists():
                table = pq.read_table(parquet_file)
                count += table.num_rows

            jsonl_file = self._storage_path / f"games_{date}.jsonl"
            if jsonl_file.exists():
                with open(jsonl_file) as f:
                    count += sum(1 for _ in f)
        except Exception as e:
            logger.error(f"Failed to count games for {date}: {e}")
        return count

    def get_recent_games(self, limit: int = 10) -> list[dict]:
        """
        Get most recently captured games.

        Args:
            limit: Maximum number of games to return

        Returns:
            List of recent game dicts (newest first)
        """
        # Include buffered games first
        recent = list(self._buffer[-limit:])
        remaining = limit - len(recent)

        if remaining <= 0:
            return list(reversed(recent))

        # Get from most recent files
        try:
            files = sorted(
                list(self._storage_path.glob("games_*.parquet"))
                + list(self._storage_path.glob("games_*.jsonl")),
                key=lambda p: p.stem,
                reverse=True,
            )

            for file in files[:5]:  # Check last 5 days max
                if remaining <= 0:
                    break

                if file.suffix == ".parquet" and PARQUET_AVAILABLE:
                    table = pq.read_table(file)
                    df_dict = table.to_pydict()
                    # Convert columnar to row-based
                    if df_dict:
                        keys = list(df_dict.keys())
                        rows = []
                        for i in range(min(remaining, len(df_dict[keys[0]]))):
                            idx = len(df_dict[keys[0]]) - 1 - i  # Reverse order
                            row = {k: df_dict[k][idx] for k in keys}
                            rows.append(row)
                        recent.extend(rows)
                        remaining -= len(rows)

                elif file.suffix == ".jsonl":
                    with open(file) as f:
                        lines = f.readlines()
                    for line in reversed(lines[-remaining:]):
                        recent.append(json.loads(line.strip()))
                    remaining -= min(remaining, len(lines))

        except Exception as e:
            logger.error(f"Failed to get recent games: {e}")

        return recent[:limit]

    def flush(self) -> None:
        """Force flush any buffered data."""
        with self._lock:
            self._flush()

    def get_storage_stats(self) -> dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dict with storage stats
        """
        total_size = 0
        file_count = 0

        for pattern in ["games_*.parquet", "games_*.jsonl"]:
            for file in self._storage_path.glob(pattern):
                total_size += file.stat().st_size
                file_count += 1

        return {
            "storage_path": str(self._storage_path),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
            "buffer_size": len(self._buffer),
            "parquet_available": PARQUET_AVAILABLE,
        }
