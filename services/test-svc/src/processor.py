"""Business logic processor — implement your service logic here."""

import logging

logger = logging.getLogger(__name__)


class Processor:
    """Process incoming events from the upstream feed."""

    def __init__(self):
        self._events_processed = 0

    async def process(self, event: dict) -> None:
        """Process a single event from the upstream feed.

        Override this method with your service's business logic.
        """
        self._events_processed += 1

    def get_stats(self) -> dict:
        return {
            "events_processed": self._events_processed,
        }
