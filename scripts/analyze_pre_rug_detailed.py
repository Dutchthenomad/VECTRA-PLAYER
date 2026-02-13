#!/usr/bin/env python3
"""
Detailed analysis of event frequency with sub-second granularity.
Focus on gameStateUpdate specifically (the tick stream).
"""

import json
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def parse_timestamp(ts_str):
    try:
        if "+" in ts_str or "Z" in ts_str:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return datetime.fromisoformat(ts_str)
    except Exception:
        return None


def find_rug_events(filepath):
    """Find rug events by detecting rugged: false -> true transitions."""
    rugs = []
    last_game_state = {}

    with open(filepath) as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                event_type = record.get("event", "")
                data = record.get("data", {})
                ts = parse_timestamp(record.get("ts", ""))

                if not ts or not data:
                    continue

                if event_type == "gameStateUpdate" and isinstance(data, dict):
                    game_id = data.get("gameId", "")
                    rugged = data.get("rugged", False)
                    tick = data.get("tickIndex", 0)
                    price = data.get("price", 0)

                    if game_id:
                        prev = last_game_state.get(game_id, {})

                        if rugged and not prev.get("rugged", False):
                            rugs.append(
                                {
                                    "ts": ts,
                                    "game_id": game_id,
                                    "tick": tick,
                                    "price": price,
                                    "prev_tick": prev.get("tick", 0),
                                    "prev_price": prev.get("price", 0),
                                }
                            )

                        last_game_state[game_id] = {
                            "rugged": rugged,
                            "tick": tick,
                            "price": price,
                            "ts": ts,
                        }
            except Exception:
                continue

    return rugs


