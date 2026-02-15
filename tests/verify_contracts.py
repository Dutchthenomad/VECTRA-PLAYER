"""
Contract verification tests for VECTRA service manifests.

Validates:
1. Every service has a manifest.json with required fields
2. Upstream/downstream port references are consistent
3. Layer dependency rules (no upward dependencies)
4. Port uniqueness across all services
5. Port ranges match layer allocation
"""

import json
import re
from pathlib import Path

import pytest

SERVICES_DIR = Path(__file__).parent.parent / "services"

REQUIRED_MANIFEST_FIELDS = [
    "name",
    "version",
    "layer",
    "port",
    "health",
    "events_consumed",
    "events_produced",
]

VALID_LAYERS = ["L0", "L1", "L2", "L3", "L4"]

# Layer ordering for dependency checks (lower index = lower layer)
LAYER_ORDER = {layer: idx for idx, layer in enumerate(VALID_LAYERS)}

# Port allocation ranges per layer
PORT_RANGES = {
    "L0": (9000, 9009),
    "L1": (9010, 9019),
    "L2": (9020, 9029),
    "L3": (9030, 9039),
    "L4": (3000, 3099),
}


def discover_services() -> list[Path]:
    """Find all service directories that contain a manifest.json."""
    return sorted(
        d for d in SERVICES_DIR.iterdir() if d.is_dir() and (d / "manifest.json").exists()
    )


def load_manifest(service_dir: Path) -> dict:
    """Load and parse a service manifest."""
    manifest_path = service_dir / "manifest.json"
    return json.loads(manifest_path.read_text())


def load_all_manifests() -> dict[str, dict]:
    """Load all service manifests into a name->manifest dict."""
    manifests = {}
    for svc_dir in discover_services():
        manifest = load_manifest(svc_dir)
        manifests[manifest["name"]] = manifest
    return manifests


# ── Fixture ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def all_manifests() -> dict[str, dict]:
    return load_all_manifests()


@pytest.fixture(scope="module")
def service_dirs() -> list[Path]:
    return discover_services()


# ── Test: Manifest Schema ────────────────────────────────────────────────


class TestManifestSchema:
    """Every service manifest has required fields with correct types."""

    def test_services_dir_exists(self):
        assert SERVICES_DIR.exists(), f"Services directory not found: {SERVICES_DIR}"

    def test_at_least_one_service(self, service_dirs):
        assert len(service_dirs) >= 1, "No services found with manifest.json"

    @pytest.mark.parametrize("service_dir", discover_services(), ids=lambda d: d.name)
    def test_manifest_has_required_fields(self, service_dir):
        manifest = load_manifest(service_dir)
        missing = [f for f in REQUIRED_MANIFEST_FIELDS if f not in manifest]
        assert not missing, f"{service_dir.name}/manifest.json missing fields: {missing}"

    @pytest.mark.parametrize("service_dir", discover_services(), ids=lambda d: d.name)
    def test_manifest_valid_layer(self, service_dir):
        manifest = load_manifest(service_dir)
        assert manifest["layer"] in VALID_LAYERS, (
            f"{manifest['name']}: invalid layer '{manifest['layer']}' (valid: {VALID_LAYERS})"
        )

    @pytest.mark.parametrize("service_dir", discover_services(), ids=lambda d: d.name)
    def test_manifest_port_is_integer(self, service_dir):
        manifest = load_manifest(service_dir)
        assert isinstance(manifest["port"], int), (
            f"{manifest['name']}: port must be integer, got {type(manifest['port'])}"
        )

    @pytest.mark.parametrize("service_dir", discover_services(), ids=lambda d: d.name)
    def test_manifest_version_is_semver(self, service_dir):
        manifest = load_manifest(service_dir)
        assert re.match(r"^\d+\.\d+\.\d+", manifest["version"]), (
            f"{manifest['name']}: version '{manifest['version']}' is not semver"
        )

    @pytest.mark.parametrize("service_dir", discover_services(), ids=lambda d: d.name)
    def test_manifest_events_are_lists(self, service_dir):
        manifest = load_manifest(service_dir)
        assert isinstance(manifest["events_consumed"], list), (
            f"{manifest['name']}: events_consumed must be a list"
        )
        assert isinstance(manifest["events_produced"], list), (
            f"{manifest['name']}: events_produced must be a list"
        )

    @pytest.mark.parametrize("service_dir", discover_services(), ids=lambda d: d.name)
    def test_manifest_name_matches_directory(self, service_dir):
        manifest = load_manifest(service_dir)
        assert manifest["name"] == service_dir.name, (
            f"Manifest name '{manifest['name']}' doesn't match directory name '{service_dir.name}'"
        )


# ── Test: Port Allocation ────────────────────────────────────────────────


