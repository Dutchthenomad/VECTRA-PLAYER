#!/usr/bin/env python3
"""Bot launcher helper functions for unified startup.

This module provides functions to check and start Flask, Chrome, and
the Control Window for bot execution testing.

Usage:
    from scripts.bot_launcher import main
    main()

Or from shell:
    ./scripts/start_bot.sh
"""

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests


def check_flask_running(port: int = 5005) -> bool:
    """Check if Flask (or any process) is listening on the specified port.

    Args:
        port: Port number to check (default: 5005)

    Returns:
        True if something is listening on the port, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
            return result == 0
    except OSError:
        return False


def check_chrome_cdp(port: int = 9222) -> bool:
    """Check if Chrome CDP endpoint is available.

    Args:
        port: CDP port to check (default: 9222)

    Returns:
        True if CDP endpoint responds with valid JSON, False otherwise
    """
    try:
        response = requests.get(f"http://localhost:{port}/json/version", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return "Browser" in data or "webSocketDebuggerUrl" in data
        return False
    except (requests.RequestException, ValueError):
        return False


def start_flask(port: int = 5005) -> int:
    """Start Flask dashboard as a background subprocess.

    Args:
        port: Port for Flask to listen on (default: 5005)

    Returns:
        PID of the started process
    """
    project_root = Path(__file__).parent.parent.parent
    venv_python = project_root / ".venv" / "bin" / "python"

    if not venv_python.exists():
        venv_python = Path(sys.executable)

    cmd = [
        str(venv_python),
        "-m",
        "recording_ui.app",
        "--port",
        str(port),
    ]

    # Start Flask in background, redirect output to log file
    log_file = Path("/tmp/flask_bot.log")
    with open(log_file, "w") as log:
        process = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=str(project_root / "src"),
            start_new_session=True,  # Detach from parent
        )

    return process.pid


def start_chrome(port: int = 9222) -> int:
    """Start Chrome with rugs_bot profile and CDP enabled.

    Args:
        port: CDP port for Chrome (default: 9222)

    Returns:
        PID of the started process
    """
    profile_dir = Path.home() / ".gamebot" / "chrome_profiles" / "rugs_bot"
    profile_dir.mkdir(parents=True, exist_ok=True)

    # Find Chrome binary
    chrome_binaries = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    ]

    chrome_bin = None
    for binary in chrome_binaries:
        if Path(binary).exists():
            chrome_bin = binary
            break

    if not chrome_bin:
        raise FileNotFoundError("Chrome/Chromium not found")

    cmd = [
        chrome_bin,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "https://rugs.fun",
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    return process.pid


def kill_process(pid: int) -> None:
    """Kill a process by PID.

    Args:
        pid: Process ID to kill
    """
    os.kill(pid, signal.SIGTERM)


def find_process_on_port(port: int) -> int | None:
    """Find the PID of a process listening on a port.

    Args:
        port: Port number to check

    Returns:
        PID of the process, or None if no process found
    """
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None

        # Parse lsof output to extract PID
        for line in result.stdout.strip().split("\n")[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 2:
                try:
                    return int(parts[1])
                except ValueError:
                    continue
        return None
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


def start_control_window() -> None:
    """Start the Tkinter Control Window."""
    project_root = Path(__file__).parent.parent.parent
    venv_python = project_root / ".venv" / "bin" / "python"

    if not venv_python.exists():
        venv_python = Path(sys.executable)

    script_path = project_root / "src" / "scripts" / "alpha_test_bot_execution.py"

    subprocess.run(
        [str(venv_python), str(script_path)],
        cwd=str(project_root / "src"),
    )


def main() -> None:
    """Main entry point for unified bot launcher.

    Checks and starts Flask, Chrome, and Control Window as needed.
    """
    print("=" * 50)
    print("VECTRA Bot Launcher")
    print("=" * 50)

    # Check/start Flask
    if check_flask_running(5005):
        print("✓ Flask already running on port 5005")
    else:
        print("Starting Flask dashboard...")
        pid = start_flask(5005)
        print(f"  Flask started (PID: {pid})")
        time.sleep(2)  # Wait for Flask to initialize

        if check_flask_running(5005):
            print("✓ Flask is ready")
        else:
            print("✗ Flask failed to start. Check /tmp/flask_bot.log")
            return

    # Check/start Chrome
    if check_chrome_cdp(9222):
        print("✓ Chrome CDP already available on port 9222")
    else:
        print("Starting Chrome with rugs_bot profile...")
        try:
            pid = start_chrome(9222)
            print(f"  Chrome started (PID: {pid})")
            time.sleep(3)  # Wait for Chrome to initialize

            if check_chrome_cdp(9222):
                print("✓ Chrome CDP is ready")
            else:
                print("⚠ Chrome started but CDP not responding yet")
                print("  (This is OK - it may take a few seconds)")
        except FileNotFoundError as e:
            print(f"✗ {e}")
            return

    print()
    print("Starting Control Window...")
    print("(Close the window to exit, Flask/Chrome will keep running)")
    print()

    # Start Control Window (blocking)
    start_control_window()

    print()
    print("Control Window closed.")
    print("Flask and Chrome are still running.")
    print("Run ./scripts/stop_bot.sh to stop everything.")


if __name__ == "__main__":
    main()
