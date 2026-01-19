"""
Tests for validate-artifact.py - Enforces boilerplate compliance.

TDD: Tests written BEFORE implementation.
"""


# =============================================================================
# PHASE 1: Path Validation Tests
# =============================================================================


class TestPathValidation:
    """Test artifact location validation."""

    def test_valid_tool_path_passes(self, tmp_path):
        """Artifacts in src/artifacts/tools/ pass validation."""
        from scripts.validate_artifact import validate_artifact_path

        # Create valid tool structure
        tool_dir = tmp_path / "src" / "artifacts" / "tools" / "my-tool"
        tool_dir.mkdir(parents=True)

        result = validate_artifact_path(tool_dir, tmp_path)

        assert result.valid is True

    def test_valid_template_path_passes(self, tmp_path):
        """Artifacts in src/artifacts/templates/ pass validation."""
        from scripts.validate_artifact import validate_artifact_path

        # Create valid template structure
        template_dir = tmp_path / "src" / "artifacts" / "templates"
        template_dir.mkdir(parents=True)

        result = validate_artifact_path(template_dir, tmp_path)

        assert result.valid is True

    def test_invalid_path_fails(self, tmp_path):
        """Artifacts outside allowed directories fail."""
        from scripts.validate_artifact import validate_artifact_path

        # Create invalid location
        invalid_dir = tmp_path / "src" / "rugs_recordings" / "PRNG CRAK"
        invalid_dir.mkdir(parents=True)

        result = validate_artifact_path(invalid_dir, tmp_path)

        assert result.valid is False
        assert "must be in" in result.error.lower()

    def test_shared_directory_rejected(self, tmp_path):
        """Artifacts cannot be added to src/artifacts/shared/."""
        from scripts.validate_artifact import validate_artifact_path

        # Shared is IMMUTABLE
        shared_dir = tmp_path / "src" / "artifacts" / "shared"
        shared_dir.mkdir(parents=True)

        result = validate_artifact_path(shared_dir, tmp_path)

        assert result.valid is False
        assert "immutable" in result.error.lower()


# =============================================================================
# PHASE 2: HTML Import Validation Tests
# =============================================================================


class TestHTMLImportValidation:
    """Test that HTML files import required shared resources."""

    def test_html_with_ws_client_import_passes(self, tmp_path):
        """HTML importing foundation-ws-client.js passes."""
        from scripts.validate_artifact import validate_html_imports

        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="../../shared/vectra-styles.css">
            <script src="../../shared/foundation-ws-client.js"></script>
        </head>
        <body></body>
        </html>
        """

        html_file = tmp_path / "index.html"
        html_file.write_text(html_content)

        result = validate_html_imports(html_file)

        assert result.valid is True

    def test_html_missing_ws_client_fails(self, tmp_path):
        """HTML missing foundation-ws-client.js import fails."""
        from scripts.validate_artifact import validate_html_imports

        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="../../shared/vectra-styles.css">
            <!-- Missing WebSocket client import -->
        </head>
        <body></body>
        </html>
        """

        html_file = tmp_path / "index.html"
        html_file.write_text(html_content)

        result = validate_html_imports(html_file)

        assert result.valid is False
        assert "foundation-ws-client.js" in result.error

    def test_html_missing_styles_fails(self, tmp_path):
        """HTML missing vectra-styles.css import fails."""
        from scripts.validate_artifact import validate_html_imports

        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="../../shared/foundation-ws-client.js"></script>
            <!-- Missing styles import -->
        </head>
        <body></body>
        </html>
        """

        html_file = tmp_path / "index.html"
        html_file.write_text(html_content)

        result = validate_html_imports(html_file)

        assert result.valid is False
        assert "vectra-styles.css" in result.error

    def test_html_with_custom_websocket_fails(self, tmp_path):
        """HTML with custom WebSocket code fails."""
        from scripts.validate_artifact import validate_html_imports

        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="../../shared/vectra-styles.css">
            <script src="../../shared/foundation-ws-client.js"></script>
        </head>
        <body>
            <script>
                // Custom WebSocket - NOT ALLOWED
                const ws = new WebSocket('ws://localhost:9000/feed');
            </script>
        </body>
        </html>
        """

        html_file = tmp_path / "index.html"
        html_file.write_text(html_content)

        result = validate_html_imports(html_file)

        assert result.valid is False
        assert "custom websocket" in result.error.lower()


# =============================================================================
# PHASE 3: Python Subscriber Validation Tests
# =============================================================================


