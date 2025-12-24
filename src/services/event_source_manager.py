"""
Event Source Manager

Manages switching between CDP (authenticated) and fallback (public) event sources.
"""

import logging
import threading
from collections.abc import Callable
from enum import Enum
from typing import Any

from services.event_bus import Events, event_bus

logger = logging.getLogger(__name__)


class EventSource(Enum):
    """Available event sources."""

    NONE = "none"
    CDP = "cdp"  # Authenticated via CDP interception
    FALLBACK = "fallback"  # Public WebSocketFeed


class EventSourceManager:
    """
    Manages event source selection and switching.

    Prefers CDP (authenticated) when available, falls back to
    WebSocketFeed (public only) when CDP is unavailable.
    """

    def __init__(self):
        """Initialize source manager."""
        self._lock = threading.Lock()

        # State
        self.active_source: EventSource = EventSource.NONE
        self.is_cdp_available: bool = False

        # Callbacks
        self.on_source_changed: Callable[[EventSource], None] | None = None

        logger.info("EventSourceManager initialized")

    def set_cdp_available(self, available: bool):
        """
        Update CDP availability status.

        Args:
            available: Whether CDP interception is available
        """
        with self._lock:
            self.is_cdp_available = available

        logger.info(f"CDP availability: {available}")

    def switch_to_best_source(self):
        """
        Switch to the best available source.

        Prefers CDP when available, falls back otherwise.
        """
        new_source = None
        old_source = None
        on_source_changed = None

        with self._lock:
            desired_source = EventSource.CDP if self.is_cdp_available else EventSource.FALLBACK
            if desired_source != self.active_source:
                old_source = self.active_source
                self.active_source = desired_source
                new_source = desired_source
                on_source_changed = self.on_source_changed

        if new_source is None:
            return

        logger.info(f"Event source: {old_source.value} -> {new_source.value}")

        # Publish outside the lock to avoid re-entrancy issues.
        try:
            event_bus.publish(Events.WS_SOURCE_CHANGED, {"source": new_source.value})
        except Exception:
            pass

        if on_source_changed:
            try:
                on_source_changed(new_source)
            except Exception as e:
                logger.error(f"Error in source changed callback: {e}")

    def get_status(self) -> dict[str, Any]:
        """Get current status."""
        with self._lock:
            return {
                "active_source": self.active_source.value,
                "is_cdp_available": self.is_cdp_available,
            }
