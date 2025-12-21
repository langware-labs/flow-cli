#!/usr/bin/env python3
"""
Pytest configuration and fixtures for py-sdk tests.
"""

import os
import subprocess
import time
import pytest
import socket
from pathlib import Path


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

@pytest.fixture(scope="session", autouse=True)
def load_env():
    """
    Session-scoped fixture to load environment variables before any tests run.

    This fixture calls the cli_init function from env_loader to load
    environment variables from the .env.local file.
    """
    from env_loader import cli_init

    # Load environment variables
    cli_init()


@pytest.fixture
def local_server(request):
    """
    Function-scoped fixture to start and stop the local test server.

    This fixture:
    1. Starts the local server on a specified port (default 9007)
    2. Clears ping and prompt results
    3. Yields a server helper object
    4. Automatically stops when test completes (via daemon thread)

    Usage:
        def test_example(local_server):
            pings = local_server.get_pings()
            prompts = local_server.get_prompts()
            port = local_server.port

    The port can be customized using pytest.mark.parametrize or by passing
    a port parameter via indirect parametrization.
    """
    import threading
    import requests
    from local_server.server import start_server
    from local_server.state import ping_results, prompt_results

    # Get port from request param if provided, otherwise use default
    port = getattr(request, 'param', {}).get('port', 9007) if hasattr(request, 'param') else 9007

    # Clear results
    ping_results.clear()
    prompt_results.clear()

    # Start server in background thread
    server_thread = threading.Thread(
        target=start_server,
        args=(port,),
        daemon=True
    )
    server_thread.start()
    time.sleep(1)  # Wait for server to start

    # Create helper object
    class ServerHelper:
        def __init__(self, port):
            self.port = port
            self.base_url = f"http://127.0.0.1:{port}"

        def get_pings(self):
            """Retrieve pings from the server."""
            response = requests.get(f"{self.base_url}/get_pings", timeout=5)
            if response.status_code == 200:
                return response.json()["pings"]
            return []

        def get_prompts(self):
            """Retrieve prompts from the server."""
            response = requests.get(f"{self.base_url}/get_prompts", timeout=5)
            if response.status_code == 200:
                return response.json()["prompts"]
            return []

    yield ServerHelper(port)


@pytest.fixture
def temp_workdir(tmp_path):
    """
    Function-scoped fixture that provides a temporary working directory.

    The directory is automatically cleaned up after the test completes.

    Usage:
        def test_example(temp_workdir):
            file_path = temp_workdir / "test.txt"
            file_path.write_text("test")

    Yields:
        Path: Temporary directory path
    """
    yield tmp_path


@pytest.fixture
def claude_settings(temp_workdir, monkeypatch):
    """
    Function-scoped fixture that provides a temporary Claude settings directory.

    Creates a .claude directory in the temp workdir and provides the settings.json path.
    The directory structure is automatically cleaned up after the test.

    This fixture also:
    - Sets the HOME environment variable to temp_workdir
    - Changes current directory to temp_workdir
    - Automatically restores both after the test

    Usage:
        def test_example(claude_settings):
            settings_file = claude_settings.file
            settings_dir = claude_settings.dir

            # Write settings
            settings_file.write_text('{"hooks": {}}')

    Yields:
        object: Settings helper with attributes:
            - file: Path to settings.json
            - dir: Path to .claude directory
            - home: Path to temp home directory (same as temp_workdir)
    """
    import os

    # Save original working directory and HOME
    original_cwd = Path.cwd()
    original_home = os.environ.get("HOME")

    # Copy authentication files from real user's .claude directory BEFORE changing HOME
    # This allows Claude Code to run properly in tests
    import shutil
    if original_home:
        real_claude_dir = Path(original_home) / ".claude"

        # Create .claude directory in the temp home
        claude_dir = temp_workdir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Copy .claude.json (contains API key) if it exists
        if (real_claude_dir / ".claude.json").exists():
            shutil.copy(real_claude_dir / ".claude.json", claude_dir / ".claude.json")

        # Copy .claude.json.backup if it exists
        if (real_claude_dir / ".claude.json.backup").exists():
            shutil.copy(real_claude_dir / ".claude.json.backup", claude_dir / ".claude.json.backup")
    else:
        # Create .claude directory in the temp home
        claude_dir = temp_workdir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

    # Set HOME to temp_workdir and change to it
    monkeypatch.setenv("HOME", str(temp_workdir))
    os.chdir(temp_workdir)

    settings_file = claude_dir / "settings.json"

    class SettingsHelper:
        def __init__(self, file_path, dir_path, home_path):
            self.file = file_path
            self.dir = dir_path
            self.home = home_path

    yield SettingsHelper(settings_file, claude_dir, temp_workdir)

    # Restore original working directory
    os.chdir(original_cwd)


@pytest.fixture(scope="session")
def flowpad_server():
    """
    Session-scoped fixture to start and stop the Flowpad backend server.

    This fixture:
    1. Reads FLOWPAD_SERVER_RUN_PATH environment variable (raises exception if missing)
    2. Optionally reads FLOWPAD_SERVER_PORT environment variable (uses default if missing)
    3. Starts the Flowpad server as a subprocess
    4. Yields the server process and port
    5. Terminates the server after all tests complete

    Raises:
        RuntimeError: If FLOWPAD_SERVER_RUN_PATH is not set

    Yields:
        dict: Server information with keys 'process', 'port', 'base_url'
    """
    # Get the server run path from environment
    server_run_path = os.environ.get("FLOWPAD_SERVER_RUN_PATH")
    if not server_run_path:
        raise RuntimeError(
            "FLOWPAD_SERVER_RUN_PATH environment variable is required but not set. "
            "Please set it to the path of the Flowpad server executable."
        )

    # Check if the server run path exists
    if not Path(server_run_path).exists():
        raise RuntimeError(
            f"FLOWPAD_SERVER_RUN_PATH points to non-existent path: {server_run_path}"
        )

    # Get the port from environment, use default if not set
    port = int(os.environ.get("FLOWPAD_SERVER_PORT", "8000"))

    # Check if port is already in use
    if is_port_in_use(port):
        raise RuntimeError(
            f"Port {port} is already in use. Please free the port or set "
            "FLOWPAD_SERVER_PORT to a different port number."
        )

    # Start the server
    cmd = [server_run_path]
    env = os.environ.copy()
    env["PORT"] = str(port)

    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for server to be ready
    base_url = f"http://127.0.0.1:{port}"
    max_wait = 10  # seconds
    wait_interval = 0.1  # seconds
    total_waited = 0

    while total_waited < max_wait:
        if is_port_in_use(port):
            # Server is ready
            break
        time.sleep(wait_interval)
        total_waited += wait_interval

        # Check if process died
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(
                f"Flowpad server failed to start.\n"
                f"Exit code: {process.returncode}\n"
                f"STDOUT: {stdout}\n"
                f"STDERR: {stderr}"
            )
    else:
        # Timeout waiting for server
        process.terminate()
        process.wait()
        raise RuntimeError(
            f"Flowpad server did not start within {max_wait} seconds. "
            f"Port {port} is not accepting connections."
        )

    # Yield server information
    server_info = {
        "process": process,
        "port": port,
        "base_url": base_url
    }

    yield server_info

    # Teardown: stop the server
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
