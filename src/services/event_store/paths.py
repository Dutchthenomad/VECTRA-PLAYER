"""
Event Store Paths - Derive all directories from config/env

No hardcoded paths. All paths derived from RUGS_DATA_DIR.
"""

from pathlib import Path


class EventStorePaths:
    """
    Centralized path management for Event Store.

    All paths derived from RUGS_DATA_DIR environment variable.
    Default: ~/rugs_data/
    """

    def __init__(self, data_dir: Path | None = None):
        """
        Initialize paths from config or explicit directory.

        Args:
            data_dir: Override data directory (for testing)
        """
        if data_dir is not None:
            self._data_dir = Path(data_dir)
        else:
            # Import config lazily to avoid circular imports
            from config import Config

            data_config = Config.get_data_config()
            self._data_dir = data_config["data_dir"]

    @property
    def data_dir(self) -> Path:
        """Root data directory (RUGS_DATA_DIR)"""
        return self._data_dir

    @property
    def events_parquet_dir(self) -> Path:
        """Canonical Parquet dataset directory"""
        return self._data_dir / "events_parquet"

    @property
    def vectors_dir(self) -> Path:
        """LanceDB vector index directory"""
        return self._data_dir / "vectors"

    @property
    def exports_dir(self) -> Path:
        """Optional JSONL exports directory"""
        return self._data_dir / "exports"

    @property
    def manifests_dir(self) -> Path:
        """Schema and checkpoint manifests"""
        return self._data_dir / "manifests"

    def parquet_partition_dir(self, doc_type: str, date_str: str) -> Path:
        """
        Get partition directory for a specific doc_type and date.

        Args:
            doc_type: Document type (ws_event, game_tick, etc.)
            date_str: Date string (YYYY-MM-DD)

        Returns:
            Path to partition directory
        """
        return self.events_parquet_dir / f"doc_type={doc_type}" / f"date={date_str}"

    def ensure_directories(self) -> dict:
        """
        Create all required directories.

        Returns:
            Dict mapping directory names to creation success status
        """
        status = {}
        for name, path in [
            ("data_dir", self.data_dir),
            ("events_parquet", self.events_parquet_dir),
            ("vectors", self.vectors_dir),
            ("exports", self.exports_dir),
            ("manifests", self.manifests_dir),
        ]:
            try:
                path.mkdir(parents=True, exist_ok=True)
                status[name] = path.exists()
            except Exception:
                status[name] = False
        return status

    def schema_version_file(self) -> Path:
        """Path to schema version manifest"""
        return self.manifests_dir / "schema_version.json"

    def vector_checkpoint_file(self) -> Path:
        """Path to vector index checkpoint"""
        return self.manifests_dir / "vector_index_checkpoint.json"

    def context_file(self) -> Path:
        """Path to CONTEXT.md for AI reference"""
        return self._data_dir / "CONTEXT.md"
