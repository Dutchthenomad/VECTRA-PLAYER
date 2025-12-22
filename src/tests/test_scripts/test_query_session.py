"""
Tests for scripts/query_session.py

Tests the DuckDB query functionality for Parquet event data.
"""

import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from query_session import get_data_dir, query_recent, query_session, query_stats


@pytest.fixture
def test_parquet_data(tmp_path):
    """
    Create test Parquet data for testing queries.

    Creates a temporary data directory with sample Parquet files
    containing test events across multiple doc_types.
    """
    # Create directory structure
    data_dir = tmp_path / "test_rugs_data"
    parquet_dir = data_dir / "events_parquet"

    # Create partitions
    for doc_type in ["ws_event", "game_tick", "player_action", "server_state"]:
        partition_dir = parquet_dir / f"doc_type={doc_type}" / "date=2025-12-21"
        partition_dir.mkdir(parents=True)

    # Create sample data
    conn = duckdb.connect()

    # Sample events for session1
    session1_id = "test-session-001"
    events1 = [
        {
            "ts": "2025-12-21 10:00:00",
            "source": "public_ws",
            "doc_type": "ws_event",
            "session_id": session1_id,
            "seq": 1,
            "direction": "received",
            "raw_json": '{"event": "gameStart"}',
            "event_name": "gameStart",
            "game_id": "game-001",
        },
        {
            "ts": "2025-12-21 10:00:01",
            "source": "public_ws",
            "doc_type": "game_tick",
            "session_id": session1_id,
            "seq": 2,
            "direction": "received",
            "raw_json": '{"tick": 1, "price": "1.0"}',
            "tick": 1,
            "price": "1.0",
            "game_id": "game-001",
        },
        {
            "ts": "2025-12-21 10:00:02",
            "source": "ui",
            "doc_type": "player_action",
            "session_id": session1_id,
            "seq": 3,
            "direction": "sent",
            "raw_json": '{"action": "buy"}',
            "action_type": "buy",
            "game_id": "game-001",
        },
    ]

    # Sample events for session2
    session2_id = "test-session-002"
    events2 = [
        {
            "ts": "2025-12-21 11:00:00",
            "source": "public_ws",
            "doc_type": "ws_event",
            "session_id": session2_id,
            "seq": 1,
            "direction": "received",
            "raw_json": '{"event": "gameStart"}',
            "event_name": "gameStart",
            "game_id": "game-002",
        },
        {
            "ts": "2025-12-21 11:00:01",
            "source": "public_ws",
            "doc_type": "server_state",
            "session_id": session2_id,
            "seq": 2,
            "direction": "received",
            "raw_json": '{"cash": "0.1"}',
            "cash": "0.1",
            "game_id": "game-002",
        },
    ]

    # Write session1 events to Parquet
    for event in events1:
        doc_type = event["doc_type"]
        partition_dir = parquet_dir / f"doc_type={doc_type}" / "date=2025-12-21"
        file_path = partition_dir / f"test_{doc_type}_session1.parquet"

        # Convert to DuckDB and write
        df = conn.execute(
            """
            SELECT * FROM (VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ) AS t(ts, source, doc_type, session_id, seq, direction, raw_json,
                   event_name, game_id, tick, price, action_type)
        """,
            [
                event.get("ts"),
                event.get("source"),
                event.get("doc_type"),
                event.get("session_id"),
                event.get("seq"),
                event.get("direction"),
                event.get("raw_json"),
                event.get("event_name"),
                event.get("game_id"),
                event.get("tick"),
                event.get("price"),
                event.get("action_type"),
            ],
        ).df()

        conn.execute(f"COPY (SELECT * FROM df) TO '{file_path}' (FORMAT PARQUET)")

    # Write session2 events to Parquet
    for event in events2:
        doc_type = event["doc_type"]
        partition_dir = parquet_dir / f"doc_type={doc_type}" / "date=2025-12-21"
        file_path = partition_dir / f"test_{doc_type}_session2.parquet"

        df = conn.execute(
            """
            SELECT * FROM (VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ) AS t(ts, source, doc_type, session_id, seq, direction, raw_json,
                   event_name, game_id, cash)
        """,
            [
                event.get("ts"),
                event.get("source"),
                event.get("doc_type"),
                event.get("session_id"),
                event.get("seq"),
                event.get("direction"),
                event.get("raw_json"),
                event.get("event_name"),
                event.get("game_id"),
                event.get("cash"),
            ],
        ).df()

        conn.execute(f"COPY (SELECT * FROM df) TO '{file_path}' (FORMAT PARQUET)")

    conn.close()

    return {
        "data_dir": data_dir,
        "parquet_dir": parquet_dir,
        "session1_id": session1_id,
        "session2_id": session2_id,
    }


class TestGetDataDir:
    """Tests for get_data_dir() function"""

    def test_get_data_dir_from_env(self, monkeypatch):
        """Test that data dir is read from RUGS_DATA_DIR env var"""
        test_dir = "/tmp/test_rugs_data"
        monkeypatch.setenv("RUGS_DATA_DIR", test_dir)

        result = get_data_dir()

        assert result == Path(test_dir)

    def test_get_data_dir_default(self, monkeypatch):
        """Test that data dir defaults to ~/rugs_data"""
        monkeypatch.delenv("RUGS_DATA_DIR", raising=False)

        result = get_data_dir()

        assert result == Path.home() / "rugs_data"


