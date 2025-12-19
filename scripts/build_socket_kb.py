#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENTS = ["gameStateUpdate", "playerUpdate"]


@dataclass
class FieldRow:
    event_name: str
    json_path: str
    cardinality: str
    inferred_type: str
    nullable_seen: bool
    occurrences: int
    example_value: str
    group: str
    scope: str
    units: str
    meaning: str
    notes: str


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _merge_field_rows(existing: FieldRow, incoming: dict[str, str]) -> FieldRow:
    def pick(first: str, second: str) -> str:
        return first or second

    cardinality = existing.cardinality
    if incoming.get("cardinality") and incoming["cardinality"] != existing.cardinality:
        cardinality = "mixed"

    inferred_type = existing.inferred_type
    if incoming.get("inferred_type") and incoming["inferred_type"] != existing.inferred_type:
        inferred_type = "mixed"

    nullable_seen = existing.nullable_seen or incoming.get("nullable_seen", "").lower() == "true"
    occurrences = existing.occurrences + int(incoming.get("occurrences") or 0)

    example_value = existing.example_value or incoming.get("example_value", "")

    return FieldRow(
        event_name=existing.event_name,
        json_path=existing.json_path,
        cardinality=cardinality,
        inferred_type=inferred_type,
        nullable_seen=nullable_seen,
        occurrences=occurrences,
        example_value=example_value,
        group=pick(existing.group, incoming.get("group", "")),
        scope=pick(existing.scope, incoming.get("scope", "")),
        units=pick(existing.units, incoming.get("units", "")),
        meaning=pick(existing.meaning, incoming.get("meaning", "")),
        notes=pick(existing.notes, incoming.get("notes", "")),
    )


def _load_field_dictionary(event_name: str, event_dir: Path) -> list[FieldRow]:
    rows: dict[tuple[str, str], FieldRow] = {}
    for csv_path in event_dir.glob("data_dictionary.generated*.csv"):
        for row in _read_csv_rows(csv_path):
            if row.get("event_name") != event_name:
                continue
            key = (row.get("event_name", ""), row.get("json_path", ""))
            if key in rows:
                rows[key] = _merge_field_rows(rows[key], row)
                continue
            rows[key] = FieldRow(
                event_name=row.get("event_name", ""),
                json_path=row.get("json_path", ""),
                cardinality=row.get("cardinality", ""),
                inferred_type=row.get("inferred_type", ""),
                nullable_seen=row.get("nullable_seen", "").lower() == "true",
                occurrences=int(row.get("occurrences") or 0),
                example_value=row.get("example_value", ""),
                group=row.get("group", ""),
                scope=row.get("scope", ""),
                units=row.get("units", ""),
                meaning=row.get("meaning", ""),
                notes=row.get("notes", ""),
            )
    return list(rows.values())


