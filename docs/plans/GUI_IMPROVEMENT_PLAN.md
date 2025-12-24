# GUI Improvement Plan - Phase 12E Preparation

**Date:** December 22, 2025
**Status:** READY FOR IMPLEMENTATION
**Dependencies:** Phase 12D Complete ✅

---

## Overview

This plan addresses critical issues found in the GUI audit and prepares the UI for Phase 12E (Protocol Explorer integration).

---

## Phase 1: Critical Bug Fixes (Priority: IMMEDIATE)

### 1.1 Fix Thread Safety - BrowserConnectionDialog

**File:** `src/ui/browser_connection_dialog.py`

**Problem:** UI mutations from background thread causing TclError crashes

**Fix:**
```python
# BEFORE (Line 150-223)
def _connect_async(self):
    """Runs in background thread"""
    self._log_progress("Connecting to browser...")  # ❌ Direct UI call

# AFTER
def _connect_async(self):
    """Runs in background thread"""
    self.root.after(0, lambda: self._log_progress("Connecting to browser..."))  # ✅ Thread-safe
```

**Test:**
```python
# tests/test_ui/test_browser_connection_dialog.py
def test_connect_async_thread_safety():
    """Verify _connect_async doesn't mutate UI from background thread"""
    dialog = BrowserConnectionDialog(root)

    # Mock root.after to verify it's called instead of direct UI mutation
    with patch.object(dialog.root, 'after') as mock_after:
        dialog._connect_async()
        assert mock_after.called
```

**Lines to change:** 150-223 (all `_log_progress()` calls inside `_connect_async()`)

---

### 1.2 Fix Subprocess Blocking - CaptureHandlers

**File:** `src/ui/handlers/capture_handlers.py`

**Problem:** `subprocess.run()` blocks UI thread for up to 30 seconds

**Fix:**
```python
# BEFORE (Line 74-80)
result = subprocess.run(
    ["python3", str(script_path), str(capture_file), "--report"],
    capture_output=True,
    text=True,
    timeout=30,  # ❌ BLOCKS UI THREAD
)

# AFTER
import threading

def _analyze_capture_async(self, script_path, capture_file):
    """Run analysis in background thread"""
    try:
        result = subprocess.run(
            ["python3", str(script_path), str(capture_file), "--report"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Update UI via dispatcher
        def update_ui():
            if result.returncode == 0:
                self.toast.show(f"Analysis complete: {result.stdout[:100]}", "success", 5000)
            else:
                self.toast.show(f"Analysis failed: {result.stderr[:100]}", "error", 5000)

        self.ui_dispatcher.submit(update_ui)
    except Exception as e:
        def show_error():
            self.toast.show(f"Analysis error: {str(e)}", "error", 5000)
        self.ui_dispatcher.submit(show_error)

# In the button handler:
def _analyze_raw_capture(self):
    thread = threading.Thread(
        target=self._analyze_capture_async,
        args=(script_path, capture_file),
        daemon=True
    )
    thread.start()
    self.toast.show("Analysis started...", "info", 2000)
```

**Test:**
```python
# tests/test_ui/test_capture_handlers.py
def test_analyze_capture_nonblocking():
    """Verify capture analysis doesn't block UI thread"""
    main_window = create_test_main_window()

    # Call analyze
    main_window._analyze_raw_capture()

    # UI should remain responsive (root.update() succeeds)
    main_window.root.update()
```

---

## Phase 2: Legacy System Removal (Priority: HIGH)

### 2.1 Remove Legacy Recorder Initialization

Legacy recorder initialization is no longer required. EventStore is the canonical capture path.

---

### 2.2 Remove CaptureHandlersMixin

**File:** `src/ui/handlers/capture_handlers.py`

**Action:** Delete entire file (171 lines)

**Rationale:**
- EventStore captures all WebSocket events automatically
- "Raw Capture" developer tool should be removed from menu

**Update main_window.py:**
```python
# REMOVE Line 38
from ui.handlers.capture_handlers import CaptureHandlersMixin

# REMOVE from class definition (Line 65)
class MainWindow(
    tk.Tk,
    # ... other mixins
    CaptureHandlersMixin,  # ❌ REMOVE THIS
    # ... other mixins
):
```

---

### 2.3 Remove RecordingHandlersMixin

**File:** `src/ui/handlers/recording_handlers.py`

**Action:** Delete entire file (195 lines)

**Rationale:**
- DemoRecorder is deprecated
- EventStore auto-captures all events
- Recording is always-on (no manual start/stop needed)

**Update main_window.py:**
```python
# REMOVE Line 41
from ui.handlers.recording_handlers import RecordingHandlersMixin

# REMOVE from class definition
class MainWindow(
    tk.Tk,
    # ... other mixins
    RecordingHandlersMixin,  # ❌ REMOVE THIS
    # ... other mixins
):
```

