"""Strategy Profile data models."""

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class StrategyProfile:
    """Trading strategy profile for live testing."""

    # Identity
    profile_id: str
    created_at: datetime

    # Configuration
    kelly_variant: str  # "quarter", "half", "full"
    min_edge_threshold: float  # 0.02 (2% edge required)
    optimal_entry_tick: int  # 200+ from survival analysis

    # Monte Carlo Results (10k iterations)
    expected_return: float
    probability_profit: float
    probability_ruin: float
    var_95: float
    sharpe_ratio: float

    # Bayesian Parameters (optional)
    base_probability_curve: list | None = None
    gap_signal_thresholds: dict | None = None

    # Live Testing State
    games_played: int = 0
    actual_return: float = 0.0
    predictions_correct: int = 0

    def to_dict(self) -> dict:
        """Serialize to dict."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "StrategyProfile":
        """Deserialize from dict."""
        data = data.copy()
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)
