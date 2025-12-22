"""
Theme management for MainWindow.
"""

import json
import logging
import os
import sys
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class ThemeManagerMixin:
    """Mixin providing theme management functionality for MainWindow."""

    def _change_theme(self: "MainWindow", theme_name: str):
        """Switch UI theme and save preference."""
        try:
            import ttkbootstrap as ttk

            if hasattr(self.root, "style"):
                style = self.root.style
            else:
                style = ttk.Style()

            style.theme_use(theme_name)

            if hasattr(self, "chart"):
                self.chart.update_theme_colors()

            self._save_theme_preference(theme_name)
            logger.info(f"Theme changed to: {theme_name}")

            if hasattr(self, "toast_notification"):
                self.toast_notification.show(
                    f"Theme changed to: {theme_name.title()}", duration=2000
                )
        except Exception as e:
            logger.error(f"Failed to change theme to {theme_name}: {e}")
            messagebox.showerror("Theme Error", f"Failed to change theme:\n{e!s}")

    def _save_theme_preference(self: "MainWindow", theme_name: str):
        """Save theme preference to config file"""
        try:
            config_dir = Path.home() / ".config" / "replayer"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "ui_config.json"

            config_data = {}
            if config_file.exists():
                with open(config_file) as f:
                    config_data = json.load(f)

            config_data["theme"] = theme_name

            with open(config_file, "w") as f:
                json.dump(config_data, f, indent=2)

            logger.debug(f"Saved theme preference: {theme_name}")
        except Exception as e:
            logger.error(f"Failed to save theme preference: {e}")

    @staticmethod
    def load_theme_preference() -> str:
        """Load saved theme preference, default to 'cyborg'"""
        try:
            config_file = Path.home() / ".config" / "replayer" / "ui_config.json"

            if config_file.exists():
                with open(config_file) as f:
                    config_data = json.load(f)
                    theme = config_data.get("theme", "cyborg")
                    logger.debug(f"Loaded theme preference: {theme}")
                    return theme
        except Exception as e:
            logger.debug(f"Could not load theme preference: {e}")

        return "cyborg"

    @staticmethod
    def load_ui_style_preference() -> str:
        """Load saved UI style preference, default to 'standard'"""
        try:
            config_file = Path.home() / ".config" / "replayer" / "ui_config.json"

            if config_file.exists():
                with open(config_file) as f:
                    config_data = json.load(f)
                    style = config_data.get("ui_style", "standard")
                    logger.debug(f"Loaded UI style preference: {style}")
                    return style
        except Exception as e:
            logger.debug(f"Could not load UI style preference: {e}")

        return "standard"

    def _set_ui_style(self: "MainWindow", style: str):
        """Set UI style and auto-restart the application"""
        try:
            config_dir = Path.home() / ".config" / "replayer"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "ui_config.json"

            config_data = {}
            if config_file.exists():
                with open(config_file) as f:
                    config_data = json.load(f)

            config_data["ui_style"] = style

            with open(config_file, "w") as f:
                json.dump(config_data, f, indent=2)

            logger.info(f"Saved UI style preference: {style}")

            result = messagebox.askyesno(
                "Restart Application",
                f"UI style changed to '{style}'.\n\nRestart now to apply changes?",
            )

            if result:
                self._restart_application()

        except Exception as e:
            logger.error(f"Failed to save UI style preference: {e}")
            messagebox.showerror("Error", f"Failed to save UI style: {e}")

    def _restart_application(self: "MainWindow"):
        """Restart the application"""
        logger.info("Restarting application...")

        python = sys.executable
        script = os.path.abspath(sys.argv[0])
        script_dir = os.path.dirname(script)

        args = [python, script] + sys.argv[1:]
        args = [a for a in args if a != "--modern"]

        logger.info(f"Restart command: {' '.join(args)}")
        logger.info(f"Working directory: {script_dir}")

        self.root.after(100, lambda: self._do_restart(python, args, script_dir))

    def _do_restart(self: "MainWindow", python, args, working_dir):
        """Execute the restart"""
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

        os.chdir(working_dir)
        os.execv(python, args)

    def _show_about(self: "MainWindow"):
        """Show about dialog with application information"""
        about_text = """
REPLAYER - Rugs.fun Game Replay & Analysis System
Version: 2.0 (Phase 7B - Menu Bar)

A professional replay viewer and empirical analysis engine for
Rugs.fun trading game recordings.

Features:
* Interactive replay with speed control
* Trading bot automation (Conservative, Aggressive, Sidebet)
* Real-time WebSocket live feed integration
* Multi-game session support
* Position & P&L tracking
* Empirical analysis for RL training

Architecture:
* Event-driven modular design
* Thread-safe state management
* 141 test suite coverage
* Symlinked ML predictor integration

Part of the Rugs.fun quantitative trading ecosystem:
* CV-BOILER-PLATE-FORK: YOLOv8 live detection
* rugs-rl-bot: Reinforcement learning trading bot
* REPLAYER: Replay viewer & analysis engine

Keyboard Shortcuts: Press 'H' for help

(c) 2025 REPLAYER Project
"""
        messagebox.showinfo("About REPLAYER", about_text)