def _extract_examples(event_dir: Path, event_name: str) -> list[dict[str, Any]]:
    examples_dir = event_dir / "examples"
    if not examples_dir.exists():
        return []
    examples = []
    for json_path in sorted(examples_dir.glob("*.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if payload.get("event") != event_name:
            continue
        data = payload.get("data") or {}
        examples.append(
            {
                "event_name": event_name,
                "seq": payload.get("seq"),
                "ts": payload.get("ts"),
                "game_id": data.get("gameId"),
                "raw_json_path": str(json_path),
                "notes": "",
            }
        )
    return examples


def _ensure_tables(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ws_event_examples (
            event_name TEXT,
            seq BIGINT,
            ts TEXT,
            game_id TEXT,
            raw_json_path TEXT,
            notes TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ws_field_dictionary (
            event_name TEXT,
            json_path TEXT,
            cardinality TEXT,
            inferred_type TEXT,
            nullable_seen BOOLEAN,
            occurrences BIGINT,
            example_value TEXT,
            "group" TEXT,
            scope TEXT,
            units TEXT,
            meaning TEXT,
            notes TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ws_event_summaries (
            event_name TEXT,
            summary TEXT,
            status TEXT,
            last_reviewed TEXT,
            notes TEXT
        )
        """
    )


def _upsert_summaries(conn: duckdb.DuckDBPyConnection, event_names: list[str]) -> None:
    existing = {
        row[0] for row in conn.execute("SELECT event_name FROM ws_event_summaries").fetchall()
    }
    now = datetime.now(timezone.utc).isoformat()
    for event_name in event_names:
        if event_name in existing:
            continue
        conn.execute(
            """
            INSERT INTO ws_event_summaries (event_name, summary, status, last_reviewed, notes)
            VALUES (?, '', 'draft', ?, '')
            """,
            [event_name, now],
        )


def _export_jsonl(conn: duckdb.DuckDBPyConnection, out_path: Path) -> None:
    docs = []
    for row in conn.execute(
        """
        SELECT event_name, json_path, cardinality, inferred_type, nullable_seen,
               occurrences, example_value, "group", scope, units, meaning, notes
        FROM ws_field_dictionary
        ORDER BY event_name, json_path
        """
    ).fetchall():
        (
            event_name,
            json_path,
            cardinality,
            inferred_type,
            nullable_seen,
            occurrences,
            example_value,
            group,
            scope,
            units,
            meaning,
            notes,
        ) = row
        text = (
            f"{event_name} {json_path} ({cardinality}, {inferred_type}) "
            f"nullable={bool(nullable_seen)} occurrences={occurrences}. "
            f"Meaning: {meaning or 'TBD'}. Units: {units or 'n/a'}. "
            f"Scope: {scope or 'n/a'}. Group: {group or 'n/a'}. "
            f"Example: {example_value or 'n/a'}."
        )
        docs.append(
            {
                "doc_type": "field",
                "event_name": event_name,
                "json_path": json_path,
                "text": text,
                "source": "ws_field_dictionary",
            }
        )

    for row in conn.execute(
        """
        SELECT event_name, summary, status, last_reviewed, notes
        FROM ws_event_summaries
        ORDER BY event_name
        """
    ).fetchall():
        event_name, summary, status, last_reviewed, notes = row
        text = (
            f"{event_name} summary: {summary or 'TBD'}. "
            f"Status: {status or 'n/a'}. Last reviewed: {last_reviewed or 'n/a'}."
        )
        docs.append(
            {
                "doc_type": "summary",
                "event_name": event_name,
                "text": text,
                "source": "ws_event_summaries",
                "notes": notes or "",
            }
        )

    for row in conn.execute(
        """
        SELECT event_name, seq, ts, game_id, raw_json_path, notes
        FROM ws_event_examples
        ORDER BY event_name, seq
        """
    ).fetchall():
        event_name, seq, ts, game_id, raw_json_path, notes = row
        text = (
            f"{event_name} example seq={seq} ts={ts} game_id={game_id or 'n/a'} "
            f"stored at {raw_json_path}."
        )
        docs.append(
            {
                "doc_type": "example",
                "event_name": event_name,
                "seq": seq,
                "ts": ts,
                "game_id": game_id,
                "raw_json_path": raw_json_path,
                "text": text,
                "source": "ws_event_examples",
                "notes": notes or "",
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a canonical DuckDB + JSONL knowledge base for websocket events."
    )
    parser.add_argument(
        "--events",
        nargs="*",
        default=DEFAULT_EVENTS,
        help="Event names to include (default: gameStateUpdate, playerUpdate)",
    )
    parser.add_argument(
        "--out-duckdb",
        default=str(ROOT / "docs" / "rag" / "socket_kb.duckdb"),
        help="DuckDB output path",
    )
    parser.add_argument(
        "--out-jsonl",
        default=str(ROOT / "docs" / "rag" / "socket_kb.jsonl"),
        help="JSONL output path for RAG ingestion",
    )
    args = parser.parse_args()

    conn = duckdb.connect(args.out_duckdb)
    _ensure_tables(conn)

    for event_name in args.events:
        event_dir = ROOT / "docs" / "spreadsheets" / "ws_events" / event_name
        if not event_dir.exists():
            continue

        conn.execute("DELETE FROM ws_field_dictionary WHERE event_name = ?", [event_name])
        conn.execute("DELETE FROM ws_event_examples WHERE event_name = ?", [event_name])

        field_rows = _load_field_dictionary(event_name, event_dir)
        for row in field_rows:
            conn.execute(
                """
                INSERT INTO ws_field_dictionary (
                    event_name, json_path, cardinality, inferred_type, nullable_seen,
                    occurrences, example_value, "group", scope, units, meaning, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    row.event_name,
                    row.json_path,
                    row.cardinality,
                    row.inferred_type,
                    row.nullable_seen,
                    row.occurrences,
                    row.example_value,
                    row.group,
                    row.scope,
                    row.units,
                    row.meaning,
                    row.notes,
                ],
            )

        for example in _extract_examples(event_dir, event_name):
            conn.execute(
                """
                INSERT INTO ws_event_examples (
                    event_name, seq, ts, game_id, raw_json_path, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    example["event_name"],
                    example["seq"],
                    example["ts"],
                    example["game_id"],
                    example["raw_json_path"],
                    example["notes"],
                ],
            )

    _upsert_summaries(conn, args.events)
    _export_jsonl(conn, Path(args.out_jsonl))
    conn.close()

    print(f"Wrote DuckDB KB: {args.out_duckdb}")
    print(f"Wrote JSONL KB: {args.out_jsonl}")


if __name__ == "__main__":
    main()
