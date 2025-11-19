import json
import pytest
import subprocess
import time
import threading
import requests
import os
from pathlib import Path
from cli_context import CLIContext, ClaudeScope
from commands.setup_cmd.claude_code_setup.hook_parser import HookParser
from local_server.server import app, start_server


def self_run_cli(command: str):
    """
    Run the flow CLI as if it was invoked from command line.

    Args:
        command: The command string (e.g., "ping hello" or "setup claude-code")

    Returns:
        subprocess.CompletedProcess result
    """
    # Get the path to flow_cli.py
    project_root = Path(__file__).parent.parent
    flow_cli_path = project_root / "flow_cli.py"

    # Split the command into arguments
    args = command.split()

    # Set up environment with PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)

    # Run the CLI
    result = subprocess.run(
        ["python3", str(flow_cli_path)] + args,
        capture_output=True,
        text=True,
        env=env,
        timeout=10
    )

    return result


@pytest.fixture
def temp_settings_file(tmp_path):
    """Create a temporary settings file for testing."""
    settings_file = tmp_path / "settings.json"
    return settings_file


@pytest.fixture
def test_server():
    """Start a test server and return its port."""
    port = 9007  # Use different port to avoid conflicts

    # Clear any previous ping results
    from local_server.server import ping_results
    ping_results.clear()

    # Start server in background thread
    server_thread = threading.Thread(
        target=start_server,
        args=(port,),
        daemon=True
    )
    server_thread.start()

    # Give server time to start
    time.sleep(1)

    yield port

    # Server will be automatically stopped when test ends (daemon thread)


def test_ping():
    """
    Comprehensive test for the ping feedback loop:
    1. Start internal server as interceptor
    2. Use self_run_cli to invoke "flow ping <message>"
    3. Verify server receives the ping
    4. Validates complete CLI → Server feedback loop
    """
    # Step 1: Start the test server
    port = 9007
    from local_server.server import ping_results
    ping_results.clear()

    server_thread = threading.Thread(
        target=start_server,
        args=(port,),
        daemon=True
    )
    server_thread.start()
    time.sleep(1)

    print(f"\n✓ Step 1: Server started on port {port}")

    try:
        # Update config to point to our test server
        from config_manager import set_config_value
        set_config_value("local_cli_port", str(port))

        # Step 2: Use self_run_cli to send a ping
        test_message = "hello from test"

        print(f"✓ Step 2: Running CLI command: flow ping {test_message}")

        result = self_run_cli(f"ping {test_message}")

        print(f"✓ Step 3: CLI executed (exit code: {result.returncode})")
        if result.stdout:
            print(f"  stdout: {result.stdout.strip()}")
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()}")

        # Step 4: Verify the server received the ping
        response = requests.get(f"http://127.0.0.1:{port}/get_pings", timeout=5)
        assert response.status_code == 200

        pings = response.json()["pings"]
        print(f"✓ Step 4: Server received {len(pings)} ping(s)")

        # Verify we got at least one ping
        assert len(pings) > 0, "No pings received by server"

        # Verify the ping contains our test message
        last_ping = pings[-1]
        assert "ping_str" in last_ping
        assert last_ping["ping_str"] == test_message

        print(f"✓ Step 5: Ping validated! Received: '{last_ping['ping_str']}'")
        print("\n✅ Full feedback loop test PASSED")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