---

### 2.5 Update Menu Bar - Remove Legacy Items

**File:** `src/ui/builders/menu_bar_builder.py`

**Changes:**
```python
# REMOVE Recording menu items (Lines 120-135)
recording_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Recording", menu=recording_menu)
recording_menu.add_command(label="Configure & Start", ...)  # ❌ REMOVE
recording_menu.add_command(label="Stop Recording", ...)     # ❌ REMOVE

# REMOVE Developer Tools → Raw Capture (Lines 180-185)
dev_menu.add_command(label="Raw Capture", ...)  # ❌ REMOVE
dev_menu.add_command(label="Analyze Capture", ...)  # ❌ REMOVE
```

**Replace with:**
```python
# ADD new Capture menu
capture_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Capture", menu=capture_menu)
capture_menu.add_command(
    label="View Stats",
    command=lambda: main_window._open_capture_stats_dialog()
)
capture_menu.add_command(
    label="Export Session (JSONL)",
    command=lambda: main_window._export_session_jsonl()
)
capture_menu.add_separator()
capture_menu.add_command(
    label="Open Data Directory",
    command=lambda: main_window._open_data_directory()
)
```

---

## Phase 3: Path Migration (Priority: HIGH)

### 3.1 Add RUGS_DATA_DIR Support

**File:** `src/ui/main_window.py`

**Changes:**
```python
# ADD at top (after imports)
import os
from pathlib import Path

RUGS_DATA_DIR = Path(os.getenv("RUGS_DATA_DIR", Path.home() / "rugs_data"))

# REPLACE Line 110
# BEFORE
demo_dir = Path(config.FILES.get("recordings_dir", "rugs_recordings")) / "demonstrations"

# AFTER
# No demo_dir needed (legacy recorder removed)

# REPLACE Line 639
# BEFORE
recordings_dir = self.config.FILES.get("recordings_dir", "rugs_recordings")

# AFTER
def _open_data_directory(self):
    """Open RUGS_DATA_DIR in file manager"""
    import subprocess
    data_dir = RUGS_DATA_DIR
    if data_dir.exists():
        subprocess.Popen(["xdg-open", str(data_dir)])  # Linux
        # subprocess.Popen(["open", str(data_dir)])     # macOS
        # subprocess.Popen(["explorer", str(data_dir)]) # Windows
```

---

self.toast.success("Config updated")  # ✅ Use convenience method
```

---

### 4.2 EventBus Injection Standardization

**Problem:** Mixed global imports and constructor injection

**Files to update:**
- `src/ui/handlers/capture_handlers.py` (will be deleted anyway)

**Pattern to enforce:**
```python
# ❌ BAD - Global import
from services.event_bus import event_bus
event_bus.subscribe(...)

# ✅ GOOD - Constructor injection
class MyClass:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.event_bus.subscribe(...)
```

**Grep command to find violations:**
```bash
grep -r "from services.event_bus import event_bus" src/ui/
```

---

## Phase 5: Enhanced Features (Priority: MEDIUM)

### 5.1 Enhanced Capture Stats Panel

**Goal:** Show event counts by type

**File:** `src/services/event_store/writer.py`

**Add property:**
```python
from collections import defaultdict

class EventStoreService:
    def __init__(self, ...):
        # ... existing code
        self._counts_by_type: Dict[str, int] = defaultdict(int)

    def _write_batch(self, batch: List[Event]):
        # ... existing write logic
        for event in batch:
            self._counts_by_type[event.doc_type] += 1

    @property
    def event_counts_by_type(self) -> Dict[str, int]:
        """Get event counts broken down by doc_type"""
        return dict(self._counts_by_type)
```

**File:** `src/ui/handlers/event_handlers.py`

**Update display:**
```python
def _update_capture_stats(self: "MainWindow"):
    try:
        if hasattr(self, "event_store_service") and self.event_store_service:
            session_id = self.event_store_service.session_id[:8]
            counts = self.event_store_service.event_counts_by_type
            total = sum(counts.values())

            # Abbreviated type names for compact display
            ws = counts.get("ws_event", 0)
            ticks = counts.get("game_tick", 0)
            trades = counts.get("player_action", 0)
            state = counts.get("server_state", 0)

            text = f"Session: {session_id} | Events: {total} ({ws}ws/{ticks}t/{trades}tr/{state}st)"
            self.capture_stats_label.config(text=text)
    except Exception as e:
        logger.debug(f"Error updating capture stats: {e}")

    self.root.after(1000, self._update_capture_stats)
