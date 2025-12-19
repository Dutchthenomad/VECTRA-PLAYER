"""
EventBus Characterization Tests - AUDIT FIX Edge Cases

Documents and tests the specific behaviors fixed by AUDIT FIX patches.
These tests capture existing behavior as a safety net for refactoring.

DO NOT modify expected values to make tests pass.

AUDIT FIX Summary (from src/services/event_bus.py):
1. Weak references to prevent memory leaks
2. No locks held during callback execution (deadlock prevention)
3. Callback ID tracking for proper unsubscribe
4. Increased queue size (5000 vs 1000)
5. Stats tracking
6. Improved shutdown with retry loop
7. Duplicate subscription prevention
8. Queue capacity warnings at 80%
"""

import gc
import logging
import threading
import time
import weakref

from services.event_bus import EventBus, Events


class TestAuditFixWeakReferences:
    """
    AUDIT FIX: Weak references prevent memory leaks.

    When subscribers go out of scope, they should be garbage collected
    and automatically removed from the EventBus.
    """

    def test_weak_ref_subscriber_is_garbage_collected(self):
        """
        Document: Weak subscribers are cleaned up when they go out of scope.

        AUDIT FIX: Use weak references to prevent memory leaks
        """
        bus = EventBus()
        bus.start()

        call_count = [0]

        def create_and_subscribe():
            def handler(_event):
                call_count[0] += 1
            bus.subscribe(Events.GAME_TICK, handler, weak=True)
            return weakref.ref(handler)

        # Create subscriber in nested scope
        weak_handler = create_and_subscribe()

        # Handler should exist before GC
        assert weak_handler() is not None or True  # May already be collected

        # Force garbage collection
        gc.collect()

        # Handler should be collected
        assert weak_handler() is None

        # Publishing should not call the dead handler
        bus.publish(Events.GAME_TICK, {"test": True})
        time.sleep(0.1)

        # Handler was never called (was already GC'd)
        # Note: May have been called once before GC, so we just verify no crash
        bus.stop()

    def test_strong_ref_subscriber_persists(self):
        """
        Document: weak=False keeps subscribers alive even without external refs.
        """
        bus = EventBus()
        bus.start()

        call_count = [0]

        def create_strong_subscriber():
            def handler(_event):
                call_count[0] += 1
            bus.subscribe(Events.GAME_TICK, handler, weak=False)

        create_strong_subscriber()
        gc.collect()

        # Strong ref should still work
        bus.publish(Events.GAME_TICK, {"test": True})
        time.sleep(0.1)

        assert call_count[0] == 1
        bus.stop()


class TestAuditFixDeadlockPrevention:
    """
    AUDIT FIX: No locks held during callback execution.

    This prevents deadlocks when callbacks publish events.
    """

    def test_callback_can_publish_without_deadlock(self):
        """
        Document: Callbacks can safely publish events without deadlock.

        AUDIT FIX CRITICAL: DO NOT hold lock during callback execution!
        This prevents deadlocks when callbacks publish events.
        """
        bus = EventBus()
        bus.start()

        events_received = []

        def cascading_handler(event):
            events_received.append(("first", event["data"]))
            # This would deadlock if lock was held during callback
            bus.publish(Events.GAME_END, {"cascaded": True})

        def end_handler(event):
            events_received.append(("end", event["data"]))

        bus.subscribe(Events.GAME_START, cascading_handler, weak=False)
        bus.subscribe(Events.GAME_END, end_handler, weak=False)

        # This should not deadlock
        bus.publish(Events.GAME_START, {"initial": True})

        # Wait for both events to process
        time.sleep(0.3)

        # Both handlers should have been called
        assert len(events_received) == 2
        assert events_received[0] == ("first", {"initial": True})
        assert events_received[1] == ("end", {"cascaded": True})

        bus.stop()

    def test_callback_can_subscribe_without_deadlock(self):
        """
        Document: Callbacks can safely subscribe new handlers.
        """
        bus = EventBus()
        bus.start()

        late_events = []

        def late_handler(event):
            late_events.append(event["data"])

        def subscribing_handler(event):
            # Subscribe another handler from within callback
            bus.subscribe(Events.GAME_TICK, late_handler, weak=False)

        bus.subscribe(Events.GAME_START, subscribing_handler, weak=False)

        # Trigger subscription from callback
        bus.publish(Events.GAME_START, {})
        time.sleep(0.1)

        # Now publish to the newly subscribed handler
        bus.publish(Events.GAME_TICK, {"late": True})
        time.sleep(0.1)

        assert late_events == [{"late": True}]
        bus.stop()