def analyze_with_granularity(filepath, rug_time, bucket_ms=250, window_seconds=5):
    """
    Analyze event frequency with sub-second granularity.
    Returns dict with event counts per bucket.
    """
    buckets = defaultdict(
        lambda: {"gameStateUpdate": 0, "playerUpdate": 0, "newTrade": 0, "other": 0, "total": 0}
    )

    with open(filepath) as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                ts = parse_timestamp(record.get("ts", ""))
                event_type = record.get("event", "")

                if not ts:
                    continue

                delta_ms = (ts - rug_time).total_seconds() * 1000

                if -window_seconds * 1000 <= delta_ms <= 1000:
                    bucket = int(delta_ms // bucket_ms) * bucket_ms

                    if event_type == "gameStateUpdate":
                        buckets[bucket]["gameStateUpdate"] += 1
                    elif event_type in ("playerUpdate", "gameStatePlayerUpdate"):
                        buckets[bucket]["playerUpdate"] += 1
                    elif "Trade" in event_type or "trade" in event_type:
                        buckets[bucket]["newTrade"] += 1
                    else:
                        buckets[bucket]["other"] += 1

                    buckets[bucket]["total"] += 1

            except Exception:
                continue

    return dict(buckets)


def main():
    capture_dir = Path("/home/devops/Desktop/VECTRA-PLAYER/src/rugs_recordings/raw_captures")
    files = sorted([f for f in capture_dir.glob("*.jsonl") if f.stat().st_size > 5_000_000])

    print(f"Analyzing {len(files)} larger capture files for detailed patterns...\n")

    all_patterns = []

    for filepath in files[:15]:  # Analyze more files
        print(f"Processing: {filepath.name}", end=" ")
        rugs = find_rug_events(filepath)
        print(f"({len(rugs)} rugs)")

        for rug in rugs:
            freq = analyze_with_granularity(filepath, rug["ts"])
            if freq:
                all_patterns.append(
                    {
                        "file": filepath.name,
                        "game_id": rug["game_id"],
                        "rug_tick": rug["tick"],
                        "rug_price": rug["price"],
                        "frequency": freq,
                    }
                )

    print(f"\n{'=' * 70}")
    print(f"DETAILED ANALYSIS: {len(all_patterns)} rug events")
    print(f"{'=' * 70}\n")

    if not all_patterns:
        print("No rug events found!")
        return

    # 250ms bucket analysis
    print("gameStateUpdate FREQUENCY (250ms buckets, before rug at t=0):\n")
    print(f"{'Time':<12} {'Avg GSU':<12} {'Std Dev':<12} {'% with 0':<12}")
    print("-" * 50)

    buckets_to_show = [
        -3000,
        -2750,
        -2500,
        -2250,
        -2000,
        -1750,
        -1500,
        -1250,
        -1000,
        -750,
        -500,
        -250,
        0,
        250,
        500,
    ]

    for bucket in buckets_to_show:
        gsu_counts = []
        for pattern in all_patterns:
            gsu = pattern["frequency"].get(bucket, {}).get("gameStateUpdate", 0)
            gsu_counts.append(gsu)

        if gsu_counts:
            avg = statistics.mean(gsu_counts)
            std = statistics.stdev(gsu_counts) if len(gsu_counts) > 1 else 0
            zero_pct = sum(1 for c in gsu_counts if c == 0) / len(gsu_counts) * 100

            label = f"{bucket}ms"
            if bucket == 0:
                label += " (RUG)"
            print(f"{label:<12} {avg:<12.2f} {std:<12.2f} {zero_pct:<12.1f}%")

    # Analyze the "gap" pattern - looking for missing ticks
    print(f"\n{'=' * 70}")
    print("TICK GAP ANALYSIS: Looking for periods with zero gameStateUpdate\n")

    gap_before_rug = []
    for pattern in all_patterns:
        # Count 250ms buckets with 0 gameStateUpdate in the -1500ms to -250ms window
        gaps = 0
        for bucket in [-1500, -1250, -1000, -750, -500, -250]:
            if pattern["frequency"].get(bucket, {}).get("gameStateUpdate", 0) == 0:
                gaps += 1
        gap_before_rug.append(gaps)

    print("Number of 250ms gaps in final 1.5s before rug:")
    print(f"  Average gaps: {statistics.mean(gap_before_rug):.1f}")
    print(f"  Max gaps: {max(gap_before_rug)}")
    print(
        f"  Rugs with ≥1 gap: {sum(1 for g in gap_before_rug if g >= 1)} ({sum(1 for g in gap_before_rug if g >= 1) / len(gap_before_rug) * 100:.1f}%)"
    )
    print(
        f"  Rugs with ≥2 gaps: {sum(1 for g in gap_before_rug if g >= 2)} ({sum(1 for g in gap_before_rug if g >= 2) / len(gap_before_rug) * 100:.1f}%)"
    )

    # Compare to baseline window (-3000ms to -1500ms)
    print(f"\n{'=' * 70}")
    print("BASELINE vs PRE-RUG COMPARISON (gameStateUpdate only)\n")

    baseline_gaps = []
    for pattern in all_patterns:
        gaps = 0
        for bucket in [-3000, -2750, -2500, -2250, -2000, -1750]:
            if pattern["frequency"].get(bucket, {}).get("gameStateUpdate", 0) == 0:
                gaps += 1
        baseline_gaps.append(gaps)

    print(f"Baseline window (-3s to -1.5s): {statistics.mean(baseline_gaps):.1f} avg gaps")
    print(f"Pre-rug window (-1.5s to 0s):   {statistics.mean(gap_before_rug):.1f} avg gaps")

    if statistics.mean(baseline_gaps) > 0:
        change = (
            (statistics.mean(gap_before_rug) - statistics.mean(baseline_gaps))
            / statistics.mean(baseline_gaps)
            * 100
        )
        print(f"Change: {change:+.1f}%")

    # Look at inter-arrival times of gameStateUpdate
    print(f"\n{'=' * 70}")
    print("INDIVIDUAL RUG PROFILES (showing last 2 seconds):\n")

    for i, pattern in enumerate(all_patterns[:5]):  # Show first 5 detailed
        print(
            f"Game {pattern['game_id'][:20]}... (tick {pattern['rug_tick']}, price {pattern['rug_price']:.4f})"
        )

        row = "  "
        for bucket in [-2000, -1750, -1500, -1250, -1000, -750, -500, -250, 0]:
            gsu = pattern["frequency"].get(bucket, {}).get("gameStateUpdate", 0)
            row += f"{gsu:>3} "
        print(row)
        print(
            f"  {'-2s':<3} {'-1.75':>3} {'-1.5':>3} {'-1.25':>3} {'-1s':>4} {'-0.75':>4} {'-0.5':>4} {'-0.25':>4} {'RUG':>4}"
        )
        print()


if __name__ == "__main__":
    main()