class TestPythonSubscriberValidation:
    """Test that Python subscribers inherit BaseSubscriber."""

    def test_valid_subscriber_passes(self, tmp_path):
        """Python file inheriting BaseSubscriber passes."""
        from scripts.validate_artifact import validate_python_subscriber

        py_content = """
from foundation.subscriber import BaseSubscriber
from foundation.events import GameTickEvent, PlayerStateEvent

class MySubscriber(BaseSubscriber):
    def on_game_tick(self, event: GameTickEvent):
        pass

    def on_player_state(self, event: PlayerStateEvent):
        pass

    def on_connection_change(self, connected: bool):
        pass
"""

        py_file = tmp_path / "subscriber.py"
        py_file.write_text(py_content)

        result = validate_python_subscriber(py_file)

        assert result.valid is True

    def test_subscriber_not_inheriting_base_fails(self, tmp_path):
        """Python subscriber not inheriting BaseSubscriber fails."""
        from scripts.validate_artifact import validate_python_subscriber

        py_content = """
# Missing BaseSubscriber inheritance
class MySubscriber:
    def on_game_tick(self, event):
        pass
"""

        py_file = tmp_path / "subscriber.py"
        py_file.write_text(py_content)

        result = validate_python_subscriber(py_file)

        assert result.valid is False
        assert "BaseSubscriber" in result.error

    def test_subscriber_with_direct_websocket_fails(self, tmp_path):
        """Python subscriber with direct WebSocket connection fails."""
        from scripts.validate_artifact import validate_python_subscriber

        py_content = """
import websockets
from foundation.subscriber import BaseSubscriber

class MySubscriber(BaseSubscriber):
    async def connect_directly(self):
        # Direct connection NOT ALLOWED
        ws = await websockets.connect('ws://localhost:9000/feed')

    def on_game_tick(self, event):
        pass

    def on_player_state(self, event):
        pass

    def on_connection_change(self, connected):
        pass
"""

        py_file = tmp_path / "subscriber.py"
        py_file.write_text(py_content)

        result = validate_python_subscriber(py_file)

        assert result.valid is False
        assert "direct" in result.error.lower() or "websocket" in result.error.lower()


# =============================================================================
# PHASE 4: Full Artifact Validation Tests
# =============================================================================


class TestFullArtifactValidation:
    """Test complete artifact validation."""

    def test_validate_tool_directory(self, tmp_path):
        """Validate complete tool directory."""
        from scripts.validate_artifact import validate_artifact

        # Create valid tool structure
        src_dir = tmp_path / "src"
        tool_dir = src_dir / "artifacts" / "tools" / "my-tool"
        tool_dir.mkdir(parents=True)

        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="../../shared/vectra-styles.css">
            <script src="../../shared/foundation-ws-client.js"></script>
        </head>
        <body></body>
        </html>
        """
        (tool_dir / "index.html").write_text(html_content)
        (tool_dir / "main.js").write_text("// JS code")
        (tool_dir / "README.md").write_text("# My Tool")

        result = validate_artifact(tool_dir, tmp_path)

        assert result.valid is True

    def test_validate_tool_missing_readme(self, tmp_path):
        """Tool without README.md fails validation."""
        from scripts.validate_artifact import validate_artifact

        # Create tool without README
        src_dir = tmp_path / "src"
        tool_dir = src_dir / "artifacts" / "tools" / "my-tool"
        tool_dir.mkdir(parents=True)

        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="../../shared/vectra-styles.css">
            <script src="../../shared/foundation-ws-client.js"></script>
        </head>
        <body></body>
        </html>
        """
        (tool_dir / "index.html").write_text(html_content)

        result = validate_artifact(tool_dir, tmp_path)

        assert result.valid is False
        assert "readme" in result.error.lower()


# =============================================================================
# PHASE 5: ValidationResult Tests
# =============================================================================


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_valid_result_has_no_error(self):
        """Valid result has empty error."""
        from scripts.validate_artifact import ValidationResult

        result = ValidationResult(valid=True)

        assert result.valid is True
        assert result.error == ""

    def test_invalid_result_has_error(self):
        """Invalid result has error message."""
        from scripts.validate_artifact import ValidationResult

        result = ValidationResult(valid=False, error="Something went wrong")

        assert result.valid is False
        assert result.error == "Something went wrong"

    def test_validation_result_to_dict(self):
        """ValidationResult can serialize to dict."""
        from scripts.validate_artifact import ValidationResult

        result = ValidationResult(valid=True, warnings=["Minor issue"])

        d = result.to_dict()

        assert d["valid"] is True
        assert d["warnings"] == ["Minor issue"]
