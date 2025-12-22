"""Services package.

Keep this module lightweight: importing `services` should not trigger heavy
imports (e.g., recorders that pull in live-feed dependencies). This improves
test startup, avoids optional-dependency explosions, and prevents import-order
side effects.
"""

from __future__ import annotations

import importlib

from .event_bus import Events, event_bus
from .logger import get_logger, setup_logging

__all__ = ["Events", "event_bus", "get_logger", "setup_logging"]


_LAZY_EXPORTS = {
    # State verifier (local vs playerUpdate server truth comparison)
    "StateVerifier": ("services.state_verifier", "StateVerifier"),
    "BALANCE_TOLERANCE": ("services.state_verifier", "BALANCE_TOLERANCE"),
    "POSITION_TOLERANCE": ("services.state_verifier", "POSITION_TOLERANCE"),
    # Game and session recorders (legacy - see EventStore for Phase 12)
    "GameStateRecorder": ("services.recorders", "GameStateRecorder"),
    "PlayerSessionRecorder": ("services.recorders", "PlayerSessionRecorder"),
    # Recording state machine
    "RecordingState": ("services.recording_state_machine", "RecordingState"),
    "RecordingStateMachine": ("services.recording_state_machine", "RecordingStateMachine"),
    # Unified recorder (legacy - see EventStore for Phase 12)
    "UnifiedRecorder": ("services.unified_recorder", "UnifiedRecorder"),
    # Phase 12C: Server-authoritative state in live mode
    "LiveStateProvider": ("services.live_state_provider", "LiveStateProvider"),
}


def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        module_name, attr = _LAZY_EXPORTS[name]
        module = importlib.import_module(module_name)
        value = getattr(module, attr)
        globals()[name] = value
        if name not in __all__:
            __all__.append(name)
        return value
    raise AttributeError(f"module 'services' has no attribute {name!r}")
