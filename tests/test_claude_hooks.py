import json
import pytest
import subprocess
import time
import threading
import requests
import os
from pathlib import Path
from local_server.server import app, start_server
from tests.utils import self_run_cli


@pytest.mark.manual
def test_ping_real_claude():
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

    # Check if claude command exists
    claude_check = subprocess.run(
        ["which", "claude"],
        capture_output=True,
        text=True
    )

    if claude_check.returncode != 0:
        pytest.skip("Claude command not found in PATH - skipping real Claude test")

    print(f"  Claude found at: {claude_check.stdout.strip()}")

    # Backup existing settings if they exist
    claude_settings_file = Path.home() / ".claude" / "settings.json"
    backup_file = None
    if claude_settings_file.exists():
        backup_file = claude_settings_file.with_suffix('.json.backup_test')
        import shutil
        shutil.copy2(claude_settings_file, backup_file)
        print(f"  Backed up existing settings to {backup_file}")

    try:
        # Update config to point to our test server
        from config_manager import set_config_value
        set_config_value("local_cli_port", str(port))

        # Step 2: Run flow setup claude-code
        print("\n✓ Step 2: Running flow setup claude-code")
        setup_result = self_run_cli("setup claude-code")
        print(f"  Setup exit code: {setup_result.returncode}")
        if setup_result.stdout:
            print(f"  Setup output:\n{setup_result.stdout}")

        # Verify hook was configured (setup uses PROJECT scope if in repo)
        project_settings_file = Path(__file__).parent.parent / ".claude" / "settings.json"

        # Check which settings file was created
        settings_file_to_check = None
        if project_settings_file.exists():
            settings_file_to_check = project_settings_file
            print(f"  Hook configured in PROJECT scope: {project_settings_file}")
        elif claude_settings_file.exists():
            settings_file_to_check = claude_settings_file
            print(f"  Hook configured in USER scope: {claude_settings_file}")

        assert settings_file_to_check is not None, "No settings file created by setup"

        with open(settings_file_to_check, 'r') as f:
            settings = json.load(f)
        assert "hooks" in settings, "No hooks in settings.json"
        assert "UserPromptSubmit" in settings["hooks"], "UserPromptSubmit hook not configured"
        print(f"✓ Step 2 complete: Hook verified in settings file")

        # Step 3: Launch Claude Code interactively
        print("\n✓ Step 3: Launching Claude Code interactively...")
        print("  ⚠ MANUAL INTERACTION REQUIRED:")
        print("  - Claude will open in interactive mode")
        print("  - Please type ANY message and press Enter")
        print("  - The hook will intercept it and call 'flow ping'")
        print("  - Waiting 30 seconds for you to type a message...")
        print()

        # Start Claude in interactive mode (no -p flag)
        claude_process = subprocess.Popen(
            ["claude", "--dangerously-skip-permissions"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Step 4: Wait for hook to fire
        print("✓ Step 4: Waiting for hook to fire...")
        timeout_seconds = 30
        start_time = time.time()
        hook_fired = False

        while time.time() - start_time < timeout_seconds:
            try:
                response = requests.get(f"http://127.0.0.1:{port}/get_pings", timeout=1)
                if response.status_code == 200:
                    pings = response.json()["pings"]
                    if len(pings) > 0:
                        elapsed = time.time() - start_time
                        print(f"  ✓ Hook fired! Ping received after {elapsed:.2f}s")
                        hook_fired = True
                        break
            except:
                pass
            time.sleep(0.5)

        # Kill Claude process
        try:
            claude_process.terminate()
            claude_process.wait(timeout=2)
        except:
            claude_process.kill()
            claude_process.wait()

        if not hook_fired:
            pytest.fail(f"Hook did not fire within {timeout_seconds} seconds. Did you type a message in Claude?")

        # Step 5 & 6: Verify the server received the ping
        response = requests.get(f"http://127.0.0.1:{port}/get_pings", timeout=5)
        assert response.status_code == 200

        pings = response.json()["pings"]
        print(f"✓ Step 5: Server received {len(pings)} ping(s)")

        # Verify we got at least one ping
        assert len(pings) > 0, "No pings received by server"

        # Verify the ping structure
        last_ping = pings[-1]
        assert "ping_str" in last_ping
        print(f"✓ Step 6: Ping validated! Received: '{last_ping['ping_str']}'")
        print("\n✅ Full end-to-end test with real Claude Code PASSED")

    finally:
        # Clean up project settings if created
        project_settings_file = Path(__file__).parent.parent / ".claude" / "settings.json"
        if project_settings_file.exists():
            project_settings_file.unlink()
            print(f"\n  Removed project settings file")
            # Remove .claude directory if empty
            claude_dir = project_settings_file.parent
            if claude_dir.exists() and not any(claude_dir.iterdir()):
                claude_dir.rmdir()

        # Restore backup if it exists
        if backup_file and backup_file.exists():
            import shutil
            shutil.move(str(backup_file), str(claude_settings_file))
            print(f"  Restored original user settings from backup")
