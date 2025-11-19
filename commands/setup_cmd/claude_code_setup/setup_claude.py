#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from commands.setup_cmd.claude_code_setup.hook_parser import HookParser


def setup_claude_code():
    """
    Run the setup specific to Claude Code.

    Returns:
        str: Setup result message
    """
    print("Setting up Claude Code integration...")

    # Initialize the hook parser
    hook_parser = HookParser()

    print("Configuring Claude Code hooks...")

    # Get the absolute path to the flow_prompt_hook.py script
    # This script should be installed with the flow-cli package
    hook_script_path = _get_hook_script_path()

    if not hook_script_path.exists():
        print(f"⚠ Warning: Hook script not found at {hook_script_path}")
        print("  Creating hook script...")
        _ensure_hook_script_exists(hook_script_path)

    # Make the hook script executable
    os.chmod(hook_script_path, 0o755)

    # Add UserPromptSubmit hook (no matcher needed for this event)
    hook_parser.add_hook(
        event_name="UserPromptSubmit",
        matcher=None,  # UserPromptSubmit doesn't use matchers
        hook_type="command",
        command=str(hook_script_path)
    )

    # Save the hooks configuration
    hook_parser.save_hooks()

    print(f"✓ Hook configured: UserPromptSubmit -> {hook_script_path}")
    print("✓ Claude Code setup complete!")
    print("\n" + "="*50)
    print("🎉 Restart Claude and type 'hello' to start :)")
    print("="*50)

    return "Claude Code setup successful"


def _get_hook_script_path() -> Path:
    """
    Get the path to the flow_prompt_hook.py script.

    Returns:
        Path to the hook script
    """
    # Try to find the script in the installed package location
    try:
        import commands.setup_cmd.claude_code_setup
        package_dir = Path(commands.setup_cmd.claude_code_setup.__file__).parent
        hook_script = package_dir / "flow_prompt_hook.py"
        return hook_script
    except Exception:
        # Fallback to local installation
        return Path(__file__).parent / "flow_prompt_hook.py"


def _ensure_hook_script_exists(hook_script_path: Path):
    """
    Ensure the hook script exists, create if missing.

    Args:
        hook_script_path: Path where the hook script should be
    """
    hook_script_content = '''#!/usr/bin/env python3
"""
Claude Code hook script for UserPromptSubmit event.
Receives user prompt via stdin and forwards to 'flow prompt' command.
"""

import json
import sys
import subprocess


def main():
    try:
        # Read the hook input from stdin
        input_data = json.load(sys.stdin)

        # Extract the user's prompt
        user_prompt = input_data.get("prompt", "")

        # Run the flow prompt command
        result = subprocess.run(
            ["flow", "prompt", user_prompt],
            capture_output=True,
            text=True
        )

        # Print any output from the flow command
        if result.stdout:
            print(result.stdout, end='')

        # Exit with 0 to allow the prompt to proceed
        sys.exit(0)

    except Exception as e:
        # Log error but don't block the prompt
        print(f"Flow hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
'''

    hook_script_path.parent.mkdir(parents=True, exist_ok=True)
    hook_script_path.write_text(hook_script_content)
    os.chmod(hook_script_path, 0o755)


def add_flow_tracking_hook():
    """
    Example function to add Flow tracking hook to Claude Code.
    """
    hook_parser = HookParser()

    # Add a hook to track all tool usage
    hook_parser.add_hook(
        event_name="tool_use",
        matcher="*",
        hook_type="command",
        command="flow track tool-use"
    )

    hook_parser.save_hooks()
    print("✓ Flow tracking hook added successfully!")


def list_claude_hooks():
    """
    Example function to list all Claude Code hooks.
    """
    hook_parser = HookParser()

    events = hook_parser.list_events()

    if not events:
        print("No hooks configured.")
        return

    print("Configured hooks:")
    for event in events:
        print(f"\nEvent: {event}")
        matchers = hook_parser.list_matchers(event)
        for matcher in matchers:
            print(f"  Matcher: {matcher}")
            hooks = hook_parser.get_hook_details(event, matcher)
            if hooks:
                for hook in hooks:
                    print(f"    - Type: {hook.get('type')}")
                    print(f"      Command: {hook.get('command')}")


def remove_flow_hooks():
    """
    Example function to remove Flow-related hooks from Claude Code.
    """
    hook_parser = HookParser()

    # Remove all hooks with Flow commands
    removed = hook_parser.remove_hook(
        event_name="tool_use",
        command="flow track tool-use"
    )

    if removed:
        hook_parser.save_hooks()
        print("✓ Flow hooks removed successfully!")
    else:
        print("No Flow hooks found to remove.")
