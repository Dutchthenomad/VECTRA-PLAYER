"""
Toggle Switch Widget - Custom Canvas-based toggle for reliable visual feedback.

Bypasses Tk theming issues by drawing its own visual state.
"""

import tkinter as tk
from collections.abc import Callable


class ToggleSwitch(tk.Canvas):
    """
    A custom toggle switch widget drawn on a Canvas.

    Provides reliable visual feedback regardless of desktop theme.
    """

    def __init__(
        self,
        parent: tk.Widget,
        width: int = 60,
        height: int = 28,
        on_color: str = "#cc0000",
        off_color: str = "#555555",
        knob_color: str = "#ffffff",
        label_on: str = "REC",
        label_off: str = "OFF",
        command: Callable[[], None] | None = None,
        initial_state: bool = False,
    ):
        """
        Initialize toggle switch.

        Args:
            parent: Parent widget
            width: Switch width in pixels
            height: Switch height in pixels
            on_color: Background color when ON
            off_color: Background color when OFF
            knob_color: Color of the sliding knob
            label_on: Text shown when ON
            label_off: Text shown when OFF
            command: Callback when toggled
            initial_state: Initial ON/OFF state
        """
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg"),
            highlightthickness=0,
            cursor="hand2",
        )

        self.width = width
        self.height = height
        self.on_color = on_color
        self.off_color = off_color
        self.knob_color = knob_color
        self.label_on = label_on
        self.label_off = label_off
        self.command = command
        self._is_on = initial_state

        # Knob dimensions
        self.knob_radius = (height - 6) // 2
        self.knob_padding = 3

        # Bind click events
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        # Draw initial state
        self._draw()

    @property
    def is_on(self) -> bool:
        """Get current state."""
        return self._is_on

    @is_on.setter
    def is_on(self, value: bool) -> None:
        """Set state and redraw."""
        self._is_on = value
        self._draw()

    def toggle(self) -> bool:
        """Toggle state and return new state."""
        self._is_on = not self._is_on
        self._draw()
        return self._is_on

    def set_state(self, is_on: bool) -> None:
        """Set state without triggering callback."""
        self._is_on = is_on
        self._draw()

    def _draw(self) -> None:
        """Draw the toggle switch."""
        self.delete("all")

        # Colors based on state
        bg_color = self.on_color if self._is_on else self.off_color
        label = self.label_on if self._is_on else self.label_off

        # Draw rounded rectangle background
        radius = self.height // 2
        self._draw_rounded_rect(0, 0, self.width, self.height, radius, bg_color)

        # Draw knob position
        if self._is_on:
            knob_x = self.width - self.knob_padding - self.knob_radius
        else:
            knob_x = self.knob_padding + self.knob_radius

        knob_y = self.height // 2

        # Draw knob (circle)
        self.create_oval(
            knob_x - self.knob_radius,
            knob_y - self.knob_radius,
            knob_x + self.knob_radius,
            knob_y + self.knob_radius,
            fill=self.knob_color,
            outline="",
            tags="knob",
        )

        # Draw label text
        if self._is_on:
            text_x = self.knob_padding + self.knob_radius
        else:
            text_x = self.width - self.knob_padding - self.knob_radius

        self.create_text(
            text_x,
            self.height // 2,
            text=label,
            fill="white",
            font=("Consolas", 8, "bold"),
            tags="label",
        )

    def _draw_rounded_rect(
        self, x1: int, y1: int, x2: int, y2: int, radius: int, color: str
    ) -> None:
        """Draw a rounded rectangle."""
        # Create rounded rectangle using polygon with arcs
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        self.create_polygon(points, fill=color, smooth=True, outline="", tags="bg")

    def _on_click(self, event: tk.Event) -> None:
        """Handle click - toggle state and call command."""
        self.toggle()
        if self.command:
            self.command()

    def _on_enter(self, event: tk.Event) -> None:
        """Handle mouse enter - show hover effect."""
        self.config(cursor="hand2")

    def _on_leave(self, event: tk.Event) -> None:
        """Handle mouse leave."""
        pass


class RecordingToggle(tk.Frame):
    """
    Recording toggle with status label.

    Combines ToggleSwitch with a status display.
    """

    def __init__(
        self,
        parent: tk.Widget,
        command: Callable[[], bool] | None = None,
        bg: str = "#1a1a1a",
    ):
        """
        Initialize recording toggle.

        Args:
            parent: Parent widget
            command: Callback that returns new recording state
            bg: Background color
        """
        super().__init__(parent, bg=bg)

        self.command = command
        self._status_update_timer: str | None = None

        # Status label (left side)
        self.status_label = tk.Label(
            self,
            text="",
            font=("Consolas", 8),
            bg=bg,
            fg="#888888",
        )
        self.status_label.pack(side=tk.LEFT, padx=(0, 5))

        # Toggle switch (right side)
        self.switch = ToggleSwitch(
            self,
            width=55,
            height=24,
            on_color="#cc0000",
            off_color="#444444",
            label_on="REC",
            label_off="OFF",
            command=self._on_toggle,
            initial_state=False,
        )
        self.switch.pack(side=tk.LEFT)

    @property
    def is_recording(self) -> bool:
        """Get current recording state."""
        return self.switch.is_on

    def _on_toggle(self) -> None:
        """Handle toggle - call command and update display."""
        if self.command:
            # Command returns the actual recording state
            actual_state = self.command()
            # Sync switch state with actual state
            if actual_state != self.switch.is_on:
                self.switch.set_state(actual_state)

    def update_status(self, event_count: int = 0, game_id: str | None = None) -> None:
        """Update the status label."""
        if event_count > 0:
            if game_id:
                short_id = game_id.split("-")[-1][:8] if "-" in game_id else game_id[:8]
                text = f"{event_count} | {short_id}"
            else:
                text = f"{event_count} evts"
            self.status_label.config(text=text, fg="#FF6B6B")
        else:
            self.status_label.config(text="", fg="#888888")

    def set_state(self, is_recording: bool) -> None:
        """Set recording state (for external sync)."""
        self.switch.set_state(is_recording)
        if not is_recording:
            self.status_label.config(text="", fg="#888888")
