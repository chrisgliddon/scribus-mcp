"""Manages Scribus as a persistent headless subprocess.

Launches Scribus with -g (headless) -ns (no splash) -py bridge.py,
communicates via NDJSON over stdin/stdout.
"""

import json
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

SCRIBUS_PATHS = [
    "/Applications/Scribus.app/Contents/MacOS/Scribus",
    "/usr/bin/scribus",
    "/usr/local/bin/scribus",
    "/snap/bin/scribus",
]

BRIDGE_SCRIPT = Path(__file__).parent / "bridge.py"
WORKSPACE_DIR = Path.home() / ".scribus-mcp" / "workspace"
DOCUMENT_PATH = WORKSPACE_DIR / "document.sla"


def find_scribus_executable() -> str:
    """Find the Scribus executable path."""
    # Check environment variable first
    env_path = os.environ.get("SCRIBUS_EXECUTABLE")
    if env_path and os.path.isfile(env_path):
        return env_path

    # Check known paths
    for path in SCRIBUS_PATHS:
        if os.path.isfile(path):
            return path

    raise FileNotFoundError(
        "Scribus executable not found. Set SCRIBUS_EXECUTABLE environment variable "
        "or install Scribus to a standard location."
    )


class ScribusClient:
    """Manages a persistent Scribus subprocess and communicates via NDJSON."""

    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._stderr_thread: threading.Thread | None = None

        # Ensure workspace directory exists
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    def _start_scribus(self) -> None:
        """Launch the Scribus subprocess and wait for the ready sentinel."""
        scribus_path = find_scribus_executable()

        logger.info("Starting Scribus: %s -g -ns -py %s", scribus_path, BRIDGE_SCRIPT)

        self._process = subprocess.Popen(
            [scribus_path, "-g", "-ns", "-py", str(BRIDGE_SCRIPT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(WORKSPACE_DIR),
        )

        # Start stderr reader thread to prevent buffer blocking
        self._stderr_thread = threading.Thread(
            target=self._read_stderr,
            daemon=True,
        )
        self._stderr_thread.start()

        # Wait for ready sentinel, discarding any non-JSON startup output
        self._wait_for_ready()

    def _read_stderr(self) -> None:
        """Read stderr in background to prevent buffer blocking."""
        try:
            assert self._process is not None
            assert self._process.stderr is not None
            for line in self._process.stderr:
                if isinstance(line, bytes):
                    line = line.decode("utf-8", errors="replace")
                logger.debug("Scribus stderr: %s", line.rstrip())
        except Exception:
            pass

    def _wait_for_ready(self) -> None:
        """Read lines from stdout until we get the ready sentinel."""
        assert self._process is not None
        assert self._process.stdout is not None

        while True:
            line = self._process.stdout.readline()
            if not line:
                raise ConnectionError(
                    "Scribus process exited before sending ready sentinel"
                )

            if isinstance(line, bytes):
                line = line.decode("utf-8", errors="replace")

            line = line.strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
                if msg.get("ready"):
                    logger.info("Scribus bridge is ready")
                    return
            except json.JSONDecodeError:
                # Discard non-JSON startup output
                logger.debug("Scribus startup output: %s", line)
                continue

    def _ensure_running(self) -> None:
        """Check if Scribus is running, restart if dead."""
        if self._process is None or self._process.poll() is not None:
            logger.warning("Scribus process not running, (re)starting...")
            self._start_scribus()

    def send_command(self, command: str, params: dict | None = None) -> dict:
        """Send a command to the Scribus bridge and return the result.

        Args:
            command: The command name (e.g. "create_document")
            params: Command parameters dict

        Returns:
            The result dict from the bridge

        Raises:
            RuntimeError: If the command fails
            ConnectionError: If communication with Scribus fails
        """
        with self._lock:
            self._ensure_running()

            assert self._process is not None
            assert self._process.stdin is not None
            assert self._process.stdout is not None

            msg = json.dumps({"command": command, "params": params or {}}) + "\n"

            try:
                self._process.stdin.write(msg.encode("utf-8"))
                self._process.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                self._process = None
                raise ConnectionError(f"Failed to send command to Scribus: {e}") from e

            # Read response
            try:
                response_line = self._process.stdout.readline()
            except OSError as e:
                self._process = None
                raise ConnectionError(
                    f"Failed to read response from Scribus: {e}"
                ) from e

            if not response_line:
                self._process = None
                raise ConnectionError(
                    "Scribus process closed stdout (likely crashed)"
                )

            if isinstance(response_line, bytes):
                response_line = response_line.decode("utf-8", errors="replace")

            try:
                response = json.loads(response_line.strip())
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"Invalid JSON response from Scribus: {response_line!r}"
                ) from e

            if not response.get("ok"):
                error_msg = response.get("error", "Unknown error")
                raise RuntimeError(f"Scribus error: {error_msg}")

            return response.get("result", {})

    def save_document(self) -> None:
        """Save the current document to the workspace."""
        self.send_command("save_document", {"file_path": str(DOCUMENT_PATH)})

    def shutdown(self) -> None:
        """Gracefully shut down the Scribus subprocess."""
        with self._lock:
            if self._process is None or self._process.poll() is not None:
                return

            try:
                msg = json.dumps({"command": "shutdown", "params": {}}) + "\n"
                assert self._process.stdin is not None
                self._process.stdin.write(msg.encode("utf-8"))
                self._process.stdin.flush()
                self._process.wait(timeout=10)
                logger.info("Scribus shut down gracefully")
            except Exception:
                logger.warning("Graceful shutdown failed, killing Scribus")
                self._process.kill()
                self._process.wait(timeout=5)
            finally:
                self._process = None
