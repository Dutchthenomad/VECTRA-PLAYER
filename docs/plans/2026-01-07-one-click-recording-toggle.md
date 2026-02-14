# One-Click Recording Toggle Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a 1-click REC button to toggle EventStore recording on/off, with recording OFF by default and automatic game deduplication on stop.

**Architecture:**
- Add `RecordingController` to manage EventStore lifecycle and track recorded game_ids
- Add REC button to MinimalWindow status bar (between BALANCE and CONNECTION)
- EventStore starts in "paused" state; toggled via UI button
- On stop: deduplicate `complete_game` records by `game_id` before final flush

**Tech Stack:** Tkinter, EventBus, EventStoreService, DuckDB (for dedup queries)

---

## Summary of Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `src/services/event_store/service.py` | Modify | Add `pause()`/`resume()` methods, start paused by default |
| `src/ui/controllers/recording_controller.py` | Create | New controller for recording state management |
| `src/ui/minimal_window.py` | Modify | Add REC button to status bar |
| `src/services/event_bus.py` | Modify | Add `RECORDING_STARTED`/`RECORDING_STOPPED` events |
| `tests/test_services/test_event_store/test_recording_toggle.py` | Create | Tests for pause/resume functionality |
| `tests/test_ui/test_recording_controller.py` | Create | Tests for recording controller |

---

## Task 1: Add Recording State to EventStoreService

**Files:**
- Modify: `src/services/event_store/service.py:1-50`
- Test: `src/tests/test_services/test_event_store/test_recording_toggle.py`

### Step 1.1: Write the failing test for pause/resume

Create test file:

```python
# src/tests/test_services/test_event_store/test_recording_toggle.py
"""Tests for EventStoreService recording toggle functionality."""

import pytest
from unittest.mock import MagicMock, patch
from services.event_store.service import EventStoreService
from services.event_bus import EventBus


class TestEventStoreRecordingToggle:
    """Test EventStoreService pause/resume functionality."""

    @pytest.fixture
    def event_bus(self):
        """Create a mock event bus."""
        bus = MagicMock(spec=EventBus)
        return bus

    @pytest.fixture
    def event_store(self, event_bus, tmp_path):
        """Create EventStoreService with temp directory."""
        with patch('services.event_store.service.EventStorePaths') as mock_paths:
            mock_paths.return_value.events_dir = tmp_path / "events"
            mock_paths.return_value.events_dir.mkdir(parents=True, exist_ok=True)
            service = EventStoreService(event_bus)
            yield service
            if service._running:
                service.stop()

    def test_starts_paused_by_default(self, event_store):
        """EventStore should start in paused state."""
        event_store.start()
        assert event_store.is_paused is True
        assert event_store.is_recording is False

    def test_resume_enables_recording(self, event_store):
        """resume() should enable event recording."""
        event_store.start()
        assert event_store.is_paused is True

        event_store.resume()

        assert event_store.is_paused is False
        assert event_store.is_recording is True

    def test_pause_disables_recording(self, event_store):
        """pause() should disable event recording."""
        event_store.start()
        event_store.resume()
        assert event_store.is_recording is True

        event_store.pause()

        assert event_store.is_paused is True
        assert event_store.is_recording is False

    def test_events_not_written_when_paused(self, event_store):
        """Events should not be written when paused."""
        event_store.start()
        assert event_store.is_paused is True

        # Simulate event - should be dropped
        initial_count = event_store.event_count
        event_store._on_ws_raw_event({
            'event_name': 'gameStateUpdate',
            'data': {'test': 'data'},
            'source': 'cdp'
        })

        assert event_store.event_count == initial_count

    def test_events_written_when_recording(self, event_store):
        """Events should be written when recording."""
        event_store.start()
        event_store.resume()

        initial_count = event_store.event_count
        event_store._on_ws_raw_event({
            'event_name': 'gameStateUpdate',
            'data': {'test': 'data'},
            'source': 'cdp'
        })

        assert event_store.event_count > initial_count

    def test_toggle_recording(self, event_store):
        """toggle_recording() should flip recording state."""
        event_store.start()
        assert event_store.is_recording is False

        event_store.toggle_recording()
        assert event_store.is_recording is True

        event_store.toggle_recording()
        assert event_store.is_recording is False

    def test_recorded_game_ids_tracked(self, event_store):
        """Service should track unique game_ids recorded."""
        event_store.start()
        event_store.resume()

        assert len(event_store.recorded_game_ids) == 0

        # Record a complete game
        event_store._on_complete_game({
            'id': 'game_001',
            'prices': [1.0, 1.1, 1.2],
            'peakMultiplier': 1.2
        })

        assert 'game_001' in event_store.recorded_game_ids
        assert len(event_store.recorded_game_ids) == 1

    def test_duplicate_games_not_written(self, event_store):
        """Duplicate game_ids should not be written twice."""
        event_store.start()
        event_store.resume()

        # Record same game twice
        game_data = {
            'id': 'game_001',
            'prices': [1.0, 1.1, 1.2],
            'peakMultiplier': 1.2
        }

        event_store._on_complete_game(game_data)
        count_after_first = event_store.event_count

        event_store._on_complete_game(game_data)
        count_after_second = event_store.event_count

        # Should not have incremented
        assert count_after_second == count_after_first
        assert len(event_store.recorded_game_ids) == 1
```

