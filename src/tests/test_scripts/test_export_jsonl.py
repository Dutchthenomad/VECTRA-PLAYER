"""
Tests for scripts/export_jsonl.py

Tests the JSONL export functionality for Parquet event data.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

# Scripts path is added via conftest.py
from export_jsonl import export_to_jsonl, get_data_dir

# Scripts directory for CLI tests
scripts_dir = Path(__file__).parent.parent.parent / "scripts"


@pytest.fixture
def test_parquet_data(tmp_path):
    """
    Create test Parquet data for testing exports.

    Creates a temporary data directory with sample Parquet files
    containing test events across multiple doc_types and sessions.
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


class TestExportToJsonl:
    """Tests for export_to_jsonl() function"""

    def test_export_all_events(self, test_parquet_data, tmp_path):
        """Test exporting all events without filters"""
        output_dir = tmp_path / "exports"

        files = export_to_jsonl(test_parquet_data["parquet_dir"], output_dir)

        # Should create one file per doc_type
        assert len(files) > 0
        assert all(f.exists() for f in files)
        assert all(f.suffix == ".jsonl" for f in files)

        # Verify files contain data
        total_lines = 0
        for filepath in files:
            with open(filepath) as f:
                lines = f.readlines()
                total_lines += len(lines)
                # Each line should be valid JSON
                for line in lines:
                    data = json.loads(line)
                    assert "ts" in data
                    assert "doc_type" in data
                    assert "session_id" in data

        # Should have 5 total events (3 from session1, 2 from session2)
        assert total_lines == 5

    def test_export_with_session_filter(self, test_parquet_data, tmp_path):
        """Test exporting events for a specific session"""
        output_dir = tmp_path / "exports"

        files = export_to_jsonl(
            test_parquet_data["parquet_dir"],
            output_dir,
            session_id=test_parquet_data["session1_id"],
        )

        # Verify only session1 events are included
        total_lines = 0
        for filepath in files:
            with open(filepath) as f:
                for line in f:
                    data = json.loads(line)
                    assert data["session_id"] == test_parquet_data["session1_id"]
                    total_lines += 1

        # Session1 has 3 events
        assert total_lines == 3

    def test_export_with_doc_type_filter(self, test_parquet_data, tmp_path):
        """Test exporting events for a specific doc_type"""
        output_dir = tmp_path / "exports"

        files = export_to_jsonl(test_parquet_data["parquet_dir"], output_dir, doc_type="ws_event")

        # Should create only one file for ws_event
        assert len(files) == 1
        assert "ws_event" in files[0].name

        # Verify only ws_event events are included
        with open(files[0]) as f:
            for line in f:
                data = json.loads(line)
                assert data["doc_type"] == "ws_event"

    def test_export_with_both_filters(self, test_parquet_data, tmp_path):
        """Test exporting with both session and doc_type filters"""
        output_dir = tmp_path / "exports"

        files = export_to_jsonl(
            test_parquet_data["parquet_dir"],
            output_dir,
            session_id=test_parquet_data["session1_id"],
            doc_type="game_tick",
        )

        # Should create only one file
        assert len(files) == 1

        # Verify filtering worked correctly
        with open(files[0]) as f:
            lines = f.readlines()
            assert len(lines) == 1  # Session1 has 1 game_tick event
            data = json.loads(lines[0])
            assert data["session_id"] == test_parquet_data["session1_id"]
            assert data["doc_type"] == "game_tick"

    def test_export_no_matching_events(self, test_parquet_data, tmp_path, capsys):
        """Test exporting when no events match filters"""
        output_dir = tmp_path / "exports"

        files = export_to_jsonl(
            test_parquet_data["parquet_dir"], output_dir, session_id="non-existent-session"
        )

        # Should return empty list
        assert len(files) == 0

        # Should print message
        captured = capsys.readouterr()
        assert "No events found" in captured.out

    def test_export_creates_output_directory(self, test_parquet_data, tmp_path):
        """Test that export creates output directory if it doesn't exist"""
        output_dir = tmp_path / "nested" / "exports"

        # Directory doesn't exist yet
        assert not output_dir.exists()

        files = export_to_jsonl(test_parquet_data["parquet_dir"], output_dir)

        # Directory should be created
        assert output_dir.exists()
        assert len(files) > 0

    def test_export_jsonl_format(self, test_parquet_data, tmp_path):
        """Test that exported JSONL files have correct format"""
        output_dir = tmp_path / "exports"

        files = export_to_jsonl(test_parquet_data["parquet_dir"], output_dir, doc_type="game_tick")

        # Read the exported file
        with open(files[0]) as f:
            for line in f:
                data = json.loads(line)

                # Check required fields
                assert "ts" in data
                assert "source" in data
                assert "doc_type" in data
                assert "session_id" in data
                assert "seq" in data
                assert "direction" in data
                assert "raw_json" in data

                # Check type-specific fields for game_tick
                assert "tick" in data
                assert "price" in data
                assert "game_id" in data

                # None values should be removed
                for value in data.values():
                    assert value is not None

    def test_export_filename_format(self, test_parquet_data, tmp_path):
        """Test that exported files have correct naming format"""
        output_dir = tmp_path / "exports"

        files = export_to_jsonl(test_parquet_data["parquet_dir"], output_dir)

        for filepath in files:
            # Filename should be: YYYYMMDD_HHMMSS_<doc_type>.jsonl
            name = filepath.stem  # Without .jsonl extension
            parts = name.split("_")

            # Should have at least 3 parts: timestamp_timestamp_doctype
            assert len(parts) >= 3

            # First part should be date (YYYYMMDD)
            assert len(parts[0]) == 8
            assert parts[0].isdigit()

            # Second part should be time (HHMMSS)
            assert len(parts[1]) == 6
            assert parts[1].isdigit()

            # Remaining parts should be doc_type
            doc_type = "_".join(parts[2:])
            assert doc_type in ["ws_event", "game_tick", "player_action", "server_state"]


