"""Tests for unified bot launcher functionality.

TDD approach: These tests define the expected behavior of the bot launcher
helper functions before implementation.
"""

import socket
from unittest.mock import MagicMock, patch


class TestCheckFlaskRunning:
    """Tests for check_flask_running function."""

    def test_returns_false_when_port_not_listening(self):
        """Should return False when nothing is listening on the port."""
        from scripts.bot_launcher import check_flask_running

        # Use a port that's definitely not in use
        result = check_flask_running(port=59999)
        assert result is False

    def test_returns_true_when_port_is_listening(self):
        """Should return True when something is listening on the port."""
        from scripts.bot_launcher import check_flask_running

        # Create a temporary server to listen on a port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", 59998))
            s.listen(1)

            result = check_flask_running(port=59998)
            assert result is True


class TestCheckChromeCdp:
    """Tests for check_chrome_cdp function."""

    def test_returns_false_when_cdp_not_available(self):
        """Should return False when CDP endpoint is not responding."""
        from scripts.bot_launcher import check_chrome_cdp

        # Use a port that's definitely not running CDP
        result = check_chrome_cdp(port=59997)
        assert result is False

    @patch("scripts.bot_launcher.requests.get")
    def test_returns_true_when_cdp_responds(self, mock_get):
        """Should return True when CDP endpoint responds with valid JSON."""
        from scripts.bot_launcher import check_chrome_cdp

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Browser": "Chrome/120.0.0.0"}
        mock_get.return_value = mock_response

        result = check_chrome_cdp(port=9222)
        assert result is True
        mock_get.assert_called_once_with("http://localhost:9222/json/version", timeout=2)


class TestStartFlask:
    """Tests for start_flask function."""

    @patch("scripts.bot_launcher.subprocess.Popen")
    def test_starts_flask_subprocess(self, mock_popen):
        """Should start Flask as a background subprocess."""
        from scripts.bot_launcher import start_flask

        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        pid = start_flask(port=5005)

        assert pid == 12345
        # Verify Popen was called with correct arguments
        call_args = mock_popen.call_args
        assert "-m" in call_args[0][0]
        assert "recording_ui.app" in call_args[0][0]


class TestStartChrome:
    """Tests for start_chrome function."""

    @patch("scripts.bot_launcher.subprocess.Popen")
    def test_starts_chrome_with_correct_flags(self, mock_popen):
        """Should launch Chrome with rugs_bot profile and CDP port."""
        from scripts.bot_launcher import start_chrome

        mock_process = MagicMock()
        mock_process.pid = 54321
        mock_popen.return_value = mock_process

        pid = start_chrome()

        assert pid == 54321
        call_args = mock_popen.call_args[0][0]
        # Should include CDP port flag
        assert any("--remote-debugging-port=9222" in arg for arg in call_args)
        # Should include user data dir with rugs_bot
        assert any("rugs_bot" in arg for arg in call_args)


class TestKillProcess:
    """Tests for kill_process function."""

    @patch("scripts.bot_launcher.os.kill")
    def test_kills_process_by_pid(self, mock_kill):
        """Should send SIGTERM to process."""
        import signal

        from scripts.bot_launcher import kill_process

        kill_process(12345)

        mock_kill.assert_called_once_with(12345, signal.SIGTERM)


class TestFindProcessOnPort:
    """Tests for find_process_on_port function."""

    @patch("scripts.bot_launcher.subprocess.run")
    def test_returns_pid_when_process_found(self, mock_run):
        """Should return PID of process listening on port."""
        from scripts.bot_launcher import find_process_on_port

        # lsof output includes a header line that gets skipped
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="COMMAND     PID   USER   FD   TYPE  DEVICE SIZE/OFF NODE NAME\npython  12345 user    3u  IPv4 12345      0t0  TCP *:5005 (LISTEN)\n",
        )

        pid = find_process_on_port(5005)
        assert pid == 12345

    @patch("scripts.bot_launcher.subprocess.run")
    def test_returns_none_when_no_process(self, mock_run):
        """Should return None when no process on port."""
        from scripts.bot_launcher import find_process_on_port

        mock_run.return_value = MagicMock(returncode=1, stdout="")

        pid = find_process_on_port(5005)
        assert pid is None
