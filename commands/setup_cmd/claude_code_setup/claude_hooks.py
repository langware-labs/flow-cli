#!/usr/bin/env python3
"""
Claude Code hooks management functions.
Provides high-level API for setting and removing hooks.
"""

from typing import Optional
from cli_command import CLICommand
from cli_context import CLIContext, ClaudeScope
from commands.setup_cmd.claude_code_setup.hook_parser import HookParser


def setHook(
    scope: ClaudeScope,
    event_name: str,
    matcher: Optional[str],
    cmd: str,
    context: Optional[CLIContext] = None
) -> bool:
    """
    Set a hook for a specific event in Claude Code settings.

    Args:
        scope: The Claude scope (PROJECT or USER)
        event_name: The event name (e.g., "UserPromptSubmit", "tool_use")
        matcher: Optional matcher pattern (None for events that don't use matchers)
        cmd: The command to execute (e.g., "flow ping hello")
        context: Optional CLIContext. If not provided, creates a new one.

    Returns:
        bool: True if hook was set successfully, False otherwise

    Example:
        setHook(ClaudeScope.PROJECT, "UserPromptSubmit", None, "flow prompt")
        setHook(ClaudeScope.USER, "tool_use", "bash", "flow track bash")
    """
    try:
        # Create context if not provided
        if context is None:
            context = CLIContext()

        # Initialize hook parser with the specified scope
        hook_parser = HookParser(context=context, scope=scope)

        # Add the hook
        hook_parser.add_hook(
            event_name=event_name,
            matcher=matcher,
            hook_type="command",
            command=cmd
        )

        # Save the hooks configuration
        hook_parser.save_hooks()

        return True

    except Exception as e:
        print(f"Error setting hook: {e}")
        return False


def removeHook(
    scope: ClaudeScope,
    event_name: str,
    matcher: Optional[str],
    context: Optional[CLIContext] = None
) -> bool:
    """
    Remove a hook only if the command is a flow command.

    This function validates that the hook's command is a flow CLI command
    before removing it, to avoid accidentally removing non-flow hooks.

    Args:
        scope: The Claude scope (PROJECT or USER)
        event_name: The event name (e.g., "UserPromptSubmit", "tool_use")
        matcher: Optional matcher pattern (None for events that don't use matchers)
        context: Optional CLIContext. If not provided, creates a new one.

    Returns:
        bool: True if a flow hook was found and removed, False otherwise

    Example:
        removeHook(ClaudeScope.PROJECT, "UserPromptSubmit", None)
        removeHook(ClaudeScope.USER, "tool_use", "bash")
    """
    try:
        # Create context if not provided
        if context is None:
            context = CLIContext()

        # Initialize hook parser with the specified scope
        hook_parser = HookParser(context=context, scope=scope)

        # Get the hook details to check if it's a flow command
        hooks = hook_parser.get_hook_details(event_name, matcher)

        if not hooks:
            print(f"No hooks found for event '{event_name}' with matcher '{matcher}'")
            return False

        # Check each hook to see if it's a flow command
        removed_any = False
        for hook in hooks:
            hook_command = hook.get("command", "")

            if _is_flow_command(hook_command):
                # This is a flow command, safe to remove
                success = hook_parser.remove_hook(
                    event_name=event_name,
                    matcher=matcher,
                    command=hook_command
                )

                if success:
                    removed_any = True
                    print(f"✓ Removed flow hook: {hook_command}")
            else:
                print(f"Skipping non-flow hook: {hook_command}")

        # Save if we removed anything
        if removed_any:
            hook_parser.save_hooks()

        return removed_any

    except Exception as e:
        print(f"Error removing hook: {e}")
        return False


def _is_flow_command(command: str) -> bool:
    """
    Check if a command string is a flow CLI command.

    Uses CLICommand to parse and validate the command.

    Args:
        command: The command string to check

    Returns:
        bool: True if it's a flow command, False otherwise
    """
    try:
        # Check if command starts with "flow" or contains "flow_cli.py"
        if command.strip().startswith("flow ") or "flow_cli.py" in command:
            return True

        # Try to parse as absolute path
        if command.startswith("/"):
            # Check if it ends with a flow-related script
            if "flow_prompt_hook.py" in command or "flow" in command.split("/")[-1]:
                return True

        return False

    except Exception:
        return False