```

**Test:**
```python
# tests/test_services/test_event_store.py
def test_event_counts_by_type():
    """Verify event counts tracked by doc_type"""
    store = EventStoreService(session_id="test", ...)

    # Publish different event types
    event_bus.publish(Events.WS_RAW_EVENT, {...})  # ws_event
    event_bus.publish(Events.GAME_TICK, {...})     # game_tick

    # Wait for processing
    time.sleep(0.1)

    counts = store.event_counts_by_type
    assert counts["ws_event"] == 1
    assert counts["game_tick"] == 1
```

---

### 5.2 Balance Display Throttling

**Goal:** Prevent UI jank from rapid balance updates

**File:** `src/ui/handlers/player_handlers.py`

**Add throttling:**
```python
import time

class PlayerHandlersMixin:
    def __init__(self):
        # ... existing code
        self._last_balance_update = 0.0

    def _update_balance_from_live_state(self: "MainWindow"):
        # Throttle to 100ms (10 FPS max)
        now = time.time()
        if now - self._last_balance_update < 0.1:
            return
        self._last_balance_update = now

        # ... existing update logic
```

---

### 5.3 Status Bar Visual Grouping

**Goal:** Improve visual hierarchy with separators

**File:** `src/ui/builders/status_bar_builder.py`

**Add separators:**
```python
def build_status_bar(root, config):
    status_bar = tk.Frame(root, height=30, bg="#000000")

    # Group 1: Game State
    tick_label = tk.Label(status_bar, text="TICK: 0", ...)
    price_label = tk.Label(status_bar, text="PRICE: 1.0000 X", ...)
    phase_label = tk.Label(status_bar, text="PHASE: UNKNOWN", ...)

    # Separator 1
    sep1 = tk.Frame(status_bar, width=2, bg="#333333")
    sep1.pack(side="left", fill="y", padx=5)

    # Group 2: Connection
    player_label = tk.Label(status_bar, text="👤 Not Authenticated", ...)
    browser_label = tk.Label(status_bar, text="BROWSER: ⚫", ...)
    source_label = tk.Label(status_bar, text="🔴 No Source", ...)

    # Separator 2
    sep2 = tk.Frame(status_bar, width=2, bg="#333333")
    sep2.pack(side="left", fill="y", padx=5)

    # Group 3: Recording
    recording_toggle = tk.Button(status_bar, text="⏺ REC OFF", ...)
    capture_stats_label = tk.Label(status_bar, text="Session: -------- | Events: 0", ...)

    return status_bar
```

---

## Phase 6: Phase 12E Prep (Priority: LOW - Future Work)

### 6.1 Protocol Explorer Panel (Phase 12E)

**Goal:** Add UI for querying captured events via ChromaDB

**File:** `src/ui/panels/protocol_explorer_panel.py` (NEW)

**Implementation:**
```python
import tkinter as tk
from tkinter import ttk, scrolledtext

class ProtocolExplorerPanel(ttk.Frame):
    def __init__(self, parent, chroma_client):
        super().__init__(parent)
        self.chroma = chroma_client

        # Query input
        query_label = ttk.Label(self, text="Query:")
        query_label.pack(anchor="w", padx=5, pady=5)

        self.query_entry = ttk.Entry(self, width=80)
        self.query_entry.pack(fill="x", padx=5, pady=5)

        # Search button
        search_btn = ttk.Button(self, text="🔍 Search", command=self._search)
        search_btn.pack(anchor="w", padx=5, pady=5)

        # Results display
        results_label = ttk.Label(self, text="Results:")
        results_label.pack(anchor="w", padx=5, pady=5)

        self.results_text = scrolledtext.ScrolledText(self, height=20, width=100)
        self.results_text.pack(fill="both", expand=True, padx=5, pady=5)

    def _search(self):
        query = self.query_entry.get()
        if not query:
            return

        # Query ChromaDB
        results = self.chroma.query(
            collection_name="rugs_events",
            query_texts=[query],
            n_results=5
        )

        # Display results
        self.results_text.delete("1.0", tk.END)
        for doc, metadata in zip(results["documents"], results["metadatas"]):
            self.results_text.insert(tk.END, f"Event: {metadata.get('doc_type', 'unknown')}\n")
            self.results_text.insert(tk.END, f"{doc}\n\n")
```

**Integration:**
```python
# src/ui/main_window.py
from ui.panels.protocol_explorer_panel import ProtocolExplorerPanel

# Add as new tab
explorer_panel = ProtocolExplorerPanel(self.notebook, chroma_client)
self.notebook.add(explorer_panel, text="Protocol Explorer")
```

---

### 6.2 DuckDB Query Panel (Phase 12E)

**Goal:** Add UI for running SQL queries on Parquet data

**File:** `src/ui/panels/data_explorer_panel.py` (NEW)

**Implementation:**
```python
import tkinter as tk
from tkinter import ttk, scrolledtext
import duckdb
import pandas as pd

