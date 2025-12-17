"""
DOM Utilities Module

Utilities for interacting with browser DOM elements.
"""

from browser.dom.selectors import (
    BALANCE_SELECTORS,
    BET_AMOUNT_INPUT_SELECTORS,
    BUY_BUTTON_SELECTORS,
    INCREMENT_SELECTOR_MAP,
    PERCENTAGE_TEXT_MAP,
    POSITION_SELECTORS,
    SELL_BUTTON_SELECTORS,
    SIDEBET_BUTTON_SELECTORS,
)
from browser.dom.timing import ExecutionTiming, TimingMetrics

__all__ = [
    "BALANCE_SELECTORS",
    "BET_AMOUNT_INPUT_SELECTORS",
    "BUY_BUTTON_SELECTORS",
    "INCREMENT_SELECTOR_MAP",
    "PERCENTAGE_TEXT_MAP",
    "POSITION_SELECTORS",
    "SELL_BUTTON_SELECTORS",
    "SIDEBET_BUTTON_SELECTORS",
    "ExecutionTiming",
    "TimingMetrics",
]
