#!/usr/bin/env python3
"""
Export complete game data for Julius AI analysis

Creates two files:
1. games_summary.csv - One row per game
2. sidebets_detailed.csv - One row per sidebet with game context
"""

import json
from pathlib import Path

import duckdb
import pandas as pd

# Connect to DuckDB
conn = duckdb.connect()

print("📊 Exporting complete game data for Julius AI...")
print("=" * 70)

# ============================================================================
# File 1: Games Summary (one row per game)
# ============================================================================
print("\n1️⃣  Exporting games summary...")

df_games = conn.execute("""
    SELECT
        json_extract_string(raw_json, '$.id') as game_id,
        CAST(json_extract_string(raw_json, '$.timestamp') AS BIGINT) as timestamp,
        json_extract_string(raw_json, '$.gameVersion') as game_version,
        CAST(json_extract_string(raw_json, '$.rugged') AS BOOLEAN) as rugged,
        CAST(json_extract_string(raw_json, '$.peakMultiplier') AS DOUBLE) as peak_multiplier,
        json_array_length(raw_json, '$.globalSidebets') as sidebet_count,
        json_array_length(raw_json, '$.prices') as tick_count,
        json_extract_string(raw_json, '$.provablyFair.serverSeedHash') as server_seed_hash,
        ts as capture_time,
        session_id
    FROM read_parquet('~/rugs_data/events_parquet/doc_type=complete_game/**/*.parquet')
""").df()

# Remove duplicates (same game captured in both rug emissions)
df_games_unique = df_games.drop_duplicates(subset=["game_id"], keep="first")

output_file_1 = Path.home() / "rugs_data" / "exports" / "games_summary.csv"
output_file_1.parent.mkdir(parents=True, exist_ok=True)
df_games_unique.to_csv(output_file_1, index=False)

print(f"✅ Exported {len(df_games_unique)} unique games to:")
print(f"   {output_file_1}")

# ============================================================================
# File 2: Sidebets Detailed (one row per sidebet)
# ============================================================================
print("\n2️⃣  Exporting detailed sidebets...")

df_raw = conn.execute("""
    SELECT game_id, raw_json
    FROM read_parquet('~/rugs_data/events_parquet/doc_type=complete_game/**/*.parquet')
""").df()

# Flatten sidebets
sidebets = []
seen_games = set()

for _, row in df_raw.iterrows():
    game_id = row["game_id"]

    # Skip duplicate games (from 2nd rug emission)
    if game_id in seen_games:
        continue
    seen_games.add(game_id)

    game = json.loads(row["raw_json"])
    peak = game.get("peakMultiplier", 0)
    tick_count = len(game.get("prices", []))

    for bet in game.get("globalSidebets", []):
        sidebets.append(
            {
                "game_id": game_id,
                "game_timestamp": game.get("timestamp"),
                "game_peak_multiplier": peak,
                "game_tick_count": tick_count,
                "game_rugged": game.get("rugged"),
                # Sidebet details
                "player_id": bet.get("playerId"),
                "username": bet.get("username"),
                "bet_amount_sol": bet.get("betAmount"),
                "target_multiplier": bet.get("xPayout"),
                "entry_tick": bet.get("startedAtTick"),
                "exit_tick": bet.get("end"),
                # Calculated fields
                "duration_ticks": bet.get("end", 0) - bet.get("startedAtTick", 0),
                "won": peak >= bet.get("xPayout", 999),
                "payout_sol": bet.get("betAmount", 0) * bet.get("xPayout", 0)
                if peak >= bet.get("xPayout", 999)
                else 0,
                "profit_sol": (
                    bet.get("betAmount", 0) * bet.get("xPayout", 0) - bet.get("betAmount", 0)
                )
                if peak >= bet.get("xPayout", 999)
                else -bet.get("betAmount", 0),
            }
        )

df_sidebets = pd.DataFrame(sidebets)

output_file_2 = Path.home() / "rugs_data" / "exports" / "sidebets_detailed.csv"
df_sidebets.to_csv(output_file_2, index=False)

print(f"✅ Exported {len(df_sidebets)} sidebets to:")
print(f"   {output_file_2}")

# ============================================================================
# Summary Statistics
# ============================================================================
print("\n" + "=" * 70)
print("📈 SUMMARY STATISTICS")
print("=" * 70)

print("\nGames:")
print(f"  Total unique games: {len(df_games_unique)}")
print(f"  Avg peak multiplier: {df_games_unique['peak_multiplier'].mean():.2f}x")
print(f"  Avg ticks per game: {df_games_unique['tick_count'].mean():.1f}")

print("\nSidebets:")
print(f"  Total sidebets: {len(df_sidebets)}")
print(f"  Win rate: {(df_sidebets['won'].sum() / len(df_sidebets) * 100):.1f}%")
print(f"  Avg bet size: {df_sidebets['bet_amount_sol'].mean():.4f} SOL")
print(f"  Total volume: {df_sidebets['bet_amount_sol'].sum():.2f} SOL")
print(f"  Net profit/loss: {df_sidebets['profit_sol'].sum():.2f} SOL")

print("\n" + "=" * 70)
print("🎯 UPLOAD TO JULIUS AI:")
print("=" * 70)
print("\n1. Go to https://julius.ai")
print("2. Upload BOTH files:")
print(f"   - {output_file_1.name}")
print(f"   - {output_file_2.name}")
print("\n3. Try these questions:")
print("   • 'What's the sidebet win rate by target multiplier?'")
print("   • 'Show correlation between game peak and number of sidebets'")
print("   • 'Plot profit/loss distribution across players'")
print("   • 'Which entry ticks have the highest win rate?'")
print("   • 'Show price trajectory patterns for games with high sidebet activity'")
print()
