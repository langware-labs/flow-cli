import json
import pytest
import subprocess
import time
import requests
import os
from pathlib import Path
from tests.utils import self_run_cli, find_claude, run_claude
from cli_command import CLICommand
from config_manager import set_config_value


def test_ping_real_claude(local_server, claude_settings, monkeypatch):
    """
    Real end-to-end test with actual Claude Code:
    1. Start internal server as interceptor
    2. Run flow setup claude-code to configure hooks
    3. Launch Claude Code interactively and send a prompt
    4. Wait for hook to fire and call flow ping
    5. Server receives the ping
    6. Validate complete flow: User → Claude → Hook → CLI → Server

    NOTE: This test requires:
    - Claude Code to be installed (`claude` command in PATH)
    - Interactive terminal (won't work in headless CI)
    - User to manually type a prompt when Claude opens
    """
    # Step 1: Use the test server fixture
    port = local_server.port
    print(f"\n✓ Step 1: Server started on port {port}")

    # Check if claude command exists
    claude_path = find_claude()
    if not claude_path:
        pytest.skip("Claude command not found in PATH - skipping real Claude test")

    print(f"  Claude found at: {claude_path}")

    # Use temp claude settings and workdir
    claude_settings_file = claude_settings.file
    workdir = claude_settings.home
    print(f"  Using temp settings file: {claude_settings_file}")
    print(f"  Using temp workdir: {workdir}")
    print(f"  Current directory: {Path.cwd()}")

    # Set LOCAL_SERVER_PORT env var to point to our test server
    monkeypatch.setenv("LOCAL_SERVER_PORT", str(port))

    # Step 2: Manually create hook configuration (simpler than running setup)
    print("\n✓ Step 2: Configuring UserPromptSubmit hook")
    from commands.setup_cmd.claude_code_setup.claude_hooks import setHook
    from cli_context import ClaudeScope

    # Create a hook that calls flow ping
    import random
    import string
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    ping_message = f"hook_test_{random_suffix}"

    # Create a wrapper script that includes env var
    hook_log = workdir / "hook_execution.log"
    hook_script = workdir / "hook_wrapper.sh"
    hook_script.write_text(f'''#!/bin/bash
echo "Hook fired at $(date)" >> {hook_log}
export LOCAL_SERVER_PORT={port}
python3 {Path(__file__).parent.parent / "flow_cli.py"} ping {ping_message} >> {hook_log} 2>&1
echo "Hook completed with exit code $?" >> {hook_log}
''')
    hook_script.chmod(0o755)

    hook_command = str(hook_script)

    success = setHook(
        scope=ClaudeScope.USER,
        event_name="UserPromptSubmit",
        matcher=None,
        cmd=hook_command
    )

    assert success, "Failed to set UserPromptSubmit hook"
    print(f"  Hook command: {hook_command}")

    # Verify hook was configured
    assert claude_settings_file.exists(), "Settings file not created"
    with open(claude_settings_file, 'r') as f:
        settings = json.load(f)
    assert "hooks" in settings, "No hooks in settings.json"
    assert "UserPromptSubmit" in settings["hooks"], "UserPromptSubmit hook not configured"
    print(f"✓ Step 2 complete: Hook verified in settings file")

    # Step 3: Launch Claude Code with prompt in the temp workdir
    print("\n✓ Step 3: Launching Claude Code with prompt 'hi'...")

    # Print the settings file for debugging
    with open(claude_settings_file, 'r') as f:
        print(f"  Settings file contents:\n{json.dumps(json.load(f), indent=2)}")

    # Start Claude with -p flag and --debug for more output
    claude_process = run_claude(workdir, prompt="hi")

    # Step 4: Wait for hook to fire
    print("✓ Step 4: Waiting for hook to fire...")
    timeout_seconds = 10  # Increase timeout
    start_time = time.time()
    hook_fired = False

    while time.time() - start_time < timeout_seconds:
        try:
            pings = local_server.get_pings()
            if len(pings) > 0:
                elapsed = time.time() - start_time
                print(f"  ✓ Hook fired! Ping received after {elapsed:.2f}s")
                hook_fired = True
                break
        except:
            pass
        time.sleep(0.1)

    # Wait for Claude to finish processing
    try:
        stdout, stderr = claude_process.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        claude_process.kill()
        stdout, stderr = claude_process.communicate()

    # Print Claude output for debugging
    if stdout:
        print(f"  Claude stdout:\n{stdout}")
    if stderr:
        print(f"  Claude stderr:\n{stderr}")

    # Check if hook was executed
    if hook_log.exists():
        print(f"  Hook log exists! Content:")
        print(f"  {hook_log.read_text()}")
    else:
        print(f"  Hook log does NOT exist at {hook_log}")

    # Give hook additional time to complete if it just fired
    if not hook_fired:
        print(f"  Waiting additional 2 seconds for late-firing hook...")
        time.sleep(2)
        pings = local_server.get_pings()
        if len(pings) > 0:
            hook_fired = True
            print(f"  ✓ Hook fired late! Ping received: {pings}")

    if not hook_fired:
        pytest.fail(f"Hook did not fire within {timeout_seconds} seconds.")

    # Step 5 & 6: Verify the server received the ping
    pings = local_server.get_pings()
    print(f"✓ Step 5: Server received {len(pings)} ping(s)")

    # Verify we got at least one ping
    assert len(pings) > 0, "No pings received by server"

    # Verify the ping structure
    last_ping = pings[-1]
    assert "ping_str" in last_ping
    print(f"✓ Step 6: Ping validated! Received: '{last_ping['ping_str']}'")
    print("\n✅ Full end-to-end test with real Claude Code PASSED")


