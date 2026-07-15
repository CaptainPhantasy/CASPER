"""
PTY (Pseudoterminal) Manager for CASPER Terminal Infrastructure.
Handles creation, management, and communication with pseudoterminals.
"""

import asyncio
import os
import pty
import select
import subprocess
import termios
import tty
from typing import Dict, Optional, Callable, Any, List
from uuid import uuid4, UUID
import logging
from pathlib import Path
import signal
import fcntl
import struct

logger = logging.getLogger(__name__)


class PTYSession:
    """Represents a single PTY session with a shell process."""

    def __init__(
        self, session_id: str, master_fd: int, slave_fd: int, process: subprocess.Popen
    ):
        self.session_id = session_id
        self.master_fd = master_fd
        self.slave_fd = slave_fd
        self.process = process
        self.is_active = True
        self.last_activity = asyncio.get_event_loop().time()
        self.output_callback: Optional[Callable[[str], None]] = None

    def set_output_callback(self, callback: Callable[[str], None]):
        """Set callback for handling terminal output."""
        self.output_callback = callback

    def write(self, data: str):
        """Write data to the terminal."""
        if self.is_active:
            try:
                os.write(self.master_fd, data.encode("utf-8"))
                self.last_activity = asyncio.get_event_loop().time()
            except OSError as e:
                logger.error(f"Failed to write to PTY {self.session_id}: {e}")
                self.is_active = False

    def read(self) -> Optional[str]:
        """Read available data from the terminal."""
        if not self.is_active:
            return None

        try:
            # Check if data is available to read
            ready, _, _ = select.select([self.master_fd], [], [], 0)
            if ready:
                data = os.read(self.master_fd, 1024)
                if data:
                    self.last_activity = asyncio.get_event_loop().time()
                    return data.decode("utf-8", errors="ignore")
        except OSError as e:
            logger.error(f"Failed to read from PTY {self.session_id}: {e}")
            self.is_active = False

        return None

    def resize(self, rows: int, cols: int):
        """Resize the terminal."""
        if self.is_active:
            try:
                # Set the window size
                fcntl.ioctl(
                    self.master_fd,
                    termios.TIOCSWINSZ,
                    struct.pack("HHHH", rows, cols, 0, 0),
                )
            except OSError as e:
                logger.error(f"Failed to resize PTY {self.session_id}: {e}")

    def close(self):
        """Close the PTY session."""
        if self.is_active:
            self.is_active = False
            try:
                # Terminate the process gracefully
                self.process.terminate()
                try:
                    # Wait for graceful termination with very short timeout for performance
                    self.process.wait(timeout=0.05)
                except subprocess.TimeoutExpired:
                    # Force kill immediately for better performance
                    self.process.kill()
                    try:
                        self.process.wait(timeout=0.05)
                    except subprocess.TimeoutExpired:
                        pass  # Process is stuck, move on
            except Exception as e:
                logger.error(
                    f"Error terminating process for PTY {self.session_id}: {e}"
                )

            try:
                os.close(self.master_fd)
            except OSError:
                pass

            try:
                os.close(self.slave_fd)
            except OSError:
                pass


class PTYManager:
    """Manages multiple PTY sessions for terminal functionality."""

    def __init__(self, shell_command: str = None):
        self.sessions: Dict[str, PTYSession] = {}
        self.shell_command = shell_command or os.environ.get("SHELL", "/bin/bash")
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the PTY manager and cleanup task."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_inactive_sessions())
        logger.info("PTY Manager started")

    async def stop(self):
        """Stop the PTY manager and cleanup all sessions."""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all active sessions
        for session in list(self.sessions.values()):
            await self.close_session(session.session_id)

        logger.info("PTY Manager stopped")

    async def create_session(
        self, working_dir: str = None, env: Dict[str, str] = None
    ) -> str:
        """Create a new PTY session and return the session ID."""
        session_id = str(uuid4())

        try:
            # Create the PTY
            master_fd, slave_fd = pty.openpty()

            # Set up environment
            session_env = os.environ.copy()
            if env:
                session_env.update(env)

            # Set terminal environment variables
            session_env["TERM"] = "xterm-256color"
            session_env["COLUMNS"] = "80"
            session_env["LINES"] = "24"

            # Start the shell process
            process = subprocess.Popen(
                self.shell_command,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=session_env,
                cwd=working_dir or str(Path.cwd()),
                preexec_fn=os.setsid,  # Create new process group
                close_fds=True,
            )

            # Create session object
            session = PTYSession(session_id, master_fd, slave_fd, process)
            self.sessions[session_id] = session

            # Start reading output in background
            asyncio.create_task(self._read_session_output(session))

            logger.info(f"Created PTY session {session_id}")
            return session_id

        except Exception as e:
            logger.error(f"Failed to create PTY session: {e}")
            raise

    async def close_session(self, session_id: str) -> bool:
        """Close a PTY session."""
        session = self.sessions.get(session_id)
        if not session:
            return False

        session.close()
        del self.sessions[session_id]
        logger.info(f"Closed PTY session {session_id}")
        return True

    async def write_to_session(self, session_id: str, data: str) -> bool:
        """Write data to a PTY session."""
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return False

        session.write(data)
        return True

    async def resize_session(self, session_id: str, rows: int, cols: int) -> bool:
        """Resize a PTY session."""
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return False

        session.resize(rows, cols)
        return True

    def set_output_callback(
        self, session_id: str, callback: Callable[[str], None]
    ) -> bool:
        """Set output callback for a session."""
        session = self.sessions.get(session_id)
        if not session:
            return False

        session.set_output_callback(callback)
        return True

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session."""
        session = self.sessions.get(session_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "is_active": session.is_active,
            "last_activity": session.last_activity,
            "process_pid": session.process.pid if session.process else None,
        }

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions."""
        return [self.get_session_info(sid) for sid in self.sessions.keys()]

    async def _read_session_output(self, session: PTYSession):
        """Background task to read output from a PTY session."""
        try:
            while session.is_active and self._running:
                data = session.read()
                if data and session.output_callback:
                    try:
                        session.output_callback(data)
                    except Exception as e:
                        logger.error(
                            f"Error in output callback for session {session.session_id}: {e}"
                        )

                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)

        except Exception as e:
            logger.error(f"Error reading from PTY session {session.session_id}: {e}")
            session.is_active = False

    async def _cleanup_inactive_sessions(self):
        """Background task to clean up inactive sessions."""
        while self._running:
            try:
                current_time = asyncio.get_event_loop().time()
                inactive_sessions = []

                for session_id, session in self.sessions.items():
                    # Check if session is inactive (no activity for 30 minutes)
                    if (
                        not session.is_active
                        or current_time - session.last_activity > 1800
                    ):
                        inactive_sessions.append(session_id)

                # Clean up inactive sessions
                for session_id in inactive_sessions:
                    await self.close_session(session_id)

                # Sleep for 60 seconds before next cleanup check
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in PTY cleanup task: {e}")
                await asyncio.sleep(60)