### Step 1.2: Run test to verify it fails

```bash
cd /home/devops/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_services/test_event_store/test_recording_toggle.py -v
```

Expected: FAIL with `AttributeError: 'EventStoreService' object has no attribute 'is_paused'`

### Step 1.3: Implement pause/resume in EventStoreService

Modify `src/services/event_store/service.py`:

Add these instance variables in `__init__`:

```python
# In __init__, after existing initializations:
self._paused = True  # Start paused by default
self._recorded_game_ids: set[str] = set()  # Track for deduplication
self._event_count = 0
```

Add these properties after `__init__`:

```python
@property
def is_paused(self) -> bool:
    """Whether recording is currently paused."""
    return self._paused

@property
def is_recording(self) -> bool:
    """Whether actively recording (running and not paused)."""
    return self._running and not self._paused

@property
def event_count(self) -> int:
    """Total events recorded this session."""
    return self._event_count

@property
def recorded_game_ids(self) -> set[str]:
    """Set of game_ids recorded this session (for dedup)."""
    return self._recorded_game_ids.copy()

def pause(self) -> None:
    """Pause recording (events will be dropped)."""
    self._paused = True
    self.logger.info("Recording PAUSED")

def resume(self) -> None:
    """Resume recording."""
    self._paused = False
    self.logger.info("Recording RESUMED")

def toggle_recording(self) -> bool:
    """Toggle recording state. Returns new is_recording state."""
    if self._paused:
        self.resume()
    else:
        self.pause()
    return self.is_recording
```

Add early return guard in all `_on_*` event handlers:

```python
# Add at TOP of each _on_* method:
def _on_ws_raw_event(self, data: dict) -> None:
    """Handle raw WebSocket event."""
    if self._paused:
        return  # Drop events when paused
    # ... rest of existing code
```

Add deduplication in `_on_complete_game`:

```python
def _on_complete_game(self, data: dict) -> None:
    """Handle complete game from gameHistory."""
    if self._paused:
        return

    game_id = data.get('id')
    if game_id and game_id in self._recorded_game_ids:
        self.logger.debug(f"Skipping duplicate game: {game_id}")
        return

    if game_id:
        self._recorded_game_ids.add(game_id)

    # ... rest of existing code
    self._event_count += 1
```

### Step 1.4: Run test to verify it passes

```bash
cd /home/devops/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_services/test_event_store/test_recording_toggle.py -v
```

Expected: All tests PASS

### Step 1.5: Commit

