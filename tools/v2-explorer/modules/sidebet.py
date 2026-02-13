"""
Sidebet pipeline module for v2-explorer.

Implements the full 5-stage sidebet decision pipeline:
  1. Feature extraction (16 features)
  2. Model A: BayesianSurvivalModel  (p_rug)
  3. Model B: SimpleBayesianForecaster (regime/duration prediction)
  4. Arbitration: consensus decision from Models A+B
  5. Risk management: position sizing and state machine

Provides:
  - replay_game()        -> ReplayResult  (Gate 1 — decision summary)
  - replay_game_traced() -> TracedReplayResult (Gate 2 — per-tick trace)
"""

from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve imports — the analysis modules live in notebooks/
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Try multiple locations: local dev layout and Docker volume mount
_NOTEBOOKS_CANDIDATES = [
    _REPO_ROOT / "notebooks",  # Docker: /app/notebooks
    _REPO_ROOT.parent / "notebooks",  # Local: repo_root/../notebooks → repo/notebooks
    Path("/app/notebooks"),  # Docker fallback: explicit mount path
]

for _nb in _NOTEBOOKS_CANDIDATES:
    if _nb.is_dir() and str(_nb) not in sys.path:
        sys.path.insert(0, str(_nb))
        break

# Re-use existing code rather than duplicating
from bayesian_sidebet_analysis import (
    BayesianSurvivalModel,
    expected_value,
    extract_features,
    load_game_data,
)

from .base import ReplayResult, TracedReplayResult

# ============================================================================
# Stage 3 — SimpleBayesianForecaster (lightweight, no external deps)
# ============================================================================


class SimpleBayesianForecaster:
    """Simplified Bayesian forecaster for regime/duration prediction.

    Re-implemented locally to avoid circular import issues with the
    prediction_engine module (which pulls in asyncio/threading).
    """

    def __init__(self):
        self.final_mu = 0.0135
        self.final_sigma = 0.0050
        self.peak_mu = 2.5
        self.peak_sigma = 1.5
        self.duration_mu = 200
        self.duration_sigma = 150
        self.history: list[dict] = []
        self.theta = 0.30

    def update(self, final_price: float, peak: float, duration: int):
        self.history.append({"final": final_price, "peak": peak, "duration": duration})
        alpha = 0.15
        self.final_mu = (1 - alpha) * self.final_mu + alpha * final_price
        self.peak_mu = (1 - alpha) * self.peak_mu + alpha * peak
        self.duration_mu = (1 - alpha) * self.duration_mu + alpha * duration
        if len(self.history) >= 5:
            import statistics

            recent = self.history[-10:]
            self.final_sigma = (
                statistics.stdev(h["final"] for h in recent)
                if len(recent) > 1
                else self.final_sigma
            )
            self.peak_sigma = (
                statistics.stdev(h["peak"] for h in recent) if len(recent) > 1 else self.peak_sigma
            )
            self.duration_sigma = (
                statistics.stdev(h["duration"] for h in recent)
                if len(recent) > 1
                else self.duration_sigma
            )

    def predict(self) -> dict:
        prev = self.history[-1] if self.history else None
        peak_point = self.peak_mu
        duration_point = self.duration_mu
        if prev:
            deviation = (prev["final"] - 0.0135) / 0.005
            peak_adj = max(0.7, min(1.3, 1.0 - 0.15 * deviation))
            peak_point *= peak_adj
            if prev["peak"] > 5.0:
                duration_point *= 0.55
            elif prev["peak"] > 2.0:
                duration_point *= 0.80
        regime = self._detect_regime(prev)
        confidence = 0.65
        if prev:
            z = abs(prev["final"] - self.final_mu) / max(self.final_sigma, 0.001)
            confidence += min(0.15, 0.05 * z)
        return {
            "predicted_peak": round(peak_point, 4),
            "predicted_duration": int(duration_point),
            "regime": regime,
            "confidence": round(confidence, 4),
        }

    def _detect_regime(self, prev: dict | None) -> str:
        if not prev:
            return "normal"
        z = (prev["final"] - self.final_mu) / max(self.final_sigma, 0.001)
        if z < -1.5:
            return "suppressed"
        if z > 1.5:
            return "inflated"
        if abs(z) > 2.0:
            return "volatile"
        return "normal"


