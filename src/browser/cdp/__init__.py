"""
Chrome DevTools Protocol (CDP) Module

CDP-specific browser connection and control.
"""

from browser.cdp.launcher import BrowserStatus, RugsBrowserManager

__all__ = [
    "BrowserStatus",
    "RugsBrowserManager",
]