```bash
git add src/services/event_store/service.py src/tests/test_services/test_event_store/test_recording_toggle.py
git commit -m "$(cat <<'EOF'
feat(event-store): Add pause/resume recording with game deduplication

- EventStore starts paused by default (no recording until toggled)
- Add pause(), resume(), toggle_recording() methods
- Track recorded game_ids to prevent duplicate complete_game writes
- Add is_paused, is_recording, event_count, recorded_game_ids properties

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add Recording Events to EventBus

**Files:**
- Modify: `src/services/event_bus.py:1-50` (Events enum)
- No separate test needed (covered by integration tests)

### Step 2.1: Add event types to Events enum

In `src/services/event_bus.py`, add to the `Events` class:

```python
# Recording events
RECORDING_STARTED = "recording.started"
RECORDING_STOPPED = "recording.stopped"
RECORDING_TOGGLED = "recording.toggled"
```

### Step 2.2: Commit

```bash
git add src/services/event_bus.py
git commit -m "$(cat <<'EOF'
feat(event-bus): Add recording lifecycle events

- RECORDING_STARTED, RECORDING_STOPPED, RECORDING_TOGGLED

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Create RecordingController

**Files:**
- Create: `src/ui/controllers/recording_controller.py`
- Test: `src/tests/test_ui/test_recording_controller.py`

### Step 3.1: Write the failing test

```python
# src/tests/test_ui/test_recording_controller.py
"""Tests for RecordingController."""

import pytest
from unittest.mock import MagicMock, patch
from ui.controllers.recording_controller import RecordingController


class TestRecordingController:
    """Test RecordingController functionality."""

    @pytest.fixture
    def mock_event_store(self):
        """Create mock EventStoreService."""
        store = MagicMock()
        store.is_recording = False
        store.is_paused = True
        store.event_count = 0
        store.recorded_game_ids = set()
        return store

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock EventBus."""
        return MagicMock()

    @pytest.fixture
    def controller(self, mock_event_store, mock_event_bus):
        """Create RecordingController with mocks."""
        return RecordingController(
            event_store=mock_event_store,
            event_bus=mock_event_bus
        )

    def test_initial_state_not_recording(self, controller):
        """Controller should start in non-recording state."""
        assert controller.is_recording is False

    def test_toggle_starts_recording(self, controller, mock_event_store):
        """toggle() should start recording when paused."""
        mock_event_store.toggle_recording.return_value = True
        mock_event_store.is_recording = True

        result = controller.toggle()

        assert result is True
        mock_event_store.toggle_recording.assert_called_once()

    def test_toggle_stops_recording(self, controller, mock_event_store):
        """toggle() should stop recording when active."""
        mock_event_store.is_recording = True
        mock_event_store.toggle_recording.return_value = False

        result = controller.toggle()

        assert result is False
        mock_event_store.toggle_recording.assert_called_once()

    def test_toggle_publishes_event(self, controller, mock_event_store, mock_event_bus):
        """toggle() should publish RECORDING_TOGGLED event."""
        mock_event_store.toggle_recording.return_value = True

        controller.toggle()

        mock_event_bus.publish.assert_called()

    def test_get_status_returns_dict(self, controller, mock_event_store):
        """get_status() should return recording status dict."""
        mock_event_store.is_recording = True
        mock_event_store.event_count = 42
        mock_event_store.recorded_game_ids = {'game1', 'game2'}

        status = controller.get_status()

        assert status['is_recording'] is True
        assert status['event_count'] == 42
        assert status['game_count'] == 2

    def test_start_recording(self, controller, mock_event_store):
        """start() should explicitly start recording."""
        mock_event_store.is_paused = True

        controller.start()

        mock_event_store.resume.assert_called_once()

    def test_stop_recording(self, controller, mock_event_store):
        """stop() should explicitly stop recording."""
        mock_event_store.is_recording = True

        controller.stop()

        mock_event_store.pause.assert_called_once()
```

### Step 3.2: Run test to verify it fails

```bash
cd /home/devops/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_ui/test_recording_controller.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ui.controllers.recording_controller'`

### Step 3.3: Implement RecordingController