# ============================================================================
# Stage 4 — ArbitrationEngine
# ============================================================================

# Consensus matrix: (bucket, regime) -> size_key
# size_key is None when models disagree (no bet)
_CONSENSUS_MATRIX: dict[tuple[str, str], str | None] = {
    ("low", "normal"): None,
    ("low", "suppressed"): None,
    ("low", "inflated"): None,
    ("low", "volatile"): None,
    ("medium", "normal"): "quarter",
    ("medium", "suppressed"): "half",
    ("medium", "inflated"): None,
    ("medium", "volatile"): "quarter",
    ("high", "normal"): "half",
    ("high", "suppressed"): "full",
    ("high", "inflated"): "quarter",
    ("high", "volatile"): "half",
    ("critical", "normal"): "full",
    ("critical", "suppressed"): "full",
    ("critical", "inflated"): "half",
    ("critical", "volatile"): "full",
}

_SIZE_MODIFIERS: dict[str | None, float] = {
    None: 0.0,
    "quarter": 0.25,
    "half": 0.50,
    "full": 1.0,
}


class ArbitrationEngine:
    """Bridges Model A + Model B into an actionable BET/WAIT recommendation."""

    MIN_TICK = 50  # Don't bet before tick 50
    MIN_P_RUG = 0.16  # Below 5x breakeven → veto

    def _check_vetoes(self, p_rug: float, context: dict) -> tuple[bool, str]:
        """Return (vetoed: bool, veto_reason: str)."""
        tick = context.get("tick", 0)
        features = context.get("features")
        if tick < self.MIN_TICK:
            return True, f"game_too_young (tick {tick} < {self.MIN_TICK})"
        if p_rug < self.MIN_P_RUG:
            return True, f"p_rug_below_breakeven ({p_rug:.3f} < {self.MIN_P_RUG})"
        if features and getattr(features, "rapid_rise", False):
            return True, "rapid_rise_momentum"
        return False, ""

    @staticmethod
    def _get_rug_bucket(p_rug: float) -> str:
        if p_rug >= 0.60:
            return "critical"
        if p_rug >= 0.35:
            return "high"
        if p_rug >= 0.20:
            return "medium"
        return "low"

    @staticmethod
    def _apply_duration_gate(bucket: str, model_b_signal: dict, tick: int) -> str:
        """Upgrade bucket if Model B predicts game is near its end."""
        predicted_duration = model_b_signal.get("predicted_duration", 999)
        remaining = predicted_duration - tick
        if remaining < 40 and bucket in ("low", "medium"):
            return {"low": "medium", "medium": "high"}[bucket]
        return bucket

    @staticmethod
    def _lookup_consensus(bucket: str, regime: str) -> str | None:
        return _CONSENSUS_MATRIX.get((bucket, regime))

    def evaluate(self, p_rug: float, model_b_signal: dict, context: dict) -> dict:
        """Full arbitration: vetoes → bucket → duration gate → consensus."""
        vetoed, veto_reason = self._check_vetoes(p_rug, context)
        if vetoed:
            return {
                "action": "WAIT",
                "bucket": self._get_rug_bucket(p_rug),
                "bucket_upgraded": self._get_rug_bucket(p_rug),
                "consensus_lookup": None,
                "size_modifier": 0.0,
                "reason": veto_reason,
                "vetoed": True,
                "veto_reason": veto_reason,
            }

        tick = context.get("tick", 0)
        bucket = self._get_rug_bucket(p_rug)
        bucket_upgraded = self._apply_duration_gate(bucket, model_b_signal, tick)
        regime = model_b_signal.get("regime", "normal")
        size_key = self._lookup_consensus(bucket_upgraded, regime)
        size_modifier = _SIZE_MODIFIERS.get(size_key, 0.0)

        action = "BET" if size_key is not None else "WAIT"
        if action == "WAIT":
            reason = f"no_consensus ({bucket_upgraded}/{regime})"
        else:
            reason = f"consensus_{size_key} ({bucket_upgraded}/{regime})"

        return {
            "action": action,
            "bucket": bucket,
            "bucket_upgraded": bucket_upgraded,
            "consensus_lookup": size_key,
            "size_modifier": size_modifier,
            "reason": reason,
            "vetoed": False,
            "veto_reason": "",
        }