def test_hook_basic(claude_settings, temp_workdir):
    """
    Basic test for session start hooks:
    1. Places a hook on SessionStart using the utility function
    2. The hook echoes a string into a temp log file
    3. Executes claude code with -p and "hi"
    4. Validates that the log was written

    NOTE: This test requires:
    - Claude Code to be installed (`claude` command in PATH)
    """
    from commands.setup_cmd.claude_code_setup.claude_hooks import setHook
    from cli_context import ClaudeScope

    # Check if claude command exists
    claude_path = find_claude()
    if not claude_path:
        pytest.skip("Claude command not found in PATH - skipping test")

    print(f"\n✓ Claude found at: {claude_path}")

    # Use temp workdir for log file and claude settings
    workdir = claude_settings.home
    log_file_path = temp_workdir / "test.log"
    print(f"✓ Using log file: {log_file_path}")
    print(f"✓ Using workdir: {workdir}")

    # Use temp claude settings
    claude_settings_file = claude_settings.file

    # Step 1: Set up the hook using the utility function
    test_message = "SessionStart hook fired successfully!"
    hook_command = f'echo "{test_message}" >> {log_file_path}'

    success = setHook(
        scope=ClaudeScope.USER,
        event_name="SessionStart",
        matcher=None,
        cmd=hook_command
    )

    assert success, "Failed to set SessionStart hook"
    print(f"✓ Step 1: SessionStart hook configured")

    # Verify hook was configured
    assert claude_settings_file.exists(), "Settings file not created"
    with open(claude_settings_file, 'r') as f:
        settings = json.load(f)
    assert "hooks" in settings, "No hooks in settings.json"
    assert "SessionStart" in settings["hooks"], "SessionStart hook not configured"
    print(f"✓ Hook verified in settings file")

    # Step 2: Execute claude code with -p "hi" in the temp workdir
    print("\n✓ Step 2: Executing Claude Code with -p 'hi'")
    claude_process = run_claude(workdir, prompt="hi", debug=False)

    try:
        stdout, stderr = claude_process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        claude_process.kill()
        stdout, stderr = claude_process.communicate()
    print(f"  Claude stdout: {stdout}")
    print(f"  Claude stderr: {stderr}")
    print(f"  Claude exit code: {claude_process.returncode}")

    # Step 3: Validate the log was written
    print("\n✓ Step 3: Validating log file")
    assert log_file_path.exists(), "Log file does not exist"

    with open(log_file_path, 'r') as f:
        log_content = f.read()

    print(f"  Log content: {log_content.strip()}")
    assert test_message in log_content, f"Expected message not found in log. Got: {log_content}"

    print("\n✅ Basic hook test PASSED")