```python
# src/ui/controllers/recording_controller.py
"""
Recording Controller - Manages EventStore recording state from UI.

Provides:
- 1-click toggle for recording on/off
- Status reporting (event count, game count)
- Event publishing for UI updates
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.event_store.service import EventStoreService
    from services.event_bus import EventBus

from services.event_bus import Events


class RecordingController:
    """
    Controller for managing recording state.

    Bridges the UI (REC button) with EventStoreService.
    """

    def __init__(
        self,
        event_store: "EventStoreService",
        event_bus: "EventBus",
    ):
        """
        Initialize recording controller.

        Args:
            event_store: EventStoreService instance to control
            event_bus: EventBus for publishing state changes
        """
        self.event_store = event_store
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)

    @property
    def is_recording(self) -> bool:
        """Whether currently recording."""
        return self.event_store.is_recording

    def toggle(self) -> bool:
        """
        Toggle recording state.

        Returns:
            New recording state (True = recording, False = paused)
        """
        new_state = self.event_store.toggle_recording()

        # Publish event for UI updates
        self.event_bus.publish(Events.RECORDING_TOGGLED, {
            'is_recording': new_state,
            'event_count': self.event_store.event_count,
            'game_count': len(self.event_store.recorded_game_ids),
        })

        if new_state:
            self.logger.info("Recording STARTED")
            self.event_bus.publish(Events.RECORDING_STARTED, {})
        else:
            self.logger.info(
                f"Recording STOPPED - {self.event_store.event_count} events, "
                f"{len(self.event_store.recorded_game_ids)} games"
            )
            self.event_bus.publish(Events.RECORDING_STOPPED, {
                'event_count': self.event_store.event_count,
                'game_count': len(self.event_store.recorded_game_ids),
            })

        return new_state

    def start(self) -> None:
        """Explicitly start recording."""
        if self.event_store.is_paused:
            self.event_store.resume()
            self.event_bus.publish(Events.RECORDING_STARTED, {})
            self.logger.info("Recording STARTED")

    def stop(self) -> None:
        """Explicitly stop recording."""
        if self.event_store.is_recording:
            self.event_store.pause()
            self.event_bus.publish(Events.RECORDING_STOPPED, {
                'event_count': self.event_store.event_count,
                'game_count': len(self.event_store.recorded_game_ids),
            })
            self.logger.info(
                f"Recording STOPPED - {self.event_store.event_count} events, "
                f"{len(self.event_store.recorded_game_ids)} games"
            )

    def get_status(self) -> dict:
        """
        Get current recording status.

        Returns:
            Dict with is_recording, event_count, game_count
        """
        return {
            'is_recording': self.event_store.is_recording,
            'event_count': self.event_store.event_count,
            'game_count': len(self.event_store.recorded_game_ids),
        }
```

### Step 3.4: Run test to verify it passes

```bash
cd /home/devops/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_ui/test_recording_controller.py -v
```

Expected: All tests PASS

### Step 3.5: Commit

