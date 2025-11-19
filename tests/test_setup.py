import json
import pytest
import subprocess
import time
import threading
import requests
from pathlib import Path
from cli_context import CLIContext, ClaudeScope
from commands.setup_cmd.claude_code_setup.hook_parser import HookParser
from local_server.server import app, start_server


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
    2. Configure hook on UserPromptSubmit event
    3. Simulate Claude prompt submission
    4. Hook calls flow ping with the prompt
    5. Server receives the ping
    6. Test validates the ping was received
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
        # Step 2: Configure the hook
        # Create a temporary directory for test configuration
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            settings_file = tmp_path / "settings.json"

            # Create a context and hook parser
            hook_parser = HookParser(hooks_file_path=str(settings_file))

            # Get the path to the ping hook script
            hook_script_path = Path(__file__).parent.parent / "commands" / "setup_cmd" / "claude_code_setup" / "flow_ping_hook.py"

            # Make sure the hook script exists and is executable
            assert hook_script_path.exists(), f"Hook script not found at {hook_script_path}"

            # Add the hook for UserPromptSubmit
            hook_parser.add_hook(
                event_name="UserPromptSubmit",
                matcher=None,  # UserPromptSubmit doesn't use matchers
                hook_type="command",
                command=str(hook_script_path)
            )

            hook_parser.save_hooks()

            # Verify the hook was configured
            assert settings_file.exists()
            with open(settings_file, 'r') as f:
                data = json.load(f)
            assert "hooks" in data
            assert "UserPromptSubmit" in data["hooks"]

            print("✓ Step 2: Hook configured in settings.json")

            # Step 3: Simulate Claude prompt submission by calling the hook directly
            test_prompt = "hi claude"

            # Prepare the input data that Claude would send to the hook
            hook_input = {
                "prompt": test_prompt,
                "event": "UserPromptSubmit"
            }

            # Update config to point to our test server
            from config_manager import set_config_value
            set_config_value("local_cli_port", str(port))

            print(f"✓ Step 3: Simulating prompt: '{test_prompt}'")

            # Step 4: Call the hook script
            # Set PYTHONPATH to include the project root so imports work
            import os
            project_root = Path(__file__).parent.parent
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_root)

            result = subprocess.run(
                ["python3", str(hook_script_path)],
                input=json.dumps(hook_input),
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )

            print(f"✓ Step 4: Hook executed (exit code: {result.returncode})")
            if result.stderr:
                print(f"  Hook stderr: {result.stderr}")

            # Give the ping time to reach the server
            time.sleep(1)

            # Step 5 & 6: Verify the server received the ping
            response = requests.get(f"http://127.0.0.1:{port}/get_pings", timeout=5)
            assert response.status_code == 200

            pings = response.json()["pings"]
            print(f"✓ Step 5: Server received {len(pings)} ping(s)")

            # Verify we got at least one ping
            assert len(pings) > 0, "No pings received by server"

            # Verify the ping contains our test prompt
            last_ping = pings[-1]
            assert "ping_str" in last_ping
            assert last_ping["ping_str"] == test_prompt

            print(f"✓ Step 6: Ping validated! Received: '{last_ping['ping_str']}'")
            print("\n✅ Full feedback loop test PASSED")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