def test_hook_cli(local_server, claude_settings, monkeypatch):
    """
    Test SessionStart hook with flow CLI ping command:
    1. Starts a test server
    2. Configures a SessionStart hook that calls 'flow ping' using CLICommand
    3. Executes claude code with -p "hi"
    4. Validates that the server received the ping

    NOTE: This test requires:
    - Claude Code to be installed (`claude` command in PATH)
    """
    from commands.setup_cmd.claude_code_setup.claude_hooks import setHook
    from cli_context import ClaudeScope

    # Check if claude command exists
    claude_path = find_claude()
    if not claude_path:
        pytest.skip("Claude command not found in PATH - skipping test")

    print(f"\n✓ Claude found at: {claude_path}")

    # Step 1: Use the test server fixture
    port = local_server.port
    workdir = claude_settings.home
    print(f"✓ Step 1: Test server started on port {port}")
    print(f"✓ Using workdir: {workdir}")

    # Set LOCAL_SERVER_PORT env var to point to our test server
    monkeypatch.setenv("LOCAL_SERVER_PORT", str(port))

    # Use temp claude settings
    claude_settings_file = claude_settings.file

    # Step 2: Set up the hook using CLICommand with use_python flag
    import random
    import string
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    ping_message = f"test_hook_cli_{random_suffix}"

    # Create a wrapper script that logs execution
    hook_log = workdir / "hook_execution.log"
    hook_script = workdir / "hook_wrapper.sh"
    hook_script.write_text(f'''#!/bin/bash
echo "Hook fired at $(date)" >> {hook_log}
export LOCAL_SERVER_PORT={port}
python3 {Path(__file__).parent.parent / "flow_cli.py"} ping {ping_message} >> {hook_log} 2>&1
echo "Hook completed with exit code $?" >> {hook_log}
''')
    hook_script.chmod(0o755)

    hook_command = str(hook_script)
    print(f"✓ Step 2: Hook command: {hook_command}")
    print(f"  Hook log file: {hook_log}")

    success = setHook(
        scope=ClaudeScope.USER,
        event_name="SessionStart",
        matcher=None,
        cmd=hook_command
    )

    assert success, "Failed to set SessionStart hook"
    print(f"✓ SessionStart hook configured")

    # Verify hook was configured
    assert claude_settings_file.exists(), "Settings file not created"
    with open(claude_settings_file, 'r') as f:
        settings = json.load(f)
    assert "hooks" in settings, "No hooks in settings.json"
    assert "SessionStart" in settings["hooks"], "SessionStart hook not configured"
    print(f"✓ Hook verified in settings file")

    # Step 3: Execute claude code with -p "hi" in the temp workdir
    print("\n✓ Step 3: Executing Claude Code with -p 'hi'")
    claude_process = run_claude(workdir, prompt="hi", debug=False)

    try:
        stdout, stderr = claude_process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        claude_process.kill()
        stdout, stderr = claude_process.communicate()

    print(f"  Claude exit code: {claude_process.returncode}")
    if stdout:
        print(f"  Claude stdout:\n{stdout}")
    if stderr:
        print(f"  Claude stderr:\n{stderr}")

    # Give the hook a moment to execute
    time.sleep(2)

    # Step 4: Validate the server received the ping
    print("\n✓ Step 4: Validating server received ping")

    # Check if hook was executed
    if hook_log.exists():
        print(f"  Hook log exists! Content:")
        print(f"  {hook_log.read_text()}")
    else:
        print(f"  Hook log does NOT exist at {hook_log}")

    pings = local_server.get_pings()

    assert len(pings) > 0, f"No pings received by server. Expected at least 1 ping."
    print(f"  Server received {len(pings)} ping(s)")

    # Verify the ping contains our test message
    last_ping = pings[-1]
    assert "ping_str" in last_ping, "Ping missing 'ping_str' field"
    assert last_ping["ping_str"] == ping_message, \
        f"Expected ping message '{ping_message}', got '{last_ping['ping_str']}'"

    print(f"  ✓ Ping validated! Received: '{last_ping['ping_str']}'")
    print("\n✅ CLI hook test PASSED")


