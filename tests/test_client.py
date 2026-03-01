"""Tests for the ScribusClient subprocess manager."""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from scribus_mcp.client import SCRIBUS_PATHS, ScribusClient, find_scribus_executable


class TestFindScribusExecutable:
    def test_uses_env_var(self, tmp_path):
        fake_bin = tmp_path / "scribus"
        fake_bin.touch()
        with patch.dict("os.environ", {"SCRIBUS_EXECUTABLE": str(fake_bin)}):
            assert find_scribus_executable() == str(fake_bin)

    def test_raises_when_not_found(self):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("os.path.isfile", return_value=False),
            pytest.raises(FileNotFoundError),
        ):
            find_scribus_executable()

    def test_env_var_nonexistent_file(self):
        with (
            patch.dict("os.environ", {"SCRIBUS_EXECUTABLE": "/no/such/binary"}),
            patch("os.path.isfile", return_value=False),
            pytest.raises(FileNotFoundError),
        ):
            find_scribus_executable()

    def test_finds_from_known_paths(self):
        def fake_isfile(path):
            return path == SCRIBUS_PATHS[0]

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("os.path.isfile", side_effect=fake_isfile),
        ):
            assert find_scribus_executable() == SCRIBUS_PATHS[0]


class TestScribusClient:
    def _make_mock_process(self, responses=None):
        """Create a mock subprocess that responds with given JSON responses."""
        process = MagicMock()
        process.poll.return_value = None  # process is alive
        process.stdin = MagicMock()
        process.stderr = MagicMock()
        process.stderr.__iter__ = MagicMock(return_value=iter([]))

        # Build stdout lines: ready sentinel + responses
        lines = [json.dumps({"ready": True}).encode() + b"\n"]
        for resp in responses or []:
            lines.append(json.dumps(resp).encode() + b"\n")

        line_iter = iter(lines)
        process.stdout = MagicMock()
        process.stdout.readline = lambda: next(line_iter, b"")

        return process

    @patch("scribus_mcp.client.find_scribus_executable")
    @patch("subprocess.Popen")
    def test_send_command_success(self, mock_popen, mock_find):
        mock_find.return_value = "/usr/bin/scribus"
        expected_result = {"width": 210, "height": 297}
        process = self._make_mock_process([{"ok": True, "result": expected_result}])
        mock_popen.return_value = process

        client = ScribusClient()
        result = client.send_command("create_document", {"width": 210})

        assert result == expected_result
        # Verify the command was written to stdin
        process.stdin.write.assert_called_once()
        written = process.stdin.write.call_args[0][0]
        msg = json.loads(written)
        assert msg["command"] == "create_document"
        assert msg["params"]["width"] == 210

    @patch("scribus_mcp.client.find_scribus_executable")
    @patch("subprocess.Popen")
    def test_send_command_error(self, mock_popen, mock_find):
        mock_find.return_value = "/usr/bin/scribus"
        process = self._make_mock_process([{"ok": False, "error": "No document open"}])
        mock_popen.return_value = process

        client = ScribusClient()
        with pytest.raises(RuntimeError, match="No document open"):
            client.send_command("get_document_info")

    @patch("scribus_mcp.client.find_scribus_executable")
    @patch("subprocess.Popen")
    def test_auto_restart_on_dead_process(self, mock_popen, mock_find):
        mock_find.return_value = "/usr/bin/scribus"

        result1 = {"ok": True, "result": {"pages": 1}}
        result2 = {"ok": True, "result": {"pages": 1}}

        process1 = self._make_mock_process([result1])
        process2 = self._make_mock_process([result2])

        mock_popen.side_effect = [process1, process2]

        client = ScribusClient()
        # First call starts the process
        client.send_command("get_document_info")
        assert mock_popen.call_count == 1

        # Simulate process death
        process1.poll.return_value = 1  # exited with code 1

        # Next call should restart
        client.send_command("get_document_info")
        assert mock_popen.call_count == 2

    @patch("scribus_mcp.client.find_scribus_executable")
    @patch("subprocess.Popen")
    def test_broken_pipe_raises_connection_error(self, mock_popen, mock_find):
        mock_find.return_value = "/usr/bin/scribus"
        process = self._make_mock_process()
        process.stdin.write.side_effect = BrokenPipeError("broken")
        mock_popen.return_value = process

        client = ScribusClient()
        with pytest.raises(ConnectionError):
            client.send_command("create_document")

    @patch("scribus_mcp.client.find_scribus_executable")
    @patch("subprocess.Popen")
    def test_shutdown(self, mock_popen, mock_find):
        mock_find.return_value = "/usr/bin/scribus"
        process = self._make_mock_process()
        process.wait.return_value = 0
        mock_popen.return_value = process

        client = ScribusClient()
        # Force process start
        client._ensure_running()

        client.shutdown()
        process.stdin.write.assert_called()
        process.wait.assert_called()

    @patch("scribus_mcp.client.find_scribus_executable")
    @patch("subprocess.Popen")
    def test_empty_stdout_raises_connection_error(self, mock_popen, mock_find):
        mock_find.return_value = "/usr/bin/scribus"
        process = self._make_mock_process([{"ok": True, "result": {}}])
        # Override readline to return empty (EOF) on the command response
        call_count = [0]
        ready_line = json.dumps({"ready": True}).encode() + b"\n"

        def fake_readline():
            call_count[0] += 1
            if call_count[0] == 1:
                return ready_line
            return b""

        process.stdout.readline = fake_readline
        mock_popen.return_value = process

        client = ScribusClient()
        with pytest.raises(ConnectionError, match="closed stdout"):
            client.send_command("get_document_info")

    @patch("scribus_mcp.client.find_scribus_executable")
    @patch("subprocess.Popen")
    def test_invalid_json_response_raises(self, mock_popen, mock_find):
        mock_find.return_value = "/usr/bin/scribus"
        process = self._make_mock_process()
        call_count = [0]
        ready_line = json.dumps({"ready": True}).encode() + b"\n"

        def fake_readline():
            call_count[0] += 1
            if call_count[0] == 1:
                return ready_line
            return b"NOT JSON\n"

        process.stdout.readline = fake_readline
        mock_popen.return_value = process

        client = ScribusClient()
        with pytest.raises(RuntimeError, match="Invalid JSON response"):
            client.send_command("create_document")

    @patch("scribus_mcp.client.find_scribus_executable")
    @patch("subprocess.Popen")
    def test_default_params_empty_dict(self, mock_popen, mock_find):
        mock_find.return_value = "/usr/bin/scribus"
        process = self._make_mock_process([{"ok": True, "result": {"info": True}}])
        mock_popen.return_value = process

        client = ScribusClient()
        client.send_command("get_document_info")
        written = process.stdin.write.call_args[0][0]
        msg = json.loads(written)
        assert msg["params"] == {}

    @patch("scribus_mcp.client.find_scribus_executable")
    @patch("subprocess.Popen")
    def test_wait_for_ready_skips_non_json(self, mock_popen, mock_find):
        mock_find.return_value = "/usr/bin/scribus"
        process = MagicMock()
        process.poll.return_value = None
        process.stdin = MagicMock()
        process.stderr = MagicMock()
        process.stderr.__iter__ = MagicMock(return_value=iter([]))

        # Junk lines before the ready sentinel
        lines = [
            b"Scribus starting up...\n",
            b"Loading plugins...\n",
            b"\n",  # blank line
            json.dumps({"ready": True}).encode() + b"\n",
            json.dumps({"ok": True, "result": {}}).encode() + b"\n",
        ]
        line_iter = iter(lines)
        process.stdout = MagicMock()
        process.stdout.readline = lambda: next(line_iter, b"")
        mock_popen.return_value = process

        client = ScribusClient()
        result = client.send_command("get_document_info")
        assert result == {}

    def test_shutdown_noop_when_not_running(self):
        client = ScribusClient()
        # No process started — should not raise
        client.shutdown()

    @patch("scribus_mcp.client.find_scribus_executable")
    @patch("subprocess.Popen")
    def test_shutdown_kills_on_timeout(self, mock_popen, mock_find):
        mock_find.return_value = "/usr/bin/scribus"
        process = self._make_mock_process()
        process.wait.side_effect = subprocess.TimeoutExpired(cmd="scribus", timeout=10)
        process.kill.return_value = None

        # After kill, wait should succeed
        def wait_after_kill(timeout=None):
            if process.kill.called:
                return 0
            raise subprocess.TimeoutExpired(cmd="scribus", timeout=10)

        process.wait.side_effect = wait_after_kill
        mock_popen.return_value = process

        client = ScribusClient()
        client._ensure_running()
        client.shutdown()
        process.kill.assert_called_once()
