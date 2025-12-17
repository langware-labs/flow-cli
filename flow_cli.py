#!/usr/bin/env python3

import os
import typer
import requests
import threading
from typing import Optional
from typing_extensions import Annotated
from _version import __version__
from cli_context import CLIContext, ClaudeScope
from cli_command import CLICommand
from config_manager import list_config, set_config_value, remove_config_value, setup_defaults, get_config_value
from commands.setup_cmd.setup_cmd import run_setup
from commands.prompt_cmd import run_prompt_command
from env_loader import cli_init
from auth import set_api_key, delete_api_key, is_logged_in

# Initialize CLI - load environment variables as first step
cli_init()

# Create Typer app
app = typer.Typer(
    name="flow",
    help="Flow CLI tool for flowpad",
    add_completion=False
)

# Global context (initialized once)
_context: Optional[CLIContext] = None


def get_context() -> CLIContext:
    """Get or initialize the CLI context."""
    global _context
    if _context is None:
        _context = CLIContext()
    return _context


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Flow CLI - Main entry point.

    If no command is provided, prints version.
    """
    # Ensure config defaults are set
    setup_defaults()

    # If no subcommand was invoked, show version
    if ctx.invoked_subcommand is None:
        typer.echo(f"flow {__version__}")


@app.command()
def setup(
    agent_name: Annotated[str, typer.Argument(help="Name of the coding agent (e.g., claude-code)")],
):
    """
    Setup flowpad for a specific coding agent.

    Example: flow setup claude-code
    """
    context = get_context()
    cmd = CLICommand(f"setup {agent_name}", context=context)

    # Set first_time_prompt flag when running setup
    set_config_value("first_time_prompt", "true")

    run_setup(agent_name, cmd)


@app.command()
def prompt(
    prompt_text: Annotated[Optional[str], typer.Argument(help="Prompt text to process")] = None
):
    """
    Process a prompt command.

    Example: flow prompt "analyze this code"
    """
    if prompt_text:
        context = get_context()
        cmd = CLICommand(f"prompt {prompt_text}", context=context)
        run_prompt_command(prompt_text, cmd)


@app.command()
def ping(
    ping_str: Annotated[str, typer.Argument(help="Ping string to send")],
):
    """
    Send a ping to the local server for testing hook integration.

    Example: flow ping hello
    """
    context = get_context()
    cmd = CLICommand(f"ping {ping_str}", context=context)

    # Get the local server port from env
    port = int(os.environ.get("LOCAL_SERVER_PORT", "9007"))

    # Send ping to local server
    try:
        url = f"http://127.0.0.1:{port}/ping"
        response = requests.get(url, params={"ping_str": ping_str}, timeout=5)

        if response.status_code == 200:
            typer.echo(f"Ping sent successfully: {ping_str}")
        else:
            typer.echo(f"Ping failed with status {response.status_code}", err=True)
            raise typer.Exit(1)
    except requests.exceptions.RequestException as e:
        typer.echo(f"Error sending ping: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def start():
    """
    Start the Flow UI server and open it in the browser.

    Launches a local web server with the Flow control panel interface,
    which includes chat, hooks management, and directory selection.

    Example: flow start
    """
    import webbrowser
    import time

    # Get the local server port from env
    port = int(os.environ.get("LOCAL_SERVER_PORT", "9007"))

    typer.echo(f"\n🌊 Starting Flow UI on http://127.0.0.1:{port}")
    typer.echo(f"Opening browser...")
    typer.echo(f"\nPress Ctrl+C to stop the server\n")

    # Start server in a background thread
    from local_server.server import start_server
    server_thread = threading.Thread(
        target=start_server,
        args=(port,),
        daemon=True
    )
    server_thread.start()

    # Give server time to start
    time.sleep(1.5)

    # Open browser
    webbrowser.open(f"http://127.0.0.1:{port}")

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        typer.echo("\n\n✓ Server stopped")
        raise typer.Exit(0)


@app.command()
def trace():
    """
    Start the server and trace hook events in real-time.

    Displays hook events with colored output as they occur.
    Use Ctrl+C to stop.

    Usage:
      Terminal 1: flow trace
      Terminal 2: flow hooks set && claude -p "hello" && flow hooks clear
    """
    import time

    from local_server.server import start_server, reporter_registry
    from local_server.reporters import PrintReporter

    port = int(os.environ.get("LOCAL_SERVER_PORT", "9007"))

    typer.echo(f"Starting Flow trace server on port {port}...")

    # Create and register print reporter
    print_reporter = PrintReporter()
    reporter_registry.add(print_reporter)

    # Start server in background thread
    server_thread = threading.Thread(
        target=start_server,
        args=(port,),
        daemon=True
    )
    server_thread.start()

    # Give server time to start
    time.sleep(1)

    typer.echo(f"✓ Server started on http://127.0.0.1:{port}")
    typer.echo(f"\n\033[2mTip: Run 'flow hooks set' in another terminal to enable hooks\033[0m\n")
    typer.echo("Waiting for hook events (Ctrl+C to stop)\n")

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Cleanup
        reporter_registry.remove(print_reporter)
        typer.echo("\n\n✓ Trace stopped")
        raise typer.Exit(0)


# Config command group
config_app = typer.Typer(help="Manage configuration")
app.add_typer(config_app, name="config")


@config_app.command("list")
def config_list():
    """List all configuration values."""
    config = list_config()
    if not config:
        typer.echo("No configuration values set.")
    else:
        for key, value in config.items():
            typer.echo(f"{key}={value}")


@config_app.command("set")
def config_set(
    key_value: Annotated[str, typer.Argument(help="Configuration in format key=value")]
):
    """
    Set a configuration value.

    Example: flow config set timeout=30
    """
    if "=" not in key_value:
        typer.echo("Error: Expected format key=value", err=True)
        raise typer.Exit(1)

    key, value = key_value.split("=", 1)
    key = key.strip()
    value = value.strip()

    if not key:
        typer.echo("Error: Key cannot be empty", err=True)
        raise typer.Exit(1)

    set_config_value(key, value)
    typer.echo(f"Set {key}={value}")


@config_app.command("remove")
def config_remove(
    key: Annotated[str, typer.Argument(help="Configuration key to remove")]
):
    """
    Remove a configuration value.

    Example: flow config remove timeout
    """
    if remove_config_value(key):
        typer.echo(f"Removed {key}")
    else:
        typer.echo(f"Key '{key}' not found", err=True)
        raise typer.Exit(1)


# Auth command group
auth_app = typer.Typer(help="Manage authentication")
app.add_typer(auth_app, name="auth")


@auth_app.command("login")
def auth_login(
    api_key: Annotated[Optional[str], typer.Argument(help="Your Flowpad API key (optional - opens browser if not provided)")] = None
):
    """
    Login to Flowpad.

    If API key is provided, stores it directly.
    If no API key is provided, opens browser for authentication.

    Examples:
      flow auth login your-api-key-here
      flow auth login  # Opens browser
    """
    if api_key:
        # Direct API key login
        from auth import validate_api_key
        from app_config import set_user
        try:
            user_info = validate_api_key(api_key)
            set_api_key(api_key)
            set_user(user_info)
            typer.echo("✓ Successfully logged in to Flowpad")
            typer.echo(f"✓ API key stored securely in system keyring")
            typer.echo(f"✓ User ID: {user_info.get('id')}")
        except Exception as e:
            typer.echo(f"✗ Login failed: {e}", err=True)
            raise typer.Exit(1)
    else:
        # Browser-based login flow
        import webbrowser
        from local_server.server import wait_for_post_login
        from env_loader import get_login_url

        # Get port from env
        port = int(os.environ.get("LOCAL_SERVER_PORT", "9007"))

        # Build the callback URL
        callback_url = f"http://127.0.0.1:{port}/post_login"

        # Get the formatted login URL with the callback URL
        full_login_url = get_login_url(callback_url)

        typer.echo(f"\n🌊 Opening browser for Flowpad login...")
        typer.echo(f"Callback URL: {callback_url}")
        typer.echo(f"Full Login URL: {full_login_url}\n")

        # Open browser
        webbrowser.open(full_login_url)

        # Wait for the login callback
        result = wait_for_post_login()

        if result.get("success"):
            typer.echo("\n✓ Successfully logged in to Flowpad")
            typer.echo("✓ API key stored securely in system keyring")
            if "user" in result:
                typer.echo(f"✓ User ID: {result['user'].get('id')}")
        else:
            typer.echo(f"\n✗ Login failed: {result.get('message', 'Unknown error')}", err=True)
            if "error" in result:
                typer.echo(f"  Error: {result['error']}", err=True)
            raise typer.Exit(1)


@auth_app.command("logout")
def auth_logout():
    """
    Logout from Flowpad by removing your stored API key.

    Example: flow auth logout
    """
    if is_logged_in():
        from app_config import clear_user
        delete_api_key()
        clear_user()
        typer.echo("✓ Successfully logged out from Flowpad")
        typer.echo(f"✓ API key and user info removed")
    else:
        typer.echo("⚠ Not currently logged in")


@auth_app.command("test")
def auth_test(
    delay: Annotated[int, typer.Option(help="Delay in seconds before allowing login")] = 5
):
    """
    Test the login flow using a local test page with countdown timer.

    This command opens a test login page that simulates the Flowpad login flow.
    Use the --delay option to test the countdown timer functionality.

    Examples:
      flow auth test          # 5 second delay (default)
      flow auth test --delay 10  # 10 second delay
    """
    import webbrowser
    from local_server.server import wait_for_post_login

    # Get port from env
    port = int(os.environ.get("LOCAL_SERVER_PORT", "9007"))

    # Build the test login URL with callback and delay
    callback_url = f"http://127.0.0.1:{port}/post_login"
    test_login_url = f"http://127.0.0.1:{port}/test_login?callback={callback_url}&delay={delay}"

    typer.echo(f"\n🧪 Opening test login page with {delay} second delay...")
    typer.echo(f"Test URL: {test_login_url}\n")

    # Open browser
    webbrowser.open(test_login_url)

    # Wait for the login callback
    result = wait_for_post_login()

    if result.get("success"):
        typer.echo("\n✓ Test login successful!")
        typer.echo("✓ API key stored securely in system keyring")
        if "user" in result:
            typer.echo(f"✓ User ID: {result['user'].get('id')}")
    else:
        typer.echo(f"\n✗ Test login failed: {result.get('message', 'Unknown error')}", err=True)
        if "error" in result:
            typer.echo(f"  Error: {result['error']}", err=True)
        raise typer.Exit(1)


# Hooks command group
hooks_app = typer.Typer(help="Manage Claude Code hooks")
app.add_typer(hooks_app, name="hooks")


def _parse_scope(scope_str: str) -> ClaudeScope:
    """Convert scope string to ClaudeScope enum."""
    scope_map = {
        "user": ClaudeScope.USER,
        "project": ClaudeScope.PROJECT,
        "local": ClaudeScope.LOCAL,
    }
    scope_lower = scope_str.lower()
    if scope_lower not in scope_map:
        raise typer.BadParameter(f"Invalid scope '{scope_str}'. Must be one of: user, project, local")
    return scope_map[scope_lower]


@hooks_app.command("set")
def hooks_set(
    scope: Annotated[str, typer.Option(help="Scope for hooks: user, project, or local")] = "user",
):
    """
    Set all Flow hooks in Claude Code settings.

    Configures hooks for all Claude Code events to report to flow trace.
    Default scope is 'user' (applies globally to all projects).

    Events configured:
    - UserPromptSubmit: User sends a prompt
    - PreToolUse: Before a tool is executed
    - PostToolUse: After a tool is executed
    - Notification: Claude sends a notification
    - Stop: Session stops
    - SubagentStop: Subagent stops

    Examples:
      flow hooks set
      flow hooks set --scope project
      flow hooks set --scope local
    """
    from commands.setup_cmd.claude_code_setup.claude_hooks import setHook
    from commands.setup_cmd.claude_code_setup.setup_claude import _get_hook_script_path
    from commands.setup_cmd.claude_code_setup.flow_metadata import FlowHookMetadata

    try:
        claude_scope = _parse_scope(scope)
    except typer.BadParameter as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    context = get_context()

    # Validate scope is available
    if claude_scope in [ClaudeScope.PROJECT, ClaudeScope.LOCAL] and not context.is_in_repo():
        typer.echo(f"Error: Cannot use '{scope}' scope - not in a git repository", err=True)
        raise typer.Exit(1)

    typer.echo(f"Setting Flow hooks (scope: {scope})...")

    # Get the hook script path
    hook_script_path = _get_hook_script_path()

    if not hook_script_path.exists():
        typer.echo(f"Error: Hook script not found at {hook_script_path}", err=True)
        typer.echo("Run 'flow setup claude-code' first to create the hook script.", err=True)
        raise typer.Exit(1)

    # All Claude Code hook events to configure
    # Events without matchers
    events_no_matcher = [
        "UserPromptSubmit",
        "Notification",
        "Stop",
        "SubagentStop",
    ]

    # Events with matchers (use "*" to match all tools)
    events_with_matcher = [
        "PreToolUse",
        "PostToolUse",
    ]

    success_count = 0

    # Set hooks for events without matchers
    for event_name in events_no_matcher:
        flow_metadata = FlowHookMetadata.create(name=event_name.lower())
        success = setHook(
            scope=claude_scope,
            event_name=event_name,
            matcher=None,
            cmd=str(hook_script_path),
            context=context,
            flow_metadata=flow_metadata
        )
        if success:
            typer.echo(f"✓ {event_name}")
            success_count += 1
        else:
            typer.echo(f"✗ {event_name} (failed)", err=True)

    # Set hooks for events with matchers (match all tools)
    for event_name in events_with_matcher:
        flow_metadata = FlowHookMetadata.create(name=event_name.lower())
        success = setHook(
            scope=claude_scope,
            event_name=event_name,
            matcher="*",  # Match all tools
            cmd=str(hook_script_path),
            context=context,
            flow_metadata=flow_metadata
        )
        if success:
            typer.echo(f"✓ {event_name} (matcher: *)")
            success_count += 1
        else:
            typer.echo(f"✗ {event_name} (failed)", err=True)

    typer.echo(f"\n✓ {success_count} hooks configured")
    typer.echo(f"✓ Settings file: {context.get_claude_settings_path(claude_scope)}")


@hooks_app.command("clear")
def hooks_clear(
    scope: Annotated[str, typer.Option(help="Scope for hooks: user, project, or local")] = "user",
):
    """
    Clear all Flow hooks from Claude Code settings.

    Only removes hooks that are Flow commands (safe for other hooks).
    Default scope is 'user'.

    Examples:
      flow hooks clear
      flow hooks clear --scope project
    """
    from commands.setup_cmd.claude_code_setup.claude_hooks import removeHook

    try:
        claude_scope = _parse_scope(scope)
    except typer.BadParameter as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    context = get_context()

    # Validate scope is available
    if claude_scope in [ClaudeScope.PROJECT, ClaudeScope.LOCAL] and not context.is_in_repo():
        typer.echo(f"Error: Cannot use '{scope}' scope - not in a git repository", err=True)
        raise typer.Exit(1)

    typer.echo(f"Clearing Flow hooks (scope: {scope})...")

    # Remove the UserPromptSubmit hook (only if it's a flow command)
    success = removeHook(
        scope=claude_scope,
        event_name="UserPromptSubmit",
        matcher=None,
        context=context
    )

    if success:
        typer.echo(f"✓ Flow hooks cleared from {context.get_claude_settings_path(claude_scope)}")
    else:
        typer.echo("No Flow hooks found to remove.")


@hooks_app.command("report")
def hooks_report():
    """
    Report hook event data to the local Flow server.

    This command is called BY hook scripts to report event data.
    Reads JSON from stdin and POSTs to the local server.
    Always exits with code 0 to avoid blocking Claude.

    This command is designed for efficiency - called on every hook trigger.
    """
    import sys
    import json

    try:
        # Read JSON from stdin (hook event data)
        input_data = json.load(sys.stdin)

        # Get server port
        port = int(os.environ.get("LOCAL_SERVER_PORT", "9007"))

        # POST to local server (fire and forget, with short timeout)
        try:
            requests.post(
                f"http://127.0.0.1:{port}/api/hooks/report",
                json=input_data,
                timeout=2  # Short timeout for efficiency
            )
            # Silently succeed or fail - don't block Claude
        except requests.exceptions.RequestException:
            # Server not running or request failed - that's okay
            pass

    except json.JSONDecodeError:
        # Invalid JSON input - exit silently
        pass
    except Exception:
        # Any other error - exit silently
        pass

    # Always exit 0 to not block Claude
    raise typer.Exit(0)


@hooks_app.command("list")
def hooks_list(
    scope: Annotated[str, typer.Option(help="Scope for hooks: user, project, or local")] = "user",
):
    """
    List all configured hooks in Claude Code settings.

    Shows events, matchers, and hook commands for the specified scope.
    Default scope is 'user'.

    Examples:
      flow hooks list
      flow hooks list --scope project
    """
    from commands.setup_cmd.claude_code_setup.hook_parser import HookParser

    try:
        claude_scope = _parse_scope(scope)
    except typer.BadParameter as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    context = get_context()

    # Validate scope is available
    if claude_scope in [ClaudeScope.PROJECT, ClaudeScope.LOCAL] and not context.is_in_repo():
        typer.echo(f"Error: Cannot use '{scope}' scope - not in a git repository", err=True)
        raise typer.Exit(1)

    settings_path = context.get_claude_settings_path(claude_scope)
    typer.echo(f"Hooks for scope '{scope}': {settings_path}")
    typer.echo("-" * 60)

    # Initialize HookParser for the specified scope
    hook_parser = HookParser(context=context, scope=claude_scope)

    events = hook_parser.list_events()

    if not events:
        typer.echo("No hooks configured.")
        return

    for event in events:
        typer.echo(f"\nEvent: {event}")
        event_hooks = hook_parser.get_event_hooks(event)

        # Handle null/None values in hooks
        if event_hooks is None:
            typer.echo("  (disabled/null)")
            continue

        for entry in event_hooks:
            matcher = entry.get("matcher")
            if matcher:
                typer.echo(f"  Matcher: {matcher}")
            else:
                typer.echo("  Matcher: (none)")

            hooks = entry.get("hooks", [])
            for hook in hooks:
                hook_type = hook.get("type", "unknown")
                command = hook.get("command", "")
                typer.echo(f"    [{hook_type}] {command}")


def cli_main():
    """Entry point that can be used with CLICommand."""
    app()


if __name__ == "__main__":
    app()
