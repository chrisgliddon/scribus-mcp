"""Tests for the ScribusClient subprocess manager."""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from scribus_mcp.client import ScribusClient, find_scribus_executable


class TestFindScribusExecutable:
    def test_uses_env_var(self, tmp_path):
        fake_bin = tmp_path / "scribus"
        fake_bin.touch()
        with patch.dict("os.environ", {"SCRIBUS_EXECUTABLE": str(fake_bin)}):
            assert find_scribus_executable() == str(fake_bin)

    def test_raises_when_not_found(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("os.path.isfile", return_value=False):
                with pytest.raises(FileNotFoundError):
                    find_scribus_executable()


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
        for resp in (responses or []):
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
        process = self._make_mock_process([
            {"ok": False, "error": "No document open"}
        ])
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