class TestCLI:
    """Tests for command-line interface"""

    def test_cli_export_all(self, test_parquet_data, tmp_path):
        """Test CLI exporting all events"""
        output_dir = tmp_path / "exports"
        env = os.environ.copy()
        env["RUGS_DATA_DIR"] = str(test_parquet_data["data_dir"])

        result = subprocess.run(
            [sys.executable, str(scripts_dir / "export_jsonl.py"), "--output", str(output_dir)],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        assert "Exported" in result.stdout
        assert len(list(output_dir.glob("*.jsonl"))) > 0

    def test_cli_export_with_session(self, test_parquet_data, tmp_path):
        """Test CLI with --session filter"""
        output_dir = tmp_path / "exports"
        env = os.environ.copy()
        env["RUGS_DATA_DIR"] = str(test_parquet_data["data_dir"])

        result = subprocess.run(
            [
                sys.executable,
                str(scripts_dir / "export_jsonl.py"),
                "--output",
                str(output_dir),
                "--session",
                test_parquet_data["session1_id"],
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        assert "Exported" in result.stdout

    def test_cli_export_with_doc_type(self, test_parquet_data, tmp_path):
        """Test CLI with --doc-type filter"""
        output_dir = tmp_path / "exports"
        env = os.environ.copy()
        env["RUGS_DATA_DIR"] = str(test_parquet_data["data_dir"])

        result = subprocess.run(
            [
                sys.executable,
                str(scripts_dir / "export_jsonl.py"),
                "--output",
                str(output_dir),
                "--doc-type",
                "ws_event",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        assert "Exported" in result.stdout

        # Should only have ws_event files
        files = list(output_dir.glob("*.jsonl"))
        assert len(files) == 1
        assert "ws_event" in files[0].name

    def test_cli_missing_output_arg(self):
        """Test CLI fails without --output argument"""
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "export_jsonl.py")],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "--output" in result.stderr

    def test_cli_missing_parquet_directory(self, tmp_path):
        """Test CLI fails when parquet directory doesn't exist"""
        output_dir = tmp_path / "exports"
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        env = os.environ.copy()
        env["RUGS_DATA_DIR"] = str(empty_dir)

        result = subprocess.run(
            [sys.executable, str(scripts_dir / "export_jsonl.py"), "--output", str(output_dir)],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 1
        assert "Parquet directory not found" in result.stderr

    def test_cli_custom_data_dir(self, test_parquet_data, tmp_path):
        """Test CLI with --data-dir argument"""
        output_dir = tmp_path / "exports"

        result = subprocess.run(
            [
                sys.executable,
                str(scripts_dir / "export_jsonl.py"),
                "--output",
                str(output_dir),
                "--data-dir",
                str(test_parquet_data["data_dir"]),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Exported" in result.stdout

    def test_cli_help(self):
        """Test CLI help message"""
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "export_jsonl.py"), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "--output" in result.stdout
        assert "--session" in result.stdout
        assert "--doc-type" in result.stdout
        assert "--data-dir" in result.stdout
        assert "Examples:" in result.stdout
