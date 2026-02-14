"""
Chrome Tab Opener Service - Opens recording dashboard in existing Chrome browser.

Uses Chrome DevTools Protocol (CDP) to open a new tab in the same Chrome
instance that the main VECTRA-PLAYER UI uses. This keeps everything in
one browser window for easier workflow.

Usage:
    from recording_ui.services.chrome_tab import open_dashboard_tab
    await open_dashboard_tab("http://localhost:5000")
"""

import asyncio
import json
import logging
import socket
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# Default CDP port (same as main UI)
CDP_PORT = 9222


def is_chrome_running(port: int = CDP_PORT) -> bool:
    """Check if Chrome is running with CDP on the given port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(("localhost", port))
            return True
    except (TimeoutError, ConnectionRefusedError, OSError):
        return False


def get_chrome_tabs(port: int = CDP_PORT) -> list[dict]:
    """Get list of open tabs from Chrome CDP."""
    try:
        req = Request(f"http://localhost:{port}/json/list")
        with urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except (URLError, json.JSONDecodeError) as e:
        logger.error(f"Failed to get Chrome tabs: {e}")
        return []


def open_tab_sync(url: str, port: int = CDP_PORT) -> dict | None:
    """
    Open a new tab in Chrome via CDP (synchronous).

    Args:
        url: URL to open in new tab
        port: CDP port (default 9222)

    Returns:
        Tab info dict or None on failure
    """
    if not is_chrome_running(port):
        logger.error(f"Chrome not running on CDP port {port}")
        return None

    try:
        # Check if tab already exists with this URL
        tabs = get_chrome_tabs(port)
        for tab in tabs:
            if url in tab.get("url", ""):
                logger.info(f"Dashboard tab already open: {tab['url']}")
                # Activate existing tab
                activate_url = f"http://localhost:{port}/json/activate/{tab['id']}"
                try:
                    urlopen(Request(activate_url), timeout=5)
                except Exception:
                    pass
                return tab

        # Open new tab using PUT method
        # Chrome CDP /json/new endpoint requires PUT with URL in body
        from urllib.parse import quote

        new_tab_url = f"http://localhost:{port}/json/new?{quote(url, safe='')}"

        req = Request(new_tab_url, method="PUT")
        with urlopen(req, timeout=10) as response:
            tab_info = json.loads(response.read().decode())
            logger.info(f"Opened new Chrome tab: {tab_info.get('url', url)}")
            return tab_info

    except URLError as e:
        # Fallback: Try GET method (some Chrome versions accept it)
        try:
            from urllib.parse import quote

            new_tab_url = f"http://localhost:{port}/json/new?{quote(url, safe='')}"
            req = Request(new_tab_url)
            with urlopen(req, timeout=10) as response:
                tab_info = json.loads(response.read().decode())
                logger.info(f"Opened new Chrome tab (GET fallback): {tab_info.get('url', url)}")
                return tab_info
        except Exception as e2:
            logger.error(f"Failed to open Chrome tab: {e} / {e2}")
            return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Chrome response: {e}")
        return None


async def open_tab_async(url: str, port: int = CDP_PORT) -> dict | None:
    """
    Open a new tab in Chrome via CDP (async wrapper).

    Args:
        url: URL to open in new tab
        port: CDP port (default 9222)

    Returns:
        Tab info dict or None on failure
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, open_tab_sync, url, port)


def close_tab_sync(tab_id: str, port: int = CDP_PORT) -> bool:
    """
    Close a Chrome tab by ID.

    Args:
        tab_id: Tab ID from CDP
        port: CDP port

    Returns:
        True if closed successfully
    """
    try:
        close_url = f"http://localhost:{port}/json/close/{tab_id}"
        req = Request(close_url)
        urlopen(req, timeout=5)
        logger.info(f"Closed Chrome tab: {tab_id}")
        return True
    except URLError as e:
        logger.error(f"Failed to close tab: {e}")
        return False


def open_dashboard_tab(url: str = "http://localhost:5000", port: int = CDP_PORT) -> dict | None:
    """
    Convenience function to open the recording dashboard in Chrome.

    Args:
        url: Dashboard URL (default http://localhost:5000)
        port: CDP port (default 9222)

    Returns:
        Tab info dict or None on failure
    """
    return open_tab_sync(url, port)


# For use as standalone script
if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"

    if is_chrome_running():
        print(f"Chrome running on port {CDP_PORT}")
        result = open_dashboard_tab(url)
        if result:
            print(f"Opened tab: {result.get('url', url)}")
        else:
            print("Failed to open tab")
    else:
        print(f"Chrome not running on port {CDP_PORT}")
        print("Start the main UI first with ./run.sh")
        sys.exit(1)
