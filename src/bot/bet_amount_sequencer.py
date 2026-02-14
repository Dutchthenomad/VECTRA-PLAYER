"""
BetAmountSequencer - Delta-based optimal button sequence calculator.

Calculates the minimal button clicks needed to go from current bet amount
to target bet amount, exploiting the fact that the amount persists in the
browser window until refresh.

Key optimizations:
- Delta-based: calculates current → target, not always from zero
- Exploits 1/2 and X2 for power-of-2 transitions
- Front-running: prepares next bet immediately after placing current
"""

from decimal import Decimal

# Available increment buttons and their values
INCREMENTS = {
    "+0.001": Decimal("0.001"),
    "+0.01": Decimal("0.01"),
    "+0.1": Decimal("0.1"),
    "+1": Decimal("1"),
}


def calculate_optimal_sequence(current: Decimal, target: Decimal) -> list[str]:
    """
    Calculate optimal button sequence from current amount to target.

    Args:
        current: Current bet amount in browser (persists between bets)
        target: Target bet amount in SOL

    Returns:
        List of button clicks (may be empty if current == target)

    Examples:
        >>> calculate_optimal_sequence(Decimal("0.004"), Decimal("0.002"))
        ['1/2']
        >>> calculate_optimal_sequence(Decimal("0.004"), Decimal("0.008"))
        ['X2']
        >>> calculate_optimal_sequence(Decimal("0.004"), Decimal("0.005"))
        ['+0.001']
        >>> calculate_optimal_sequence(Decimal("0.004"), Decimal("0.001"))
        ['1/2', '1/2']
        >>> calculate_optimal_sequence(Decimal("0"), Decimal("0.004"))
        ['+0.001', '+0.001', 'X2']  # Half optimization (3 clicks)
    """
    # Normalize to ensure we're working with proper Decimals
    current = Decimal(str(current)).quantize(Decimal("0.001"))
    target = Decimal(str(target)).quantize(Decimal("0.001"))

    # No change needed
    if current == target:
        return []

    # Strategy 1: Check if single 1/2 works
    if current > 0 and current / 2 == target:
        return ["1/2"]

    # Strategy 2: Check if single X2 works
    if current > 0 and current * 2 == target:
        return ["X2"]

    # Strategy 3: Check if multiple 1/2 presses work (max 3)
    halves = _count_halves(current, target)
    if halves and halves <= 3:
        return ["1/2"] * halves

    # Strategy 4: Check if multiple X2 presses work (max 3)
    doubles = _count_doubles(current, target)
    if doubles and doubles <= 3:
        return ["X2"] * doubles

    # Strategy 5: Check if we can add to reach target
    delta = target - current
    if delta > 0:
        if current == 0:
            # Starting from zero - use optimized build with X2
            return _build_from_zero(target)
        else:
            # Adding to existing amount - use greedy increments
            increments = _greedy_increments(delta)
            # Check if this is reasonable (not too many clicks)
            if len(increments) <= 5:
                return increments
            # If too many increments, consider clear + rebuild
            rebuild = ["X"] + _build_from_zero(target)
            return rebuild if len(rebuild) < len(increments) else increments

    # Strategy 6: Need to decrease - clear and rebuild is often faster
    return ["X"] + _build_from_zero(target)


def _count_halves(current: Decimal, target: Decimal) -> int | None:
    """
    Count how many 1/2 presses needed to reach target from current.

    Returns None if target cannot be reached by halving.
    """
    if current <= 0 or target <= 0:
        return None

    count = 0
    val = current
    while val > target and count < 10:
        val = val / 2
        # Quantize to avoid floating point issues
        val = val.quantize(Decimal("0.001"))
        count += 1
        if val == target:
            return count
    return None


def _count_doubles(current: Decimal, target: Decimal) -> int | None:
    """
    Count how many X2 presses needed to reach target from current.

    Returns None if target cannot be reached by doubling.
    """
    if current <= 0:
        return None

    count = 0
    val = current
    while val < target and count < 10:
        val = val * 2
        # Quantize to avoid floating point issues
        val = val.quantize(Decimal("0.001"))
        count += 1
        if val == target:
            return count
    return None


def _greedy_increments(amount: Decimal) -> list[str]:
    """
    Build amount using largest increments first (greedy algorithm).

    Args:
        amount: Amount to build using increment buttons

    Returns:
        List of increment button clicks
    """
    sequence = []
    remaining = amount

    # Sort increments by value descending (largest first)
    for button, value in sorted(INCREMENTS.items(), key=lambda x: -x[1]):
        while remaining >= value:
            sequence.append(button)
            remaining -= value
            # Quantize to avoid floating point issues
            remaining = remaining.quantize(Decimal("0.001"))

    return sequence


def _build_from_zero(target: Decimal) -> list[str]:
    """
    Build target amount from zero, with X2 optimization.

    Tries to find if building half + X2 is more efficient than
    straight greedy increments.

    Args:
        target: Target amount to build

    Returns:
        Optimal sequence of buttons to build target from zero
    """
    if target <= 0:
        return []

    # Get greedy sequence
    greedy = _greedy_increments(target)

    # Try building half and doubling
    half = target / 2
    half_quantized = half.quantize(Decimal("0.001"))

    # Only use X2 optimization if half is a clean value
    if half == half_quantized and half > 0:
        half_seq = _greedy_increments(half_quantized)
        # X2 optimization is worth it if it saves clicks
        if len(half_seq) + 1 < len(greedy):
            return half_seq + ["X2"]

    # Try building quarter and doubling twice
    quarter = target / 4
    quarter_quantized = quarter.quantize(Decimal("0.001"))

    if quarter == quarter_quantized and quarter > 0:
        quarter_seq = _greedy_increments(quarter_quantized)
        # Two X2s worth it if saves clicks
        if len(quarter_seq) + 2 < len(greedy):
            return quarter_seq + ["X2", "X2"]

    return greedy


def estimate_clicks(current: Decimal, target: Decimal) -> int:
    """
    Estimate the number of clicks needed without computing full sequence.

    Useful for comparing strategies without full computation.

    Args:
        current: Current bet amount
        target: Target bet amount

    Returns:
        Estimated number of button clicks
    """
    return len(calculate_optimal_sequence(current, target))
