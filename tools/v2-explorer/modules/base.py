"""
Base data structures for the v2-explorer replay engine.

ReplayResult: Summary of a replayed game (Gate 1)
TracedReplayResult: Full per-tick pipeline trace (Gate 2)
"""

from dataclasses import dataclass, field


@dataclass
class ReplayResult:
    """Summary result from replaying a game through the sidebet pipeline."""

    game_id: str
    ticks: int
    rug_tick: int
    peak_price: float
    bets_placed: int
    bets_won: int
    bets_lost: int
    net_pnl: float
    final_bankroll: float
    decisions: list[dict] = field(default_factory=list)


@dataclass
class TracedReplayResult(ReplayResult):
    """Extended replay result with per-tick pipeline trace data.

    Each entry in tick_traces contains the full 5-stage pipeline output:
    features, model_a, model_b, arbitration, and risk state.
    """

    tick_traces: list[dict] = field(default_factory=list)