class TestQuerySession:
    """Tests for query_session() function"""

    def test_query_session_success(self, test_parquet_data, capsys, monkeypatch):
        """Test querying a valid session"""
        monkeypatch.setenv("RUGS_DATA_DIR", str(test_parquet_data["data_dir"]))

        query_session(test_parquet_data["session1_id"])

        captured = capsys.readouterr()
        assert test_parquet_data["session1_id"] in captured.out
        assert "ws_event" in captured.out
        assert "game_tick" in captured.out
        assert "player_action" in captured.out
        assert "TOTAL" in captured.out

    def test_query_session_not_found(self, test_parquet_data, capsys, monkeypatch):
        """Test querying a non-existent session"""
        monkeypatch.setenv("RUGS_DATA_DIR", str(test_parquet_data["data_dir"]))

        query_session("non-existent-session-id")

        captured = capsys.readouterr()
        assert "No events found" in captured.out

    def test_query_session_missing_directory(self, tmp_path, capsys, monkeypatch):
        """Test querying when parquet directory doesn't exist"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        monkeypatch.setenv("RUGS_DATA_DIR", str(empty_dir))

        with pytest.raises(SystemExit) as exc_info:
            query_session("any-session")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Parquet directory not found" in captured.err


class TestQueryRecent:
    """Tests for query_recent() function"""

    def test_query_recent_default_limit(self, test_parquet_data, capsys, monkeypatch):
        """Test querying recent events with default limit"""
        monkeypatch.setenv("RUGS_DATA_DIR", str(test_parquet_data["data_dir"]))

        query_recent()

        captured = capsys.readouterr()
        assert "Most Recent" in captured.out
        assert "Timestamp" in captured.out
        assert "Doc Type" in captured.out

    def test_query_recent_custom_limit(self, test_parquet_data, capsys, monkeypatch):
        """Test querying recent events with custom limit"""
        monkeypatch.setenv("RUGS_DATA_DIR", str(test_parquet_data["data_dir"]))

        query_recent(limit=3)

        captured = capsys.readouterr()
        assert "Most Recent 3 Events" in captured.out

    def test_query_recent_missing_directory(self, tmp_path, capsys, monkeypatch):
        """Test querying recent when parquet directory doesn't exist"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        monkeypatch.setenv("RUGS_DATA_DIR", str(empty_dir))

        with pytest.raises(SystemExit) as exc_info:
            query_recent()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Parquet directory not found" in captured.err


class TestQueryStats:
    """Tests for query_stats() function"""

    def test_query_stats_success(self, test_parquet_data, capsys, monkeypatch):
        """Test querying statistics"""
        monkeypatch.setenv("RUGS_DATA_DIR", str(test_parquet_data["data_dir"]))

        query_stats()

        captured = capsys.readouterr()
        assert "CAPTURE STATISTICS" in captured.out
        assert "Total Events:" in captured.out
        assert "Total Sessions:" in captured.out
        assert "Date Range:" in captured.out
        assert "Events by Document Type:" in captured.out

    def test_query_stats_shows_doc_types(self, test_parquet_data, capsys, monkeypatch):
        """Test that statistics show doc_type breakdown"""
        monkeypatch.setenv("RUGS_DATA_DIR", str(test_parquet_data["data_dir"]))

        query_stats()

        captured = capsys.readouterr()
        # Should show at least some of the doc types we created
        assert "ws_event" in captured.out or "game_tick" in captured.out

    def test_query_stats_missing_directory(self, tmp_path, capsys, monkeypatch):
        """Test querying stats when parquet directory doesn't exist"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        monkeypatch.setenv("RUGS_DATA_DIR", str(empty_dir))

        with pytest.raises(SystemExit) as exc_info:
            query_stats()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Parquet directory not found" in captured.err


class TestCLI:
    """Tests for command-line interface"""

    def test_cli_stats(self, test_parquet_data):
        """Test CLI with --stats flag"""
        env = os.environ.copy()
        env["RUGS_DATA_DIR"] = str(test_parquet_data["data_dir"])

        result = subprocess.run(
            [sys.executable, str(scripts_dir / "query_session.py"), "--stats"],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        assert "CAPTURE STATISTICS" in result.stdout

    def test_cli_recent(self, test_parquet_data):
        """Test CLI with --recent flag"""
        env = os.environ.copy()
        env["RUGS_DATA_DIR"] = str(test_parquet_data["data_dir"])

        result = subprocess.run(
            [sys.executable, str(scripts_dir / "query_session.py"), "--recent", "5"],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        assert "Most Recent 5 Events" in result.stdout

    def test_cli_session(self, test_parquet_data):
        """Test CLI with --session flag"""
        env = os.environ.copy()
        env["RUGS_DATA_DIR"] = str(test_parquet_data["data_dir"])

        result = subprocess.run(
            [
                sys.executable,
                str(scripts_dir / "query_session.py"),
                "--session",
                test_parquet_data["session1_id"],
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        assert test_parquet_data["session1_id"] in result.stdout

    def test_cli_no_arguments(self):
        """Test CLI with no arguments (should fail)"""
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "query_session.py")],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "arguments" in result.stderr.lower()

    def test_cli_help(self):
        """Test CLI help message"""
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "query_session.py"), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "--stats" in result.stdout
        assert "--recent" in result.stdout
        assert "--session" in result.stdout
