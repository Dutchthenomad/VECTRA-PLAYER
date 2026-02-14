"""Business logic tests — add your service-specific tests here."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processor import Processor


@pytest.fixture
def processor():
    return Processor()


@pytest.mark.asyncio
async def test_processor_processes_event(processor):
    await processor.process({"event_type": "test", "data": {}})
    stats = processor.get_stats()
    assert stats["events_processed"] == 1


@pytest.mark.asyncio
async def test_processor_counts_events(processor):
    for _ in range(5):
        await processor.process({"event_type": "test", "data": {}})
    assert processor.get_stats()["events_processed"] == 5