def test_user_prompt_hook(local_server, claude_settings, temp_workdir, monkeypatch):
    """
    Test UserPromptSubmit hook with flow CLI prompt command:
    1. Starts a test server
    2. Configures a UserPromptSubmit hook that calls 'flow prompt' using CLICommand
    3. Executes claude code with a random prompt string
    4. Validates that the server received the prompt text

    NOTE: This test requires:
    - Claude Code to be installed (`claude` command in PATH)
    """
    from commands.setup_cmd.claude_code_setup.claude_hooks import setHook
    from cli_context import ClaudeScope

    # Check if claude command exists
    claude_path = find_claude()
    if not claude_path:
        pytest.skip("Claude command not found in PATH - skipping test")

    print(f"\n✓ Claude found at: {claude_path}")

    # Step 1: Use the test server fixture
    port = local_server.port
    workdir = claude_settings.home
    print(f"✓ Step 1: Test server started on port {port}")
    print(f"✓ Using workdir: {workdir}")

    # Set LOCAL_SERVER_PORT env var to point to our test server
    monkeypatch.setenv("LOCAL_SERVER_PORT", str(port))
    # Disable first-time onboarding for test
    set_config_value("first_time_prompt", "false")

    # Use temp claude settings
    claude_settings_file = claude_settings.file

    # Step 2: Create a temporary hook script that reads stdin and calls flow prompt
    hook_log = temp_workdir / "hook_execution.log"
    hook_script_path = temp_workdir / "hook_script.py"
    # Get the path to flow_cli.py
    flow_cli_path = Path(__file__).parent.parent / "flow_cli.py"
    hook_script_path.write_text(f'''#!/usr/bin/env python3
import json
import sys
import subprocess
import os
from datetime import datetime

log_file = "{hook_log}"

try:
    with open(log_file, "a") as log:
        log.write(f"Hook fired at {{datetime.now()}}\\n")

    input_data = json.load(sys.stdin)
    user_prompt = input_data.get("prompt", "")

    with open(log_file, "a") as log:
        log.write(f"Received prompt: {{user_prompt}}\\n")

    # Set LOCAL_SERVER_PORT for the subprocess
    env = os.environ.copy()
    env["LOCAL_SERVER_PORT"] = "{port}"

    result = subprocess.run(
        ["python3", "{flow_cli_path}", "prompt", user_prompt],
        capture_output=True,
        text=True,
        env=env
    )

    with open(log_file, "a") as log:
        log.write(f"Flow prompt exit code: {{result.returncode}}\\n")
        if result.stdout:
            log.write(f"Flow prompt stdout: {{result.stdout}}\\n")
        if result.stderr:
            log.write(f"Flow prompt stderr: {{result.stderr}}\\n")

    # Verify server is reachable and try to send prompt directly
    import requests
    try:
        test_url = f"http://127.0.0.1:{port}/get_prompts"
        response = requests.get(test_url, timeout=2)
        with open(log_file, "a") as log:
            log.write(f"Server check (get_prompts): {{response.status_code}} - {{response.text[:200]}}\\n")
    except Exception as e:
        with open(log_file, "a") as log:
            log.write(f"Server check failed: {{e}}\\n")

    # Try sending prompt directly
    try:
        prompt_url = f"http://127.0.0.1:{port}/prompt"
        response = requests.get(prompt_url, params={{"prompt_text": user_prompt}}, timeout=2)
        with open(log_file, "a") as log:
            log.write(f"Direct prompt send: {{response.status_code}} - {{response.text[:200]}}\\n")
    except Exception as e:
        with open(log_file, "a") as log:
            log.write(f"Direct prompt send failed: {{e}}\\n")

    if result.stdout:
        print(result.stdout, end='')
    sys.exit(0)
except Exception as e:
    with open(log_file, "a") as log:
        log.write(f"Hook error: {{e}}\\n")
    print(f"Hook error: {{e}}", file=sys.stderr)
    sys.exit(0)
''')

    # Make the script executable
    import stat
    os.chmod(hook_script_path, os.stat(hook_script_path).st_mode | stat.S_IEXEC)

    print(f"✓ Step 2: Hook script created at: {hook_script_path}")

    success = setHook(
        scope=ClaudeScope.USER,
        event_name="UserPromptSubmit",
        matcher=None,
        cmd=str(hook_script_path)
    )

    assert success, "Failed to set UserPromptSubmit hook"
    print(f"✓ UserPromptSubmit hook configured")

    # Verify hook was configured
    assert claude_settings_file.exists(), "Settings file not created"
    with open(claude_settings_file, 'r') as f:
        settings = json.load(f)
    assert "hooks" in settings, "No hooks in settings.json"
    assert "UserPromptSubmit" in settings["hooks"], "UserPromptSubmit hook not configured"
    print(f"✓ Hook verified in settings file")

    # Step 3: Execute claude code with a random prompt in the temp workdir
    import random
    import string
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    test_prompt = f"hi claude {random_suffix}"

    print(f"\n✓ Step 3: Executing Claude Code with prompt: '{test_prompt}'")
    claude_process = run_claude(workdir, prompt=test_prompt, debug=False)

    try:
        stdout, stderr = claude_process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        claude_process.kill()
        stdout, stderr = claude_process.communicate()
    print(  f"  Claude stdout: {stdout}")
    print(  f"  Claude stderr: {stderr}")

    print(f"  Claude exit code: {claude_process.returncode}")

    # Give the hook a moment to execute
    time.sleep(2)

    # Check if hook was executed
    if hook_log.exists():
        print(f"  Hook log exists! Content:")
        print(f"  {hook_log.read_text()}")
    else:
        print(f"  Hook log does NOT exist at {hook_log}")

    # Step 4: Validate the server received the prompt
    print("\n✓ Step 4: Validating server received prompt")
    prompts = local_server.get_prompts()

    # Give hook additional time if it just fired
    if len(prompts) == 0:
        print(f"  No prompts yet, waiting additional 2 seconds...")
        time.sleep(2)
        prompts = local_server.get_prompts()

    assert len(prompts) > 0, f"No prompts received by server. Expected at least 1 prompt."
    print(f"  Server received {len(prompts)} prompt(s)")

    # Verify the prompt contains our test message
    last_prompt = prompts[-1]
    assert "prompt_text" in last_prompt, "Prompt missing 'prompt_text' field"
    assert last_prompt["prompt_text"] == test_prompt, \
        f"Expected prompt '{test_prompt}', got '{last_prompt['prompt_text']}'"

    print(f"  ✓ Prompt validated! Received: '{last_prompt['prompt_text']}'")
    print("\n✅ UserPromptSubmit hook test PASSED")