```bash
git add src/ui/controllers/recording_controller.py src/tests/test_ui/test_recording_controller.py
git commit -m "$(cat <<'EOF'
feat(ui): Add RecordingController for 1-click recording toggle

- toggle() flips recording state and publishes events
- start()/stop() for explicit control
- get_status() returns event_count and game_count
- Publishes RECORDING_STARTED/STOPPED/TOGGLED events

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Add REC Button to MinimalWindow

**Files:**
- Modify: `src/ui/minimal_window.py:200-300` (status bar section)
- Test: `src/tests/test_ui/test_minimal_window.py` (add recording tests)

### Step 4.1: Write the failing test

Add to existing `src/tests/test_ui/test_minimal_window.py`:

```python
# Add to existing test file
class TestRecordingButton:
    """Test REC button functionality."""

    @pytest.fixture
    def window_with_recording(self, root, mock_services):
        """Create MinimalWindow with recording controller."""
        # mock_services should include event_store
        mock_services['event_store'] = MagicMock()
        mock_services['event_store'].is_recording = False
        mock_services['event_store'].is_paused = True

        window = MinimalWindow(root, **mock_services)
        yield window
        window.destroy()

    def test_rec_button_exists(self, window_with_recording):
        """REC button should exist in status bar."""
        assert hasattr(window_with_recording, 'rec_button')
        assert window_with_recording.rec_button is not None

    def test_rec_button_initial_state_gray(self, window_with_recording):
        """REC button should be gray when not recording."""
        button = window_with_recording.rec_button
        assert button.cget('bg') in ['gray', 'grey', '#808080']

    def test_rec_button_click_toggles_recording(self, window_with_recording):
        """Clicking REC should toggle recording state."""
        window_with_recording.recording_controller.toggle = MagicMock(return_value=True)

        # Simulate button click
        window_with_recording._on_rec_clicked()

        window_with_recording.recording_controller.toggle.assert_called_once()

    def test_rec_button_turns_red_when_recording(self, window_with_recording):
        """REC button should turn red when recording."""
        window_with_recording.update_recording_state(is_recording=True)

        button = window_with_recording.rec_button
        assert button.cget('bg') in ['red', '#FF0000', '#ff0000']

    def test_rec_button_shows_indicator_when_recording(self, window_with_recording):
        """REC button should show indicator when recording."""
        window_with_recording.update_recording_state(is_recording=True)

        button = window_with_recording.rec_button
        assert '●' in button.cget('text') or 'REC' in button.cget('text')
```

### Step 4.2: Run test to verify it fails

```bash
cd /home/devops/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_ui/test_minimal_window.py::TestRecordingButton -v
```

Expected: FAIL with `AttributeError: 'MinimalWindow' object has no attribute 'rec_button'`

### Step 4.3: Add REC button to MinimalWindow

In `src/ui/minimal_window.py`:

**Add import at top:**
```python
from ui.controllers.recording_controller import RecordingController
```

**Add to __init__ parameters:**
```python
def __init__(
    self,
    root: tk.Tk,
    event_bus: "EventBus",
    browser_bridge: "BrowserBridge",
    live_state_provider: "LiveStateProvider" = None,
    event_store: "EventStoreService" = None,  # ADD THIS
):
```

**Add after other controller initializations:**
```python
# Recording controller
self.recording_controller = None
if event_store:
    self.recording_controller = RecordingController(
        event_store=event_store,
        event_bus=event_bus,
    )
```

**In `_create_status_bar()`, add REC button before CONNECTION indicator:**
```python
# REC button (before connection indicator)
self.rec_button = tk.Button(
    status_frame,
    text="REC",
    font=("Consolas", 9, "bold"),
    width=4,
    height=1,
    bg="gray",
    fg="white",
    activebackground="darkgray",
    command=self._on_rec_clicked,
)
self.rec_button.pack(side=tk.LEFT, padx=(5, 2))
```

**Add callback method:**
```python
def _on_rec_clicked(self) -> None:
    """Handle REC button click."""
    if not self.recording_controller:
        self.logger.warning("Recording controller not available")
        return

    is_recording = self.recording_controller.toggle()
    self.update_recording_state(is_recording=is_recording)

def update_recording_state(self, is_recording: bool) -> None:
    """Update REC button visual state."""
    if is_recording:
        self.rec_button.config(
            text="● REC",
            bg="red",
            fg="white",
            activebackground="darkred",
        )
    else:
        self.rec_button.config(
            text="REC",
            bg="gray",
            fg="white",
            activebackground="darkgray",
        )
```

**Subscribe to recording events in `_setup_event_subscriptions()`:**
```python
# Recording state changes
self.event_bus.subscribe(
    Events.RECORDING_TOGGLED,
    self._on_recording_toggled,
    weak=False,
)

def _on_recording_toggled(self, data: dict) -> None:
    """Handle recording state change."""
    self.root.after(0, lambda: self.update_recording_state(data.get('is_recording', False)))
