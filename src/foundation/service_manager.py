"""
Service Manager - Subprocess management for VECTRA services.

Scans services/*/manifest.json, validates against PORT-ALLOCATION-SPEC,
spawns/kills subprocesses, and tracks service state.
"""

import asyncio
import json
import logging
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """Service state machine states."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServiceInfo:
    """Information about a registered service."""

    name: str
    version: str
    description: str
    port: int
    health_endpoint: str
    start_command: str
    working_dir: str
    requires_foundation: bool
    events_consumed: list[str]
    events_emitted: list[str]
    dependencies: list[str]

    # Runtime state
    state: ServiceState = ServiceState.STOPPED
    pid: int | None = None
    process: subprocess.Popen | None = None
    start_time: float | None = None
    error_message: str | None = None
    health_failures: int = 0

    # Manifest path for reference
    manifest_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "port": self.port,
            "health_endpoint": self.health_endpoint,
            "start_command": self.start_command,
            "working_dir": self.working_dir,
            "requires_foundation": self.requires_foundation,
            "events_consumed": self.events_consumed,
            "events_emitted": self.events_emitted,
            "dependencies": self.dependencies,
            "status": self.state.value,
            "pid": self.pid,
            "error_message": self.error_message,
        }

        if self.start_time:
            result["uptime_seconds"] = round(time.time() - self.start_time, 1)

        return result


@dataclass
class PortAllocation:
    """Port allocation from PORT-ALLOCATION-SPEC."""

    port: int
    service: str
    protocol: str
    purpose: str


class ServiceManager:
    """
    Manages VECTRA service lifecycle.

    Responsibilities:
    - Discover services from services/*/manifest.json
    - Validate manifests against PORT-ALLOCATION-SPEC
    - Start/stop services as subprocesses
    - Monitor health via HTTP endpoints
    - Expose state for REST API
    """

    HEALTH_CHECK_INTERVAL = 5.0  # seconds
    HEALTH_CHECK_TIMEOUT = 3.0  # seconds
    MAX_HEALTH_FAILURES = 3
    STARTUP_GRACE_PERIOD = 10.0  # seconds before health checks start

    def __init__(self, project_root: Path | None = None):
        """
        Initialize Service Manager.

        Args:
            project_root: Project root directory (auto-detected if None)
        """
        if project_root is None:
            # Detect project root from this file's location
            project_root = Path(__file__).parent.parent.parent

        self.project_root = project_root
        self.services_dir = project_root / "services"
        self.port_spec_path = project_root / "docs" / "specs" / "PORT-ALLOCATION-SPEC.md"

        self.services: dict[str, ServiceInfo] = {}
        self.allocated_ports: dict[int, PortAllocation] = {}

        self._health_check_task: asyncio.Task | None = None
        self._running = False

        logger.info(f"ServiceManager initialized (root={project_root})")

    def discover_services(self) -> list[str]:
        """
        Discover and validate services from services/*/manifest.json.

        Returns:
            List of successfully registered service names
        """
        # First, parse port allocations
        self._parse_port_allocations()

        registered = []
        errors = []

        if not self.services_dir.exists():
            logger.warning(f"Services directory not found: {self.services_dir}")
            return registered

        for service_dir in self.services_dir.iterdir():
            if not service_dir.is_dir():
                continue

            manifest_path = service_dir / "manifest.json"
            if not manifest_path.exists():
                logger.warning(f"No manifest.json in {service_dir.name}")
                continue

            try:
                service = self._load_manifest(manifest_path)
                self._validate_service(service)
                self.services[service.name] = service
                registered.append(service.name)
                logger.info(f"Registered service: {service.name} (port {service.port})")
            except Exception as e:
                errors.append((service_dir.name, str(e)))
                logger.error(f"Failed to register {service_dir.name}: {e}")

        if errors:
            logger.warning(f"{len(errors)} services failed validation")

        return registered

    def _parse_port_allocations(self) -> None:
        """Parse PORT-ALLOCATION-SPEC.md to get valid port allocations."""
        if not self.port_spec_path.exists():
            logger.warning(f"Port spec not found: {self.port_spec_path}")
            return

        content = self.port_spec_path.read_text()

        # Parse table rows with format: | **PORT** | Service | Protocol | Purpose |
        # Match both **9000** and 9000 formats
        pattern = r"\|\s*\*?\*?(\d{4})\*?\*?\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|"

        for match in re.finditer(pattern, content):
            port = int(match.group(1))
            service = match.group(2).strip()
            protocol = match.group(3).strip()
            purpose = match.group(4).strip()

            self.allocated_ports[port] = PortAllocation(
                port=port,
                service=service,
                protocol=protocol,
                purpose=purpose,
            )

        logger.info(f"Parsed {len(self.allocated_ports)} port allocations")

    def _load_manifest(self, manifest_path: Path) -> ServiceInfo:
        """Load and parse manifest.json."""
        with open(manifest_path) as f:
            data = json.load(f)

        # Extract required fields
        required_fields = [
            "name",
            "version",
            "description",
            "port",
            "health_endpoint",
            "start_command",
            "working_dir",
            "requires_foundation",
            "events_consumed",
            "events_emitted",
            "dependencies",
        ]

        # Handle legacy manifests by providing defaults for new fields
        if "start_command" not in data:
            # Check for docker config
            if "docker" in data:
                data["start_command"] = "docker-compose up"
            else:
                data["start_command"] = "python -m src.main"

        if "working_dir" not in data:
            data["working_dir"] = f"services/{data.get('name', manifest_path.parent.name)}"

        if "requires_foundation" not in data:
            data["requires_foundation"] = True

        if "events_emitted" not in data:
            data["events_emitted"] = []

        if "dependencies" not in data:
            data["dependencies"] = []

        # Get port from docker config if not at top level
        if "port" not in data and "docker" in data:
            data["port"] = data["docker"].get("port")

        if "health_endpoint" not in data and "docker" in data:
            data["health_endpoint"] = data["docker"].get("health_endpoint", "/health")

        # Validate all required fields present
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        service = ServiceInfo(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            port=data["port"],
            health_endpoint=data["health_endpoint"],
            start_command=data["start_command"],
            working_dir=data["working_dir"],
            requires_foundation=data["requires_foundation"],
            events_consumed=data["events_consumed"],
            events_emitted=data["events_emitted"],
            dependencies=data["dependencies"],
            manifest_path=manifest_path,
        )

        return service

    def _validate_service(self, service: ServiceInfo) -> None:
        """Validate service against PORT-ALLOCATION-SPEC."""
        # Check port is allocated
        if service.port not in self.allocated_ports:
            raise ValueError(
                f"Port {service.port} not allocated in PORT-ALLOCATION-SPEC.md. "
                "Add port to spec before registering service."
            )

        # Check working_dir exists
        working_path = self.project_root / service.working_dir
        if not working_path.exists():
            raise ValueError(f"Working directory not found: {service.working_dir}")

    def get_service(self, name: str) -> ServiceInfo | None:
        """Get service by name."""
        return self.services.get(name)

    def list_services(self) -> list[dict[str, Any]]:
        """List all services with their current state."""
        return [svc.to_dict() for svc in self.services.values()]

    async def start_service(self, name: str) -> dict[str, Any]:
        """
        Start a service by name.

        Args:
            name: Service name

        Returns:
            Result dict with success status
        """
        service = self.services.get(name)
        if not service:
            return {"success": False, "error": f"Service not found: {name}"}

        if service.state == ServiceState.RUNNING:
            return {"success": True, "service": name, "status": "already_running"}

        if service.state == ServiceState.STARTING:
            return {"success": True, "service": name, "status": "starting"}

        # Check dependencies
        for dep_name in service.dependencies:
            dep = self.services.get(dep_name)
            if not dep or dep.state != ServiceState.RUNNING:
                return {
                    "success": False,
                    "error": f"Dependency not running: {dep_name}",
                }

        try:
            service.state = ServiceState.STARTING
            service.error_message = None
            service.health_failures = 0

            # Build command
            working_path = self.project_root / service.working_dir
            cmd = service.start_command.split()

            # Set environment
            env = os.environ.copy()
            env["PORT"] = str(service.port)
            env["PYTHONPATH"] = str(self.project_root / "src")

            logger.info(f"Starting {name}: {cmd} in {working_path}")

            # Start subprocess
            process = subprocess.Popen(
                cmd,
                cwd=working_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # Separate process group
            )

            service.process = process
            service.pid = process.pid
            service.start_time = time.time()

            logger.info(f"Started {name} with PID {process.pid}")

            return {"success": True, "service": name, "status": "starting", "pid": process.pid}

        except Exception as e:
            logger.error(f"Failed to start {name}: {e}")
            service.state = ServiceState.ERROR
            service.error_message = str(e)
            return {"success": False, "error": str(e)}

    async def stop_service(self, name: str) -> dict[str, Any]:
        """
        Stop a service by name.

        Args:
            name: Service name

        Returns:
            Result dict with success status
        """
        service = self.services.get(name)
        if not service:
            return {"success": False, "error": f"Service not found: {name}"}

        if service.state == ServiceState.STOPPED:
            return {"success": True, "service": name, "status": "already_stopped"}

        if service.state == ServiceState.STOPPING:
            return {"success": True, "service": name, "status": "stopping"}

        try:
            service.state = ServiceState.STOPPING

            if service.process:
                logger.info(f"Stopping {name} (PID {service.pid})")

                # Send SIGTERM
                try:
                    os.killpg(os.getpgid(service.process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass  # Already dead

                # Wait briefly for graceful shutdown
                try:
                    service.process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    # Force kill
                    logger.warning(f"Force killing {name}")
                    try:
                        os.killpg(os.getpgid(service.process.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass

            service.state = ServiceState.STOPPED
            service.process = None
            service.pid = None
            service.start_time = None

            logger.info(f"Stopped {name}")
            return {"success": True, "service": name, "status": "stopped"}

        except Exception as e:
            logger.error(f"Failed to stop {name}: {e}")
            service.error_message = str(e)
            return {"success": False, "error": str(e)}

    async def stop_all(self) -> None:
        """Stop all running services."""
        for name, service in self.services.items():
            if service.state in (ServiceState.RUNNING, ServiceState.STARTING):
                await self.stop_service(name)

    async def check_service_health(self, service: ServiceInfo) -> bool:
        """
        Check if service is healthy via HTTP endpoint.

        Args:
            service: Service to check

        Returns:
            True if healthy
        """
        if not service.pid:
            return False

        url = f"http://localhost:{service.port}{service.health_endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=self.HEALTH_CHECK_TIMEOUT)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("status") == "healthy"
        except Exception:
            pass

        return False

    async def _health_check_loop(self) -> None:
        """Background task for health checking all services."""
        while self._running:
            for name, service in self.services.items():
                if service.state == ServiceState.STARTING:
                    # Check if still within grace period
                    if service.start_time:
                        elapsed = time.time() - service.start_time
                        if elapsed < self.STARTUP_GRACE_PERIOD:
                            continue

                    # Check health
                    healthy = await self.check_service_health(service)
                    if healthy:
                        service.state = ServiceState.RUNNING
                        service.health_failures = 0
                        logger.info(f"Service {name} is now running")
                    else:
                        service.health_failures += 1
                        if service.health_failures >= self.MAX_HEALTH_FAILURES:
                            service.state = ServiceState.ERROR
                            service.error_message = "Health check failed after startup"
                            logger.error(f"Service {name} failed to start (health check)")

                elif service.state == ServiceState.RUNNING:
                    # Periodic health check
                    healthy = await self.check_service_health(service)
                    if not healthy:
                        service.health_failures += 1
                        if service.health_failures >= self.MAX_HEALTH_FAILURES:
                            service.state = ServiceState.ERROR
                            service.error_message = "Health check failed"
                            logger.error(f"Service {name} is unhealthy")
                    else:
                        service.health_failures = 0

                    # Also check if process is still running
                    if service.process and service.process.poll() is not None:
                        service.state = ServiceState.ERROR
                        service.error_message = (
                            f"Process exited with code {service.process.returncode}"
                        )
                        logger.error(f"Service {name} process exited unexpectedly")

            await asyncio.sleep(self.HEALTH_CHECK_INTERVAL)

    async def start(self) -> None:
        """Start the service manager (health check loop)."""
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("ServiceManager health check loop started")

    async def stop(self) -> None:
        """Stop the service manager."""
        self._running = False

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Stop all services
        await self.stop_all()
        logger.info("ServiceManager stopped")