# ============================================================================
# Stage 5 — Lightweight RiskManager (no matplotlib dependency)
# ============================================================================


class TradingState(str, Enum):
    ACTIVE = "active"
    REDUCED = "reduced"
    PAUSED = "paused"
    RECOVERY = "recovery"


class RiskManager:
    """Position sizing + state machine for replay."""

    def __init__(self, initial_bankroll: float = 1.0):
        self.bankroll = initial_bankroll
        self.peak_bankroll = initial_bankroll
        self.state = TradingState.ACTIVE
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.kelly_fraction = 0.25
        self.payout = 5

    @property
    def drawdown_pct(self) -> float:
        if self.peak_bankroll <= 0:
            return 0.0
        return (self.peak_bankroll - self.bankroll) / self.peak_bankroll * 100

    def calculate_position(self, p_win: float) -> float:
        if self.state == TradingState.PAUSED:
            return 0.0
        b = self.payout - 1
        kelly = max(0.0, (p_win * b - (1 - p_win)) / b)
        base = self.bankroll * kelly * self.kelly_fraction
        if self.state == TradingState.REDUCED:
            base *= 0.75
        elif self.state == TradingState.RECOVERY:
            base *= 0.50
        return max(0.001, min(base, self.bankroll * 0.05))

    def record_outcome(self, bet_size: float, won: bool):
        if won:
            self.bankroll += bet_size * (self.payout - 1)
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.bankroll -= bet_size
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        if self.bankroll > self.peak_bankroll:
            self.peak_bankroll = self.bankroll
        self._update_state()

    def _update_state(self):
        if self.drawdown_pct >= 25.0 or self.consecutive_losses >= 8:
            self.state = TradingState.PAUSED
        elif self.drawdown_pct >= 15.0 or self.consecutive_losses >= 5:
            self.state = TradingState.REDUCED
        elif self.drawdown_pct < 5.0 and self.consecutive_losses < 3:
            self.state = TradingState.ACTIVE

    def snapshot(self, p_win: float) -> dict:
        """Return current risk state for tracing."""
        return {
            "trading_state": self.state.value,
            "bankroll": round(self.bankroll, 6),
            "drawdown_pct": round(self.drawdown_pct, 2),
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
            "position_size": round(self.calculate_position(p_win), 6),
            "kelly_fraction": round(
                max(0.0, (p_win * (self.payout - 1) - (1 - p_win)) / (self.payout - 1)),
                4,
            ),
            "ev": round(expected_value(p_win, self.payout), 6),
        }


# ============================================================================
# SidebetModule — orchestrates the 5-stage pipeline
# ============================================================================