```

### Step 4.4: Run test to verify it passes

```bash
cd /home/devops/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/test_ui/test_minimal_window.py::TestRecordingButton -v
```

Expected: All tests PASS

### Step 4.5: Commit

```bash
git add src/ui/minimal_window.py src/tests/test_ui/test_minimal_window.py
git commit -m "$(cat <<'EOF'
feat(ui): Add REC button to status bar for 1-click recording toggle

- Gray "REC" button when not recording
- Red "● REC" button when recording
- Click toggles EventStore recording state
- Subscribes to RECORDING_TOGGLED for state sync

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Wire Up EventStore in Main Application

**Files:**
- Modify: `src/main.py:240-250` (EventStore initialization)

### Step 5.1: Pass event_store to MinimalWindow

In `src/main.py`, find where MinimalWindow is created and add the event_store parameter:

```python
# Before (around line 270-280):
self.window = MinimalWindow(
    root=self.root,
    event_bus=self.event_bus,
    browser_bridge=self.browser_bridge,
    live_state_provider=self.live_state_provider,
)

# After:
self.window = MinimalWindow(
    root=self.root,
    event_bus=self.event_bus,
    browser_bridge=self.browser_bridge,
    live_state_provider=self.live_state_provider,
    event_store=self.event_store,  # ADD THIS
)
```

### Step 5.2: Run full test suite

```bash
cd /home/devops/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -m pytest tests/ -v --tb=short
```

Expected: All tests PASS

### Step 5.3: Commit

```bash
git add src/main.py
git commit -m "$(cat <<'EOF'
feat(main): Wire EventStore to MinimalWindow for recording toggle

- Pass event_store to MinimalWindow constructor
- Enables REC button functionality

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Integration Test - Manual Verification

### Step 6.1: Launch application

```bash
cd /home/devops/Desktop/VECTRA-PLAYER && ./run.sh
```

### Step 6.2: Verify REC button behavior

1. **Initial state:** REC button should be gray with text "REC"
2. **Click REC:** Button should turn red with text "● REC"
3. **Click again:** Button should return to gray "REC"
4. **Check logs:** Should see "Recording STARTED" / "Recording STOPPED" messages

### Step 6.3: Verify data capture

1. Start recording (click REC)
2. Wait for 2-3 games to complete
3. Stop recording (click REC)
4. Check output:
   ```bash
   ls -la ~/rugs_data/events_parquet/doc_type=complete_game/
   ```

### Step 6.4: Verify deduplication

```bash
cd /home/devops/Desktop/VECTRA-PLAYER/src && ../.venv/bin/python -c "
import duckdb
conn = duckdb.connect()
df = conn.execute('''
    SELECT
        json_extract_string(raw_json, \"$.id\") as game_id,
        COUNT(*) as count
    FROM read_parquet('~/rugs_data/events_parquet/doc_type=complete_game/**/*.parquet')
    GROUP BY game_id
    HAVING count > 1
''').df()
print('Duplicate games:', len(df))
print(df)
"
```

Expected: No duplicates (or very few from previous sessions)

### Step 6.5: Final commit

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat: Complete 1-click recording toggle implementation

Summary:
- EventStore starts paused by default (OFF)
- REC button in status bar toggles recording
- Visual feedback: gray=off, red=recording
- Automatic game_id deduplication prevents duplicate complete_game records
- Recording events published for UI sync

Closes: Recording toggle feature

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Verification Checklist

- [ ] EventStore starts paused (not recording)
- [ ] REC button visible in status bar (gray)
- [ ] Click REC starts recording (button turns red)
- [ ] Click REC again stops recording (button turns gray)
- [ ] Events not written when paused
- [ ] Events written when recording
- [ ] Duplicate game_ids filtered out
- [ ] RECORDING_STARTED/STOPPED events published
- [ ] All tests pass
- [ ] Manual integration test passes

---

## Rollback Plan

If issues occur:

```bash
# Revert all changes
git revert HEAD~5..HEAD

# Or reset to before feature
git reset --hard HEAD~5
```

---

*Plan created: 2026-01-07*
*Estimated tasks: 6*
*TDD approach: Yes*