class TestPortAllocation:
    """No port collisions and ports are within allocated ranges."""

    def test_no_duplicate_ports(self, all_manifests):
        ports = {}
        for name, manifest in all_manifests.items():
            port = manifest["port"]
            if port in ports:
                pytest.fail(f"Port collision: {name} and {ports[port]} both use port {port}")
            ports[port] = name

    @pytest.mark.parametrize("service_dir", discover_services(), ids=lambda d: d.name)
    def test_port_within_layer_range(self, service_dir):
        manifest = load_manifest(service_dir)
        layer = manifest["layer"]
        port = manifest["port"]
        lo, hi = PORT_RANGES[layer]
        assert lo <= port <= hi, (
            f"{manifest['name']}: port {port} outside {layer} range [{lo}-{hi}]"
        )


# ── Test: Layer Dependencies ─────────────────────────────────────────────


class TestLayerDependencies:
    """Services only depend on same-layer or lower-layer upstreams."""

    def _extract_port_from_upstream(self, upstream: str) -> int | None:
        """Extract port number from upstream URL."""
        match = re.search(r":(\d+)", upstream)
        return int(match.group(1)) if match else None

    @pytest.mark.parametrize("service_dir", discover_services(), ids=lambda d: d.name)
    def test_upstream_not_higher_layer(self, service_dir, all_manifests):
        manifest = load_manifest(service_dir)
        upstream = manifest.get("upstream")
        if not upstream:
            return  # No upstream = source service, OK

        consumer_layer = LAYER_ORDER[manifest["layer"]]
        upstream_port = self._extract_port_from_upstream(upstream)
        if upstream_port is None:
            return  # Can't determine port, skip

        # Find upstream service by port
        for up_name, up_manifest in all_manifests.items():
            if up_manifest["port"] == upstream_port:
                producer_layer = LAYER_ORDER[up_manifest["layer"]]
                assert consumer_layer >= producer_layer, (
                    f"{manifest['name']} (layer {manifest['layer']}) "
                    f"depends on {up_name} (layer {up_manifest['layer']}) "
                    f"— upward dependency violates layer rules"
                )
                return

    @pytest.mark.parametrize("service_dir", discover_services(), ids=lambda d: d.name)
    def test_events_consumed_match_upstream_produced(self, service_dir, all_manifests):
        """Warn if consumed events aren't produced by any known service."""
        manifest = load_manifest(service_dir)
        consumed = set(manifest["events_consumed"])
        if not consumed:
            return

        all_produced = set()
        for m in all_manifests.values():
            all_produced.update(m["events_produced"])

        orphaned = consumed - all_produced
        if orphaned:
            pytest.skip(
                f"{manifest['name']} consumes events not produced by "
                f"any registered service: {orphaned} "
                f"(may come from L0/Foundation)"
            )


# ── Test: Upstream Consistency ───────────────────────────────────────────


class TestUpstreamConsistency:
    """Upstream references point to valid, existing services."""

    @pytest.mark.parametrize("service_dir", discover_services(), ids=lambda d: d.name)
    def test_upstream_port_exists(self, service_dir, all_manifests):
        manifest = load_manifest(service_dir)
        upstream = manifest.get("upstream")
        if not upstream:
            return

        match = re.search(r":(\d+)", upstream)
        if not match:
            return

        upstream_port = int(match.group(1))
        known_ports = {m["port"] for m in all_manifests.values()}

        # Port 9000 is Foundation (L0) — not in manifests but valid
        known_ports.add(9000)

        assert upstream_port in known_ports, (
            f"{manifest['name']}: upstream port {upstream_port} "
            f"not found in any service manifest "
            f"(known: {sorted(known_ports)})"
        )

    @pytest.mark.parametrize("service_dir", discover_services(), ids=lambda d: d.name)
    def test_upstream_url_format(self, service_dir):
        manifest = load_manifest(service_dir)
        upstream = manifest.get("upstream")
        if not upstream:
            return

        assert re.match(r"^wss?://", upstream), (
            f"{manifest['name']}: upstream '{upstream}' must start with ws:// or wss://"
        )


# ── Test: Health Endpoints ───────────────────────────────────────────────


class TestHealthEndpoints:
    """Every service declares a health endpoint."""

    @pytest.mark.parametrize("service_dir", discover_services(), ids=lambda d: d.name)
    def test_health_endpoint_defined(self, service_dir):
        manifest = load_manifest(service_dir)
        assert manifest.get("health"), f"{manifest['name']}: must declare a health endpoint"

    @pytest.mark.parametrize("service_dir", discover_services(), ids=lambda d: d.name)
    def test_health_endpoint_starts_with_slash(self, service_dir):
        manifest = load_manifest(service_dir)
        health = manifest.get("health")
        if health:
            assert health.startswith("/"), (
                f"{manifest['name']}: health endpoint '{health}' must start with /"
            )
