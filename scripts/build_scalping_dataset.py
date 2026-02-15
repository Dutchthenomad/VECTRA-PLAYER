#!/usr/bin/env python3
"""Build simulator-ready scalping datasets from complete_game parquet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export deduplicated game recordings for scalping explorer."
    )
    parser.add_argument(
        "--input-glob",
        default="/home/devops/rugs_data/events_parquet/doc_type=complete_game/**/*.parquet",
        help="Parquet glob for complete_game data.",
    )
    parser.add_argument(
        "--output-dir",
        default="/home/devops/rugs_data/exports/scalping_explorer",
        help="Directory for generated JSONL datasets.",
    )
    parser.add_argument(
        "--min-len",
        type=int,
        default=30,
        help="Minimum price array length for included games.",
    )
    parser.add_argument(
        "--quick-size",
        type=int,
        default=500,
        help="Row count for quick dataset.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()

    ranked_query = f"""
    WITH rows AS (
      SELECT
        game_id,
        date,
        ts,
        raw_json,
        json_array_length(json_extract(raw_json, '$.prices')) AS price_len
      FROM read_parquet('{args.input_glob}', hive_partitioning=1)
    ),
    ranked AS (
      SELECT *,
             ROW_NUMBER() OVER (
               PARTITION BY game_id
               ORDER BY COALESCE(price_len, -1) DESC, date DESC, ts DESC
             ) AS rn
      FROM rows
    )
    SELECT game_id, date, ts, raw_json, price_len
    FROM ranked
    WHERE rn = 1
      AND price_len IS NOT NULL
      AND price_len >= {args.min_len}
    ORDER BY date DESC, game_id;
    """

    rows = con.execute(ranked_query).fetchall()

    full_path = out_dir / f"scalping_unique_games_min{args.min_len}.jsonl"
    quick_path = out_dir / f"scalping_unique_games_min{args.min_len}_quick{args.quick_size}.jsonl"
    summary_path = out_dir / f"scalping_unique_games_min{args.min_len}_summary.json"

    lengths: list[int] = []
    records: list[dict] = []

    for game_id, date, ts, raw_json, price_len in rows:
        raw = json.loads(raw_json)
        prices = raw.get("prices")
        if not isinstance(prices, list):
            continue

        cleaned_prices = [float(v) for v in prices if isinstance(v, (int, float)) and float(v) > 0]
        if len(cleaned_prices) < args.min_len:
            continue

        record = {
            "game_id": game_id,
            "id": game_id,
            "date": str(date),
            "source_ts": ts,
            "source": "rugs_data.complete_game.best_row",
            "price_len": len(cleaned_prices),
            "peakMultiplier": raw.get("peakMultiplier"),
            "rugged": raw.get("rugged"),
            "prices": cleaned_prices,
        }
        records.append(record)
        lengths.append(len(cleaned_prices))

    with full_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, separators=(",", ":")) + "\n")

    quick_records = records[: args.quick_size]
    with quick_path.open("w", encoding="utf-8") as f:
        for rec in quick_records:
            f.write(json.dumps(rec, separators=(",", ":")) + "\n")

    lengths_sorted = sorted(lengths)

    def pct(p: float) -> int:
        if not lengths_sorted:
            return 0
        idx = int((len(lengths_sorted) - 1) * p)
        return lengths_sorted[idx]

    summary = {
        "input_glob": args.input_glob,
        "output_full": str(full_path),
        "output_quick": str(quick_path),
        "min_len": args.min_len,
        "quick_size": args.quick_size,
        "games_exported": len(records),
        "len_min": min(lengths) if lengths else 0,
        "len_avg": (sum(lengths) / len(lengths)) if lengths else 0,
        "len_p50": pct(0.5),
        "len_p90": pct(0.9),
        "len_max": max(lengths) if lengths else 0,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
