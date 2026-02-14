#!/usr/bin/env python3
"""
Analyze WebSocket event frequency before game rugs.

This script examines the hypothesis that event frequency changes
(increase or decrease) in the 1-3 seconds before a game rugs.
"""

import json
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def parse_timestamp(ts_str):
    """Parse ISO timestamp to datetime."""
    # Handle both formats: with and without timezone
    try:
        if "+" in ts_str or "Z" in ts_str:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return datetime.fromisoformat(ts_str)
    except Exception:
        return None


def find_rug_events(filepath):
    """
    Find rug events in a capture file.
    Returns list of (timestamp, game_id, rug_tick) tuples.
    """
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

                # Track gameStateUpdate for rug detection
                if event_type == "gameStateUpdate" and isinstance(data, dict):
                    game_id = data.get("gameId", "")
                    rugged = data.get("rugged", False)
                    tick = data.get("tickIndex", 0)

                    if game_id:
                        prev = last_game_state.get(game_id, {})

                        # Detect rug transition: rugged goes from false to true
                        if rugged and not prev.get("rugged", False):
                            rugs.append((ts, game_id, tick))

                        last_game_state[game_id] = {"rugged": rugged, "tick": tick, "ts": ts}
            except json.JSONDecodeError:
                continue
            except Exception as e:
                continue

    return rugs


def analyze_event_frequency(filepath, rug_time, window_seconds=5):
    """
    Analyze event frequency around a rug event.
    Returns dict with event counts per second before/after rug.
    """
    # Buckets: -5s, -4s, -3s, -2s, -1s, 0s (rug), +1s, +2s
    buckets = defaultdict(lambda: defaultdict(int))

    with open(filepath) as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                ts = parse_timestamp(record.get("ts", ""))
                event_type = record.get("event", "")

                if not ts:
                    continue

                # Calculate offset from rug time in seconds
                delta = (ts - rug_time).total_seconds()

                if -window_seconds <= delta <= 2:
                    bucket = int(delta) if delta >= 0 else int(delta) - (1 if delta % 1 else 0)
                    bucket = max(-window_seconds, min(2, bucket))
                    buckets[bucket][event_type] += 1
                    buckets[bucket]["_total"] += 1

            except Exception:
                continue

    return dict(buckets)


def main():
    capture_dir = Path("/home/devops/Desktop/VECTRA-PLAYER/src/rugs_recordings/raw_captures")

    # Find files with decent size (likely contain full games)
    files = sorted([f for f in capture_dir.glob("*.jsonl") if f.stat().st_size > 1_000_000])

    print(f"Analyzing {len(files)} capture files...\n")

    all_rug_patterns = []

    for filepath in files[:10]:  # Start with first 10 files
        print(f"Processing: {filepath.name}")
        rugs = find_rug_events(filepath)
        print(f"  Found {len(rugs)} rug events")

        for rug_ts, game_id, rug_tick in rugs:
            freq = analyze_event_frequency(filepath, rug_ts)
            if freq:
                all_rug_patterns.append(
                    {
                        "file": filepath.name,
                        "game_id": game_id,
                        "rug_tick": rug_tick,
                        "rug_time": rug_ts.isoformat(),
                        "frequency": freq,
                    }
                )

    print(f"\n{'=' * 60}")
    print(f"ANALYSIS RESULTS: {len(all_rug_patterns)} rug events analyzed")
    print(f"{'=' * 60}\n")

    if not all_rug_patterns:
        print("No rug events found!")
        return

    # Aggregate statistics
    print("EVENT FREQUENCY BY SECOND (relative to rug at t=0):\n")
    print(f"{'Second':<10} {'Avg Events':<15} {'Std Dev':<15} {'Min':<10} {'Max':<10}")
    print("-" * 60)

    for second in range(-5, 3):
        totals = []
        for pattern in all_rug_patterns:
            if second in pattern["frequency"]:
                totals.append(pattern["frequency"][second].get("_total", 0))
            else:
                totals.append(0)

        if totals:
            avg = statistics.mean(totals)
            std = statistics.stdev(totals) if len(totals) > 1 else 0
            label = f"t={second}s" + (" (RUG)" if second == 0 else "")
            print(f"{label:<10} {avg:<15.1f} {std:<15.1f} {min(totals):<10} {max(totals):<10}")

    # Event type breakdown for the critical window
    print(f"\n{'=' * 60}")
    print("EVENT TYPE BREAKDOWN (t=-3 to t=-1, the critical window):\n")

    event_counts = defaultdict(list)
    for pattern in all_rug_patterns:
        for second in [-3, -2, -1]:
            if second in pattern["frequency"]:
                for event_type, count in pattern["frequency"][second].items():
                    if event_type != "_total":
                        event_counts[event_type].append(count)

    print(f"{'Event Type':<30} {'Avg/sec':<15} {'Occurrences':<15}")
    print("-" * 60)
    for event_type, counts in sorted(event_counts.items(), key=lambda x: -sum(x[1])):
        avg = statistics.mean(counts) if counts else 0
        total = sum(counts)
        print(f"{event_type:<30} {avg:<15.2f} {total:<15}")

    # Look for patterns: compare t=-3,-2,-1 to t=-5,-4
    print(f"\n{'=' * 60}")
    print("PATTERN DETECTION: Comparing baseline (t=-5,-4) to pre-rug (t=-3,-2,-1)\n")

    baseline_rates = []
    prerug_rates = []

    for pattern in all_rug_patterns:
        baseline = sum(pattern["frequency"].get(s, {}).get("_total", 0) for s in [-5, -4]) / 2
        prerug = sum(pattern["frequency"].get(s, {}).get("_total", 0) for s in [-3, -2, -1]) / 3
        baseline_rates.append(baseline)
        prerug_rates.append(prerug)

    if baseline_rates and prerug_rates:
        avg_baseline = statistics.mean(baseline_rates)
        avg_prerug = statistics.mean(prerug_rates)
        change_pct = ((avg_prerug - avg_baseline) / avg_baseline * 100) if avg_baseline > 0 else 0

        print(f"Average baseline rate (t=-5,-4):  {avg_baseline:.1f} events/sec")
        print(f"Average pre-rug rate (t=-3,-2,-1): {avg_prerug:.1f} events/sec")
        print(f"Change: {change_pct:+.1f}%")

        # Count individual patterns
        increases = sum(1 for b, p in zip(baseline_rates, prerug_rates) if p > b * 1.1)
        decreases = sum(1 for b, p in zip(baseline_rates, prerug_rates) if p < b * 0.9)
        stable = len(baseline_rates) - increases - decreases

        print("\nPattern breakdown:")
        print(f"  Increases (>10%): {increases} ({increases / len(baseline_rates) * 100:.1f}%)")
        print(f"  Decreases (>10%): {decreases} ({decreases / len(baseline_rates) * 100:.1f}%)")
        print(f"  Stable (±10%):    {stable} ({stable / len(baseline_rates) * 100:.1f}%)")


if __name__ == "__main__":
    main()
