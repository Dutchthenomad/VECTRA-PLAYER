"""Statistical analysis modules."""

from .bayesian import (
    BASE_PROBABILITY_CURVE,
    BayesianSidebetAdvisor,
    GapSignalResult,
    RugGapSignalDetector,
    compute_bayesian_rug_probability,
    get_base_rug_probability,
)
from .kelly import (
    KellyResult,
    calculate_all_variants,
    calculate_edge,
    fractional_kelly,
    kelly_criterion,
    recommend_bet_size,
)
from .survival import (
    compute_conditional_probability,
    compute_hazard_rate,
    compute_survival_curve,
    find_optimal_entry_window,
)

__all__ = [
    # Survival
    "compute_survival_curve",
    "compute_hazard_rate",
    "compute_conditional_probability",
    "find_optimal_entry_window",
    # Bayesian
    "RugGapSignalDetector",
    "GapSignalResult",
    "get_base_rug_probability",
    "compute_bayesian_rug_probability",
    "BayesianSidebetAdvisor",
    "BASE_PROBABILITY_CURVE",
    # Kelly
    "kelly_criterion",
    "fractional_kelly",
    "calculate_edge",
    "recommend_bet_size",
    "calculate_all_variants",
    "KellyResult",
]