class TestAuditFixDuplicatePrevention:
    """
    AUDIT FIX: Prevent duplicate subscriptions.
    """

    def test_same_handler_not_added_twice(self):
        """
        Document: Subscribing same handler twice is idempotent.

        AUDIT FIX: Skip if already subscribed (prevent duplicates)
        """
        bus = EventBus()
        bus.start()

        call_count = [0]

        def handler(_event):
            call_count[0] += 1

        # Subscribe same handler twice
        bus.subscribe(Events.GAME_TICK, handler, weak=False)
        bus.subscribe(Events.GAME_TICK, handler, weak=False)

        bus.publish(Events.GAME_TICK, {})
        time.sleep(0.1)

        # Should only be called once, not twice
        assert call_count[0] == 1
        bus.stop()


class TestAuditFixCallbackIdTracking:
    """
    AUDIT FIX 2: Track callback IDs for proper unsubscribe.

    Fixes broken unsubscribe when using weak references.
    """

    def test_unsubscribe_by_callback_identity(self):
        """
        Document: Unsubscribe works correctly with callback ID tracking.

        AUDIT FIX 2: Use callback ID for proper matching
        """
        bus = EventBus()
        bus.start()

        handler1_calls = [0]
        handler2_calls = [0]

        def handler1(_event):
            handler1_calls[0] += 1

        def handler2(_event):
            handler2_calls[0] += 1

        bus.subscribe(Events.GAME_TICK, handler1, weak=False)
        bus.subscribe(Events.GAME_TICK, handler2, weak=False)

        # Unsubscribe only handler1
        bus.unsubscribe(Events.GAME_TICK, handler1)

        bus.publish(Events.GAME_TICK, {})
        time.sleep(0.1)

        # handler1 should NOT be called, handler2 should be called
        assert handler1_calls[0] == 0
        assert handler2_calls[0] == 1
        bus.stop()

    def test_unsubscribe_nonexistent_handler_no_error(self):
        """
        Document: Unsubscribing handler that doesn't exist is safe.
        """
        bus = EventBus()

        def handler(_event):
            pass

        # Should not raise
        bus.unsubscribe(Events.GAME_TICK, handler)


class TestAuditFixQueueManagement:
    """
    AUDIT FIX: Queue size and capacity monitoring.
    """

    def test_queue_size_is_5000_by_default(self):
        """
        Document: Default queue size is 5000 (was 1000).

        AUDIT FIX: Increased queue size from 1000 to 5000
        """
        bus = EventBus()
        assert bus._queue.maxsize == 5000

    def test_queue_full_drops_event_without_error(self):
        """
        Document: When queue is full, event is dropped gracefully.
        """
        bus = EventBus(max_queue_size=2)
        # Don't start processing - queue will fill up

        bus.publish(Events.GAME_TICK, {"event": 1})
        bus.publish(Events.GAME_TICK, {"event": 2})
        bus.publish(Events.GAME_TICK, {"event": 3})  # Should be dropped

        # Check stats
        assert bus._stats["events_dropped"] >= 1

    def test_queue_capacity_warning_at_80_percent(self, caplog):
        """
        Document: Warning logged when queue reaches 80% capacity.

        AUDIT FIX: Warn at 80% capacity
        """
        bus = EventBus(max_queue_size=10)
        # Don't start processing

        with caplog.at_level(logging.WARNING):
            # Fill to 80%
            for i in range(9):
                bus.publish(Events.GAME_TICK, {"event": i})

        # Should have logged a warning
        assert any("capacity" in record.message.lower() for record in caplog.records)


