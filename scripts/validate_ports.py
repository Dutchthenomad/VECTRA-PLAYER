#!/usr/bin/env python3
"""
Port Allocation Validator

Validates that all VECTRA service ports are available before starting.
Run this BEFORE starting any services to detect conflicts early.

Usage:
    python scripts/validate_ports.py
    python scripts/validate_ports.py --fix  # Kill conflicting processes
"""

import argparse
import socket
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class PortAssignment:
    """A port assignment from PORT-ALLOCATION-SPEC."""

    port: int
    service: str
    protocol: str
    required: bool = True


# Official port allocations from PORT-ALLOCATION-SPEC.md
PORT_ALLOCATIONS = [
    PortAssignment(9000, "Foundation WebSocket", "WS", required=True),
    PortAssignment(9001, "Foundation HTTP", "HTTP", required=True),
    PortAssignment(9010, "Recording Service", "HTTP", required=False),
    PortAssignment(9222, "Chrome CDP", "CDP", required=False),
]


def check_port_available(port: int) -> bool:
    """Check if a port is available for binding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.bind(("localhost", port))
            return True
        except OSError:
            return False


def get_port_user(port: int) -> str | None:
    """Get the process using a port (Linux only)."""
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"], capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            processes = []
            for pid in pids:
                try:
                    ps_result = subprocess.run(
                        ["ps", "-p", pid, "-o", "comm="], capture_output=True, text=True, timeout=5
                    )
                    if ps_result.stdout.strip():
                        processes.append(f"{ps_result.stdout.strip()} (PID {pid})")
                except Exception:
                    processes.append(f"PID {pid}")
            return ", ".join(processes)
    except Exception:
        pass
    return None


def kill_port_user(port: int) -> bool:
    """Kill the process using a port."""
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"], capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                try:
                    subprocess.run(["kill", pid], timeout=5)
                    print(f"  Killed PID {pid}")
                except Exception:
                    pass
            return True
    except Exception:
        pass
    return False


def validate_ports(fix: bool = False) -> bool:
    """
    Validate all port allocations.

    Args:
        fix: If True, attempt to kill conflicting processes

    Returns:
        True if all ports are available, False otherwise
    """
    print("=" * 60)
    print("VECTRA Port Allocation Validator")
    print("=" * 60)
    print()

    all_ok = True

    for assignment in PORT_ALLOCATIONS:
        available = check_port_available(assignment.port)

        if available:
            status = "✅ Available"
            color = "\033[92m"  # Green
        else:
            user = get_port_user(assignment.port)
            status = f"❌ IN USE by {user or 'unknown'}"
            color = "\033[91m"  # Red

            if assignment.required:
                all_ok = False

            if fix and not available:
                print(f"  Attempting to free port {assignment.port}...")
                if kill_port_user(assignment.port):
                    # Re-check
                    import time

                    time.sleep(1)
                    if check_port_available(assignment.port):
                        status = "✅ Freed"
                        color = "\033[93m"  # Yellow
                        all_ok = True

        reset = "\033[0m"
        req = "(REQUIRED)" if assignment.required else "(optional)"
        print(f"{color}Port {assignment.port}: {status}{reset}")
        print(f"  Service: {assignment.service} [{assignment.protocol}] {req}")
        print()

    print("=" * 60)

    if all_ok:
        print("\033[92m✅ All required ports are available!\033[0m")
        print("You can start VECTRA services.")
    else:
        print("\033[91m❌ Port conflicts detected!\033[0m")
        print()
        print("To identify the conflicting process:")
        print("  lsof -i :PORT_NUMBER")
        print()
        print("To kill it (if safe):")
        print("  kill $(lsof -i :PORT_NUMBER -t)")
        print()
        print("Or run this script with --fix:")
        print("  python scripts/validate_ports.py --fix")

    print("=" * 60)

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Validate VECTRA port allocations")
    parser.add_argument(
        "--fix", action="store_true", help="Attempt to kill processes using reserved ports"
    )
    args = parser.parse_args()

    success = validate_ports(fix=args.fix)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