class DataExplorerPanel(ttk.Frame):
    def __init__(self, parent, rugs_data_dir):
        super().__init__(parent)
        self.conn = duckdb.connect()
        self.parquet_path = rugs_data_dir / "events_parquet"

        # SQL input
        sql_label = ttk.Label(self, text="SQL Query:")
        sql_label.pack(anchor="w", padx=5, pady=5)

        self.sql_text = scrolledtext.ScrolledText(self, height=5, width=100)
        self.sql_text.pack(fill="x", padx=5, pady=5)

        # Default query
        self.sql_text.insert("1.0", """SELECT ts, doc_type, username, raw_json
FROM read_parquet('~/rugs_data/events_parquet/**/*.parquet')
ORDER BY ts DESC
LIMIT 10""")

        # Run button
        run_btn = ttk.Button(self, text="▶️ Run Query", command=self._run_query)
        run_btn.pack(anchor="w", padx=5, pady=5)

        # Results table
        results_label = ttk.Label(self, text="Results:")
        results_label.pack(anchor="w", padx=5, pady=5)

        self.results_tree = ttk.Treeview(self, height=15)
        self.results_tree.pack(fill="both", expand=True, padx=5, pady=5)

    def _run_query(self):
        sql = self.sql_text.get("1.0", tk.END).strip()
        if not sql:
            return

        try:
            df = self.conn.execute(sql).df()

            # Clear previous results
            self.results_tree.delete(*self.results_tree.get_children())

            # Configure columns
            self.results_tree["columns"] = list(df.columns)
            self.results_tree["show"] = "headings"

            for col in df.columns:
                self.results_tree.heading(col, text=col)
                self.results_tree.column(col, width=150)

            # Insert rows
            for _, row in df.iterrows():
                self.results_tree.insert("", "end", values=list(row))

        except Exception as e:
            # Show error in results
            self.results_tree.delete(*self.results_tree.get_children())
            self.results_tree["columns"] = ["Error"]
            self.results_tree.heading("Error", text="Error")
            self.results_tree.insert("", "end", values=[str(e)])
```

---

## Implementation Order

### Week 1: Critical Fixes
1. ✅ Fix thread safety (BrowserConnectionDialog)
2. ✅ Fix subprocess blocking (CaptureHandlers)
3. ✅ Set legacy flags to false in `.env` file

### Week 2: Legacy Removal
4. ✅ Remove legacy recorder initialization
5. ✅ Delete CaptureHandlersMixin
6. ✅ Delete RecordingHandlersMixin
8. ✅ Update menu bar (remove legacy items)

### Week 3: Cleanup & Enhancement
9. ✅ Migrate to RUGS_DATA_DIR
10. ✅ Standardize toast API
11. ✅ Enhanced capture stats (event counts by type)
12. ✅ Balance display throttling
13. ✅ Status bar visual grouping

### Week 4: Phase 12E Prep (Optional)
14. 🔲 Protocol Explorer panel
15. 🔲 DuckDB Query panel

---

## Testing Strategy

### Unit Tests
```bash
# Test thread safety
cd src && python3 -m pytest tests/test_ui/test_thread_safety.py -v

# Test legacy removal
cd src && python3 -m pytest tests/test_ui/test_legacy_removal.py -v

# Test EventStore UI integration
cd src && python3 -m pytest tests/test_ui/test_event_handlers.py -v

# Test LiveStateProvider UI integration
cd src && python3 -m pytest tests/test_ui/test_player_handlers.py -v
```

### Manual Testing
1. Launch GUI: `./run.sh`
2. Connect to live feed
3. Verify capture stats update in real-time
4. Verify balance display shows server value (green)
5. Disconnect from live feed
6. Verify balance display shows local value (gray)
7. Test browser connection (no crashes)
8. Verify capture analysis doesn't freeze UI

### Regression Testing
```bash
# All tests should pass
cd src && python3 -m pytest tests/ -v
```

---

## Rollback Plan

If issues arise:
1. Re-enable legacy flags: `export LEGACY_RECORDER_SINK=true`
2. Revert menu bar changes
3. Re-add legacy recorder initialization

All legacy code remains in git history for emergency rollback.

---

## Success Criteria

✅ No thread safety crashes
✅ UI remains responsive during all operations
✅ Legacy recorders removed from codebase
✅ All tests passing (1127+ tests)
✅ EventStore captures all events
✅ LiveStateProvider balance display working
✅ Capture stats display working
✅ Clean menu structure (no deprecated items)
✅ RUGS_DATA_DIR used consistently

---

**End of Plan**