class SidebetModule:
    """Replay engine for the sidebet pipeline.

    Loads game data from parquet, fits the survival model, then replays
    individual games through the full 5-stage pipeline.
    """

    SIDEBET_WINDOW = 40  # ticks

    def __init__(self, data_dir: str = "~/rugs_data"):
        self.data_dir = Path(data_dir).expanduser()
        self._games_df = None
        self._survival_model = None
        self._forecaster = SimpleBayesianForecaster()
        self._arbitrator = ArbitrationEngine()

    # -- lazy loaders --------------------------------------------------------

    @property
    def games_df(self):
        if self._games_df is None:
            self._games_df = load_game_data(min_ticks=10)
        return self._games_df

    @property
    def survival_model(self):
        if self._survival_model is None:
            self._survival_model = BayesianSurvivalModel(self.games_df)
        return self._survival_model

    # -- public API ----------------------------------------------------------

    def list_games(self, limit: int = 50) -> list[dict]:
        """Return a summary list of available games."""
        rows = []
        for _, g in self.games_df.head(limit).iterrows():
            rows.append(
                {
                    "game_id": g["game_id"],
                    "tick_count": int(g["tick_count"]),
                    "peak_multiplier": round(float(g["peak_multiplier"]), 4),
                    "rug_tick": int(g["rug_tick"]),
                }
            )
        return rows

    def get_game(self, game_id: str) -> dict | None:
        """Look up a single game by ID."""
        match = self.games_df[self.games_df["game_id"] == game_id]
        if match.empty:
            return None
        return match.iloc[0].to_dict()

    # -- Gate 1: basic replay ------------------------------------------------

    def replay_game(self, game_id: str, initial_bankroll: float = 1.0) -> ReplayResult:
        """Replay a game, returning only BET/WAIT decisions and outcomes."""
        game = self.get_game(game_id)
        if game is None:
            raise ValueError(f"Game {game_id} not found")

        prices = game["prices"]
        rug_tick = int(game["rug_tick"])
        risk = RiskManager(initial_bankroll)
        decisions: list[dict] = []

        for tick in range(len(prices)):
            if tick < 1:
                continue
            features = extract_features(prices, tick)
            p_rug = self.survival_model.predict_rug_probability(
                tick,
                window=self.SIDEBET_WINDOW,
                features=features,
            )
            model_b = self._forecaster.predict()
            arb = self._arbitrator.evaluate(p_rug, model_b, {"tick": tick, "features": features})

            if arb["action"] == "BET":
                bet_size = risk.calculate_position(p_rug)
                won = (rug_tick > tick) and (rug_tick <= tick + self.SIDEBET_WINDOW)
                risk.record_outcome(bet_size, won)
                decisions.append(
                    {
                        "tick": tick,
                        "action": "BET",
                        "p_rug": round(p_rug, 4),
                        "bet_size": round(bet_size, 6),
                        "won": won,
                        "reason": arb["reason"],
                    }
                )

        bets_won = sum(1 for d in decisions if d["won"])
        bets_lost = len(decisions) - bets_won
        return ReplayResult(
            game_id=game_id,
            ticks=len(prices),
            rug_tick=rug_tick,
            peak_price=round(float(game["peak_multiplier"]), 4),
            bets_placed=len(decisions),
            bets_won=bets_won,
            bets_lost=bets_lost,
            net_pnl=round(risk.bankroll - initial_bankroll, 6),
            final_bankroll=round(risk.bankroll, 6),
            decisions=decisions,
        )

    # -- Gate 2: traced replay -----------------------------------------------

    def replay_game_traced(
        self,
        game_id: str,
        initial_bankroll: float = 1.0,
    ) -> TracedReplayResult:
        """Replay a game with full per-tick pipeline trace.

        Every tick emits a trace dict covering all 5 pipeline stages:
        features, model_a, model_b, arbitration, risk.
        """
        game = self.get_game(game_id)
        if game is None:
            raise ValueError(f"Game {game_id} not found")

        prices = game["prices"]
        rug_tick = int(game["rug_tick"])
        risk = RiskManager(initial_bankroll)
        decisions: list[dict] = []
        tick_traces: list[dict] = []

        for tick in range(len(prices)):
            if tick < 1:
                continue

            # --- Stage 1: Features ---
            features = extract_features(prices, tick)
            features_dict = {
                "tick": features.tick,
                "price": features.price,
                "age": features.age,
                "distance_from_peak": round(features.distance_from_peak, 6),
                "volatility_5": round(features.volatility_5, 6),
                "volatility_10": round(features.volatility_10, 6),
                "momentum_3": round(features.momentum_3, 6),
                "momentum_5": round(features.momentum_5, 6),
                "price_acceleration": round(features.price_acceleration, 6),
                "is_rising": features.is_rising,
                "is_falling": features.is_falling,
                "rapid_rise": features.rapid_rise,
                "rapid_fall": features.rapid_fall,
                "peak_so_far": round(features.peak_so_far, 6),
                "ticks_since_peak": features.ticks_since_peak,
                "mean_reversion": round(features.mean_reversion, 6),
            }

            # --- Stage 2: Model A (BayesianSurvivalModel) ---
            base_prob = self.survival_model.predict_rug_probability(
                tick,
                window=self.SIDEBET_WINDOW,
                features=None,
            )
            p_rug = self.survival_model.predict_rug_probability(
                tick,
                window=self.SIDEBET_WINDOW,
                features=features,
            )
            feature_adjustment = p_rug / base_prob if base_prob > 0 else 1.0
            # Decompose which multipliers fired
            multipliers_fired = {}
            if features.rapid_fall:
                multipliers_fired["rapid_fall"] = 2.0
            if features.volatility_10 > 0.1:
                multipliers_fired["high_volatility"] = 1.5
            if features.ticks_since_peak > 20:
                multipliers_fired["time_since_peak"] = 1.3
            if features.rapid_rise:
                multipliers_fired["rapid_rise"] = 0.7
            if features.distance_from_peak > 0.3:
                multipliers_fired["distance_from_peak"] = 1.2

            model_a = {
                "base_prob": round(base_prob, 6),
                "feature_adjustment": round(feature_adjustment, 4),
                "p_rug": round(p_rug, 6),
                "multipliers_fired": multipliers_fired,
            }

            # --- Stage 3: Model B (SimpleBayesianForecaster) ---
            model_b = self._forecaster.predict()

            # --- Stage 4: Arbitration (decomposed) ---
            context = {"tick": tick, "features": features}
            vetoed, veto_reason = self._arbitrator._check_vetoes(p_rug, context)
            bucket = self._arbitrator._get_rug_bucket(p_rug)
            bucket_upgraded = self._arbitrator._apply_duration_gate(
                bucket,
                model_b,
                tick,
            )
            regime = model_b.get("regime", "normal")
            consensus_key = self._arbitrator._lookup_consensus(bucket_upgraded, regime)
            # Full evaluate for the actual action
            arb_result = self._arbitrator.evaluate(p_rug, model_b, context)

            arbitration = {
                "action": arb_result["action"],
                "bucket": bucket,
                "bucket_upgraded": bucket_upgraded,
                "consensus_lookup": consensus_key,
                "size_modifier": arb_result["size_modifier"],
                "reason": arb_result["reason"],
                "vetoed": vetoed,
                "veto_reason": veto_reason,
            }

            # --- Stage 5: Risk ---
            risk_snap = risk.snapshot(p_rug)

            # --- Bet execution ---
            bet_placed = False
            bet_amount = None
            bet_outcome = None

            if arb_result["action"] == "BET":
                bet_size = risk.calculate_position(p_rug)
                won = (rug_tick > tick) and (rug_tick <= tick + self.SIDEBET_WINDOW)
                risk.record_outcome(bet_size, won)
                bet_placed = True
                bet_amount = round(bet_size, 6)
                bet_outcome = "WON" if won else "LOST"
                decisions.append(
                    {
                        "tick": tick,
                        "action": "BET",
                        "p_rug": round(p_rug, 4),
                        "bet_size": bet_amount,
                        "won": won,
                        "reason": arb_result["reason"],
                    }
                )

            # --- Assemble trace ---
            tick_traces.append(
                {
                    "tick": tick,
                    "price": round(float(prices[tick]), 6),
                    "features": features_dict,
                    "model_a": model_a,
                    "model_b": model_b,
                    "arbitration": arbitration,
                    "risk": risk_snap,
                    "bet_placed": bet_placed,
                    "bet_amount": bet_amount,
                    "bet_outcome": bet_outcome,
                }
            )

        bets_won = sum(1 for d in decisions if d["won"])
        bets_lost = len(decisions) - bets_won

        return TracedReplayResult(
            game_id=game_id,
            ticks=len(prices),
            rug_tick=rug_tick,
            peak_price=round(float(game["peak_multiplier"]), 4),
            bets_placed=len(decisions),
            bets_won=bets_won,
            bets_lost=bets_lost,
            net_pnl=round(risk.bankroll - initial_bankroll, 6),
            final_bankroll=round(risk.bankroll, 6),
            decisions=decisions,
            tick_traces=tick_traces,
        )