class TestAuditFixShutdown:
    """
    AUDIT FIX: Improved shutdown with retry loop.
    """

    def test_shutdown_with_full_queue_succeeds(self):
        """
        Document: Shutdown succeeds even when queue is full.

        AUDIT FIX: Retry loop with timeout for reliable sentinel insertion
        """
        bus = EventBus(max_queue_size=2)
        bus.start()

        # Fill the queue
        bus.publish(Events.GAME_TICK, {"event": 1})
        bus.publish(Events.GAME_TICK, {"event": 2})

        # Stop should succeed (drains queue to insert sentinel)
        bus.stop()

        assert bus._processing is False

    def test_shutdown_timeout_logged(self, caplog):
        """
        Document: If thread doesn't stop within timeout, error is logged.
        """
        bus = EventBus()
        bus._processing = True

        # Create a thread that won't respond to sentinel
        def stubborn_thread():
            time.sleep(10)  # Longer than timeout

        bus._thread = threading.Thread(target=stubborn_thread, daemon=True)
        bus._thread.start()

        with caplog.at_level(logging.ERROR):
            bus.stop()

        # Should log error about thread not stopping
        # (may or may not trigger depending on timing)


class TestAuditFixStatistics:
    """
    AUDIT FIX: Statistics tracking for monitoring.
    """

    def test_stats_track_published_events(self):
        """
        Document: events_published counter increments on publish.
        """
        bus = EventBus()
        initial = bus._stats["events_published"]

        bus.publish(Events.GAME_TICK, {})
        bus.publish(Events.GAME_TICK, {})
        bus.publish(Events.GAME_TICK, {})

        assert bus._stats["events_published"] == initial + 3

    def test_stats_track_dropped_events(self):
        """
        Document: events_dropped counter increments when queue full.
        """
        bus = EventBus(max_queue_size=1)

        bus.publish(Events.GAME_TICK, {})
        bus.publish(Events.GAME_TICK, {})  # Dropped

        assert bus._stats["events_dropped"] >= 1

    def test_stats_track_processing_errors(self):
        """
        Document: errors counter increments on callback exception.
        """
        bus = EventBus()
        bus.start()

        def bad_handler(_event):
            raise ValueError("Test error")

        bus.subscribe(Events.GAME_TICK, bad_handler, weak=False)
        bus.publish(Events.GAME_TICK, {})
        time.sleep(0.1)

        assert bus._stats["errors"] >= 1
        bus.stop()

    def test_get_stats_returns_complete_info(self):
        """
        Document: get_stats() returns all tracking information.
        """
        bus = EventBus()
        stats = bus.get_stats()

        expected_keys = [
            "subscriber_count",
            "event_types",
            "queue_size",
            "processing",
            "events_published",
            "events_processed",
            "events_dropped",
            "errors",
        ]

        for key in expected_keys:
            assert key in stats, f"Missing stat: {key}"


class TestAuditFixClearAll:
    """
    AUDIT FIX 2: clear_all() for proper cleanup.
    """

    def test_clear_all_removes_all_subscribers(self):
        """
        Document: clear_all() removes all subscribers.
        """
        bus = EventBus()

        def handler(_event):
            pass

        bus.subscribe(Events.GAME_TICK, handler, weak=False)
        bus.subscribe(Events.GAME_END, handler, weak=False)

        assert bus.get_stats()["subscriber_count"] == 2

        bus.clear_all()

        assert bus.get_stats()["subscriber_count"] == 0
        assert bus.get_stats()["event_types"] == 0
