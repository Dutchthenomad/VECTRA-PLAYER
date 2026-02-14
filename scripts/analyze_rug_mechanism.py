#!/usr/bin/env python3
"""
Analyze the rug mechanism - when and how games liquidate
"""

import json

import duckdb
import numpy as np

conn = duckdb.connect()
df = conn.execute("""
    SELECT game_id, raw_json
    FROM read_parquet('~/rugs_data/events_parquet/doc_type=complete_game/**/*.parquet')
""").df()

print("💥 RUG MECHANISM ANALYSIS")
print("=" * 70)

rug_drops = []
seen = set()

for _, row in df.iterrows():
    game_id = row["game_id"]
    if game_id in seen:
        continue
    seen.add(game_id)

    game = json.loads(row["raw_json"])
    prices = game.get("prices", [])

    if len(prices) < 2:
        continue

    # Find the rug point (largest single-tick drop)
    max_drop = 0
    max_drop_idx = 0

    for i in range(1, len(prices)):
        drop = prices[i - 1] - prices[i]
        if drop > max_drop:
            max_drop = drop
            max_drop_idx = i

    # Analyze the rug
    rug_drops.append(
        {
            "game_id": game_id[-8:],
            "peak": game.get("peakMultiplier", 0),
            "total_ticks": len(prices),
            "rug_tick": max_drop_idx,
            "price_before_rug": prices[max_drop_idx - 1],
            "price_after_rug": prices[max_drop_idx],
            "drop_amount": max_drop,
            "drop_percent": (max_drop / prices[max_drop_idx - 1] * 100)
            if prices[max_drop_idx - 1] > 0
            else 0,
            "final_price": prices[-1],
            "ticks_after_rug": len(prices) - max_drop_idx - 1,
        }
    )

# Sort by drop percent
rug_drops.sort(key=lambda x: x["drop_percent"], reverse=True)

print("\nTop 10 Largest Rug Drops:")
print(
    f"{'Game':<10} {'Before':<10} {'After':<10} {'Drop %':<10} {'Rug Tick':<12} {'Ticks After':<12}"
)
print("-" * 70)

for rug in rug_drops[:10]:
    print(
        f"{rug['game_id']:<10} {rug['price_before_rug']:<10.4f} {rug['price_after_rug']:<10.6f} "
        f"{rug['drop_percent']:<10.1f} {rug['rug_tick']:<12} {rug['ticks_after_rug']:<12}"
    )

# Analyze rug timing
rug_ticks = [r["rug_tick"] for r in rug_drops]
total_ticks = [r["total_ticks"] for r in rug_drops]
rug_positions = [r["rug_tick"] / r["total_ticks"] * 100 for r in rug_drops]

print("\n📊 Rug Timing Statistics:")
print(f"  Avg rug occurs at tick: {np.mean(rug_ticks):.1f}")
print(f"  Avg position in game: {np.mean(rug_positions):.1f}% through")
print(f"  Avg drop size: {np.mean([r['drop_amount'] for r in rug_drops]):.4f}")
print(f"  Avg drop percent: {np.mean([r['drop_percent'] for r in rug_drops]):.1f}%")

# 0.02x floor analysis
rugs_at_02 = [r for r in rug_drops if abs(r["price_after_rug"] - 0.02) < 0.001]
rugs_below_02 = [r for r in rug_drops if r["price_after_rug"] < 0.019]

print("\n🎯 Rug Destination:")
print(f"  Rugs to ~0.02x: {len(rugs_at_02)} ({len(rugs_at_02) / len(rug_drops) * 100:.1f}%)")
print(
    f"  Rugs below 0.02x: {len(rugs_below_02)} ({len(rugs_below_02) / len(rug_drops) * 100:.1f}%)"
)

# House take calculation
print("\n💰 House Liquidation Calculation:")
print("  When rug happens at 1.0x → 0.02x:")
print("    Price drops: 98% instantly")
print("    All positions @ 1.0x are liquidated")
print("    House keeps: 100% of liquidated value")
print("  ")
avg_ticks = np.mean(total_ticks)
tick_fee_total = 0.0005 * avg_ticks * 100
print(f"  Plus: 0.05% per tick fee × {avg_ticks:.0f} avg ticks = {tick_fee_total:.1f}% total")
print("  ")
print("  Total house edge: Liquidation value + tick fees")
