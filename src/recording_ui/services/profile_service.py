"""
Trading Profile Service - Unified profile management for VECTRA-PLAYER.

Manages TradingProfile v2 schema with:
- Execution params (entry_tick, bet_sizes, etc.)
- Scaling config (Kelly, Theta Bayesian, etc.)
- Risk controls (drawdown, take profit)
- Monte Carlo metrics (cached simulation results)

Supports migration from v1 (flat params) to v2 (structured sections).
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Schema version for new profiles
SCHEMA_VERSION = "2.0.0"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class ExecutionConfig:
    """Execution parameters for bet placement."""

    entry_tick: int = 219
    num_bets: int = 4
    bet_sizes: list[float] = field(default_factory=lambda: [0.001, 0.001, 0.001, 0.001])
    initial_balance: float = 0.1


@dataclass
class ScalingConfig:
    """Position sizing and scaling configuration."""

    mode: str = "fixed"  # fixed, kelly, anti_martingale, theta_bayesian, volatility_adjusted
    kelly_fraction: float = 0.25
    win_streak_multiplier: float = 1.0
    max_streak_multiplier: float = 1.0
    theta_base: float = 1.0
    theta_max: float = 1.0
    use_volatility_scaling: bool = False


@dataclass
class RiskControls:
    """Risk management parameters."""

    max_drawdown_pct: float = 0.15
    take_profit_target: float | None = None
    reduce_on_drawdown: bool = False
    daily_loss_limit: float | None = None


@dataclass
class MonteCarloMetrics:
    """Cached Monte Carlo simulation results."""

    computed_at: str | None = None
    iterations: int = 0
    win_rate_assumption: float = 0.185
    mean_final_bankroll: float = 0.0
    median_final_bankroll: float = 0.0
    probability_profit: float = 0.0
    probability_2x: float = 0.0
    mean_max_drawdown: float = 0.0
    sortino_ratio: float = 0.0
    sharpe_ratio: float = 0.0
    calmar_ratio: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    risk_level: str = "Unknown"


@dataclass
class TradingProfile:
    """
    Unified trading profile with v2 schema.

    Combines execution params, scaling config, risk controls,
    and cached Monte Carlo metrics in a single profile.
    """

    name: str
    schema_version: str = SCHEMA_VERSION
    created: str = ""
    source: str = "manual"  # manual, monte_carlo, explorer, imported

    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    scaling: ScalingConfig = field(default_factory=ScalingConfig)
    risk_controls: RiskControls = field(default_factory=RiskControls)
    monte_carlo_metrics: MonteCarloMetrics | None = None

    def __post_init__(self):
        if not self.created:
            self.created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result = {
            "schema_version": self.schema_version,
            "name": self.name,
            "created": self.created,
            "source": self.source,
            "execution": asdict(self.execution),
            "scaling": asdict(self.scaling),
            "risk_controls": asdict(self.risk_controls),
        }
        if self.monte_carlo_metrics:
            result["monte_carlo_metrics"] = asdict(self.monte_carlo_metrics)
        return result

    def to_legacy_format(self) -> dict[str, Any]:
        """
        Convert to v1 legacy format for backward compatibility.
        Used by existing backtest_service and live_backtest_service.
        """
        return {
            "name": self.name,
            "initial_balance": self.execution.initial_balance,
            "params": {
                "entry_tick": self.execution.entry_tick,
                "num_bets": self.execution.num_bets,
                "bet_sizes": self.execution.bet_sizes,
                "use_kelly_sizing": self.scaling.mode in ("kelly", "theta_bayesian"),
                "kelly_fraction": self.scaling.kelly_fraction,
                "use_dynamic_sizing": self.scaling.mode == "theta_bayesian",
                "high_confidence_threshold": 55,
                "high_confidence_multiplier": self.scaling.win_streak_multiplier,
                "reduce_on_drawdown": self.risk_controls.reduce_on_drawdown,
                "max_drawdown_pct": self.risk_controls.max_drawdown_pct,
                "take_profit_target": self.risk_controls.take_profit_target,
            },
            "created": self.created,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TradingProfile":
        """Create from dict (handles both v1 and v2 formats)."""
        # Check if v2 format (has schema_version or structured sections)
        if "schema_version" in data or "execution" in data:
            return cls._from_v2_dict(data)
        else:
            return cls._from_v1_dict(data)

    @classmethod
    def _from_v2_dict(cls, data: dict[str, Any]) -> "TradingProfile":
        """Create from v2 format dict."""
        execution = ExecutionConfig(**data.get("execution", {}))
        scaling = ScalingConfig(**data.get("scaling", {}))
        risk_controls = RiskControls(**data.get("risk_controls", {}))

        mc_data = data.get("monte_carlo_metrics")
        mc_metrics = MonteCarloMetrics(**mc_data) if mc_data else None

        return cls(
            name=data.get("name", "unnamed"),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            created=data.get("created", ""),
            source=data.get("source", "manual"),
            execution=execution,
            scaling=scaling,
            risk_controls=risk_controls,
            monte_carlo_metrics=mc_metrics,
        )

    @classmethod
    def _from_v1_dict(cls, data: dict[str, Any]) -> "TradingProfile":
        """
        Migrate from v1 legacy format.

        v1 format:
        {
            "name": "...",
            "initial_balance": 0.1,
            "params": {
                "entry_tick": 219,
                "num_bets": 4,
                "bet_sizes": [...],
                "use_kelly_sizing": true,
                ...
            }
        }
        """
        params = data.get("params", {})

        # Determine scaling mode from v1 flags
        scaling_mode = "fixed"
        if params.get("use_kelly_sizing"):
            if params.get("use_dynamic_sizing"):
                scaling_mode = "theta_bayesian"
            else:
                scaling_mode = "kelly"

        execution = ExecutionConfig(
            entry_tick=params.get("entry_tick", 219),
            num_bets=params.get("num_bets", 4),
            bet_sizes=params.get("bet_sizes", [0.001, 0.001, 0.001, 0.001]),
            initial_balance=data.get("initial_balance", 0.1),
        )

        scaling = ScalingConfig(
            mode=scaling_mode,
            kelly_fraction=params.get("kelly_fraction", 0.25),
            win_streak_multiplier=params.get("high_confidence_multiplier", 1.0),
            max_streak_multiplier=params.get("high_confidence_multiplier", 1.0) * 2,
        )

        risk_controls = RiskControls(
            max_drawdown_pct=params.get("max_drawdown_pct", 0.15),
            take_profit_target=params.get("take_profit_target"),
            reduce_on_drawdown=params.get("reduce_on_drawdown", False),
        )

        return cls(
            name=data.get("name", "unnamed"),
            schema_version=SCHEMA_VERSION,
            created=data.get("created", ""),
            source="imported",  # Mark as imported from v1
            execution=execution,
            scaling=scaling,
            risk_controls=risk_controls,
        )


# =============================================================================
# PROFILE SERVICE
# =============================================================================


class ProfileService:
    """
    Service for managing TradingProfiles.

    Handles CRUD operations, v1→v2 migration, and profile queries.
    """

    def __init__(self, profiles_dir: Path | None = None):
        """
        Initialize profile service.

        Args:
            profiles_dir: Directory for profile storage.
                         Defaults to Machine Learning/strategies/
        """
        if profiles_dir:
            self.profiles_dir = profiles_dir
        else:
            # Default to existing strategy directory
            base = Path(__file__).parent.parent.parent.parent
            self.profiles_dir = base / "Machine Learning" / "strategies"

        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ProfileService initialized with dir: {self.profiles_dir}")

    def list_profiles(self) -> list[dict[str, Any]]:
        """
        List all profiles with summary info.

        Returns list of dicts with: name, created, source, has_mc_metrics, risk_level
        """
        profiles = []

        for f in self.profiles_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)

                # Handle both v1 and v2 formats
                name = data.get("name", f.stem)
                created = data.get("created", "")

                # Check for MC metrics
                mc_metrics = data.get("monte_carlo_metrics")
                has_mc = mc_metrics is not None

                # Extract key metrics for display
                sortino = mc_metrics.get("sortino_ratio", 0) if mc_metrics else None
                p_profit = mc_metrics.get("probability_profit", 0) if mc_metrics else None
                risk_level = mc_metrics.get("risk_level", "Unknown") if mc_metrics else None

                profiles.append(
                    {
                        "name": name,
                        "file": f.name,
                        "created": created,
                        "source": data.get("source", "manual"),
                        "schema_version": data.get("schema_version", "1.0.0"),
                        "has_mc_metrics": has_mc,
                        "sortino_ratio": sortino,
                        "probability_profit": p_profit,
                        "risk_level": risk_level,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to read profile {f}: {e}")
                continue

        # Sort by created date (newest first)
        return sorted(profiles, key=lambda x: x.get("created", ""), reverse=True)

    def load_profile(self, name: str) -> TradingProfile | None:
        """
        Load a profile by name.

        Automatically handles v1→v2 migration.
        """
        path = self.profiles_dir / f"{name}.json"
        if not path.exists():
            logger.warning(f"Profile not found: {name}")
            return None

        try:
            with open(path) as fp:
                data = json.load(fp)

            profile = TradingProfile.from_dict(data)
            logger.debug(f"Loaded profile: {name} (v{profile.schema_version})")
            return profile
        except Exception as e:
            logger.error(f"Failed to load profile {name}: {e}")
            return None

    def save_profile(self, profile: TradingProfile) -> str:
        """
        Save a profile.

        Returns the sanitized filename.
        """
        # Sanitize name
        safe_name = "".join(c for c in profile.name if c.isalnum() or c in "-_").strip()
        if not safe_name:
            safe_name = f"profile_{int(time.time())}"

        profile.name = safe_name

        path = self.profiles_dir / f"{safe_name}.json"

        try:
            with open(path, "w") as fp:
                json.dump(profile.to_dict(), fp, indent=2)

            logger.info(f"Saved profile: {safe_name}")
            return safe_name
        except Exception as e:
            logger.error(f"Failed to save profile {safe_name}: {e}")
            raise

    def delete_profile(self, name: str) -> bool:
        """Delete a profile by name."""
        path = self.profiles_dir / f"{name}.json"
        if path.exists():
            path.unlink()
            logger.info(f"Deleted profile: {name}")
            return True
        return False

    def update_mc_metrics(self, name: str, metrics: MonteCarloMetrics) -> bool:
        """
        Update Monte Carlo metrics for an existing profile.
        """
        profile = self.load_profile(name)
        if not profile:
            return False

        profile.monte_carlo_metrics = metrics
        self.save_profile(profile)
        return True

    def migrate_v1_to_v2(self, name: str) -> TradingProfile | None:
        """
        Explicitly migrate a v1 profile to v2 format.

        Loads v1 format, converts to v2, saves, returns new profile.
        """
        profile = self.load_profile(name)
        if not profile:
            return None

        # If already v2, just return
        if profile.schema_version == SCHEMA_VERSION:
            return profile

        # Mark as migrated
        profile.source = "migrated"
        profile.schema_version = SCHEMA_VERSION

        self.save_profile(profile)
        logger.info(f"Migrated profile {name} to v2 schema")

        return profile


# =============================================================================
# MODULE-LEVEL SINGLETON
# =============================================================================

_profile_service: ProfileService | None = None


def get_profile_service(profiles_dir: Path | None = None) -> ProfileService:
    """Get or create the ProfileService singleton."""
    global _profile_service

    if _profile_service is None:
        _profile_service = ProfileService(profiles_dir)

    return _profile_service
