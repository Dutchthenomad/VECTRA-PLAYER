"""Foundation Service configuration."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FoundationConfig:
    """
    Configuration for the Foundation Service.

    All settings can be overridden via environment variables.
    """

    # WebSocket Broadcaster
    host: str = field(default_factory=lambda: os.getenv("FOUNDATION_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("FOUNDATION_PORT", "9000")))

    # HTTP Server
    http_port: int = field(default_factory=lambda: int(os.getenv("FOUNDATION_HTTP_PORT", "9001")))

    # Chrome/CDP
    chrome_profile: str = field(default_factory=lambda: os.getenv("CHROME_PROFILE", "rugs_bot"))
    chrome_profile_base: Path = field(
        default_factory=lambda: Path(
            os.getenv("CHROME_PROFILE_PATH", "~/.gamebot/chrome_profiles")
        ).expanduser()
    )
    cdp_port: int = field(default_factory=lambda: int(os.getenv("CDP_PORT", "9222")))
    headless: bool = field(
        default_factory=lambda: os.getenv("FOUNDATION_HEADLESS", "false").lower() == "true"
    )

    # Authentication
    auth_timeout_ms: int = field(
        default_factory=lambda: int(os.getenv("FOUNDATION_AUTH_TIMEOUT_MS", "2000"))
    )

    # rugs.fun connection
    rugs_url: str = field(default_factory=lambda: os.getenv("RUGS_URL", "https://rugs.fun"))

    @property
    def chrome_profile_path(self) -> Path:
        """Full path to Chrome profile directory."""
        return self.chrome_profile_base / self.chrome_profile

    @property
    def ws_url(self) -> str:
        """WebSocket broadcaster URL."""
        return f"ws://{self.host}:{self.port}/feed"

    @property
    def monitor_url(self) -> str:
        """Monitoring UI URL."""
        return f"http://{self.host}:{self.port}/monitor"
