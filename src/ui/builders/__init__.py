"""
UI Builders Package

Contains builder classes for UI construction, extracted from MainWindow.
Each builder handles construction of a specific UI section.

Pattern:
    builder = SomeBuilder(parent, **dependencies)
    widgets = builder.build()  # Returns dict of widget references
"""

from .action_builder import ActionBuilder
from .betting_builder import BettingBuilder
from .chart_builder import ChartBuilder
from .menu_bar_builder import MenuBarBuilder
from .playback_builder import PlaybackBuilder
from .status_bar_builder import StatusBarBuilder

__all__ = [
    "ActionBuilder",
    "BettingBuilder",
    "ChartBuilder",
    "MenuBarBuilder",
    "PlaybackBuilder",
    "StatusBarBuilder",
]
