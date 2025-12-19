"""
Sources module for REPLAYER - Live feed integrations.

Extracted classes to separate modules for maintainability (<400 lines per file).
"""

# Data integrity monitor
from sources.data_integrity_monitor import DataIntegrityMonitor, IntegrityIssue, ThresholdType
from sources.feed_degradation import GracefulDegradationManager, OperatingMode

# Feed monitors
from sources.feed_monitors import ConnectionHealth, ConnectionHealthMonitor, LatencySpikeDetector
from sources.feed_rate_limiter import PriorityRateLimiter, TokenBucketRateLimiter
from sources.game_state_machine import GameSignal, GameStateMachine

# Price history handler
from sources.price_history_handler import PriceHistoryHandler
from sources.websocket_feed import WebSocketFeed

__all__ = [
    "WebSocketFeed",
    "GameSignal",
    "GameStateMachine",
    # Monitors
    "LatencySpikeDetector",
    "ConnectionHealth",
    "ConnectionHealthMonitor",
    # Rate limiters
    "TokenBucketRateLimiter",
    "PriorityRateLimiter",
    # Degradation
    "OperatingMode",
    "GracefulDegradationManager",
    # Price history handler
    "PriceHistoryHandler",
    # Data integrity monitor
    "DataIntegrityMonitor",
    "ThresholdType",
    "IntegrityIssue",
]