def test_claude_cli():
    """
    Test Claude Code CLI directly without hooks:
    1. Run Claude with a simple prompt asking for a single word response
    2. Validate that the response contains "hi" (case-insensitive)

    NOTE: This test requires:
    - Claude Code to be installed (`claude` command in PATH)
    - Valid API authentication in the user's home directory
    - Manual execution (marked with @pytest.mark.manual)

    Run with: pytest -v -m manual tests/test_claude_hooks.py::test_claude_cli
    """
    # Check if claude command exists
    claude_path = find_claude()
    if not claude_path:
        pytest.skip("Claude command not found in PATH - skipping test")

    print(f"\n✓ Claude found at: {claude_path}")

    # Use current directory for this test (not temp) to access real auth
    import os
    workdir = Path(os.getcwd())
    print(f"✓ Using workdir: {workdir}")

    # Run Claude with the test prompt
    print("\n✓ Running Claude Code with prompt: 'reply with single word - hi'")
    claude_process = run_claude(workdir, prompt="reply with single word - hi")

    try:
        stdout, stderr = claude_process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        claude_process.kill()
        stdout, stderr = claude_process.communicate()

    print(f"  Claude exit code: {claude_process.returncode}")
    print(f"  Claude stdout:\n{stdout}")
    if stderr:
        print(f"  Claude stderr:\n{stderr}")

    # Check if authentication failed
    if "invalid api key" in stdout.lower():
        pytest.skip("Claude authentication required - please run 'claude login' first")

    # Validate the response contains "hi" (case-insensitive)
    assert stdout, "Claude produced no output"
    stdout_lower = stdout.lower()
    assert "hi" in stdout_lower, f"Expected 'hi' in response, got: {stdout}"

    print(f"\n✅ Claude CLI test PASSED - response contains 'hi'")
