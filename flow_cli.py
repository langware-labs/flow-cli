#!/usr/bin/env python3

import typer
import requests
from typing import Optional
from typing_extensions import Annotated
from cli_context import CLIContext
from cli_command import CLICommand
from config_manager import list_config, set_config_value, remove_config_value, setup_defaults, get_config_value
from commands.setup_cmd.setup_cmd import run_setup
from commands.prompt_cmd import run_prompt_command

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

    If no command is provided, prints welcome message.
    """
    # Ensure config defaults are set
    setup_defaults()

    # If no subcommand was invoked, show welcome message
    if ctx.invoked_subcommand is None:
        typer.echo("Hello flowpad")


@app.command()
def setup(
    agent_name: Annotated[str, typer.Argument(help="Name of the coding agent (e.g., claude-code)")],
):
    """
    Setup flowpad for a specific coding agent.

    Example: flow setup claude-code
    """
    context = get_context()

    # Set first_time_prompt flag when running setup
    set_config_value("first_time_prompt", "true")

    run_setup(agent_name, context)


@app.command()
def prompt(
    prompt_text: Annotated[Optional[str], typer.Argument(help="Prompt text to process")] = None
):
    """
    Process a prompt command.

    Example: flow prompt "analyze this code"
    """
    if prompt_text:
        run_prompt_command(prompt_text)


@app.command()
def ping(
    ping_str: Annotated[str, typer.Argument(help="Ping string to send")],
):
    """
    Send a ping to the local server for testing hook integration.

    Example: flow ping hello
    """
    # Get the local server port from config
    setup_defaults()
    port_str = get_config_value("local_cli_port")
    port = int(port_str) if port_str else 9006

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


def cli_main():
    """Entry point that can be used with CLICommand."""
    app()


if __name__ == "__main__":
    app()
